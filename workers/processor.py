import hashlib
import json
import os
import re
from datetime import datetime, date, timedelta
from services.sentence_finder import extract_sentence_from_pdf
from services.ai_client import extract_data_with_gemini
from services.text_processor import find_section_hybrid
from services.database import save_extraction, get_cache, save_cache, get_user_credits, deduct_credit
from services.legal_validator import validar_dados
from models import ProcessoTrabalhista
from config import settings

# ── Caminho da pasta de playbooks ────────────────────────────────────────────
SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "skills")

def _load_skill(filename: str) -> str:
    """Carrega um playbook .md da pasta skills/."""
    path = os.path.join(SKILLS_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    print(f"[SKILL] Aviso: playbook não encontrado: {filename}")
    return ""

def _hash_pdf(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()

# ---------------------------------------------------------------------------
# Campos de texto simples do ProcessoTrabalhista
# ---------------------------------------------------------------------------
CAMPOS_TEXTO = [
    # Identificação
    "numero_processo",
    "vara_trabalho",
    "reclamante",
    "reclamada",
    "tipo_rito",
    "funcao_reclamante",
    "data_sentenca",
    "data_ajuizamento",
    "advogado_reclamante",   # NOVO
    "juiz_responsavel",      # NOVO
    # Contrato
    "data_admissao",
    "data_demissao",
    "motivo_rescisao",
    "tipo_contrato",         # NOVO
    "salario_base",
    "jornada_contratual",
    "horario_trabalho",
    "aviso_previo_dias",     # NOVO
    "data_saida_ctps",       # NOVO
    "anotacao_ctps",         # NOVO
    "seguro_desemprego",     # NOVO
    # Parâmetros de cálculo
    "indice_correcao",
    "juros_mora",
    "contribuicao_previdenciaria",
    "ir_retido_fonte",
    "honorarios_sucumbenciais",
    "percentual_honorarios",
    "custas_processuais",
    # Valores fixos e multas
    "dano_moral",
    "dano_material",
    "multa_art_467",
    "multa_art_477",
    # FGTS especial
    "fgts_sobre_aviso_previo",        # NOVO
    "fgts_multa_40_aviso_previo",     # NOVO
    "fgts_sobre_ferias_indenizadas",  # NOVO
    "fgts_periodo_completo",          # NOVO
    "fgts_observacoes",               # NOVO
]

# Campos de texto simples de cada VerbaDeferida
CAMPOS_VERBA_TEXTO = [
    "nome",
    "status_final",
    "periodo",
    "percentual",
    "quantidade_diaria",
    "base_calculo",
    "valor_fixado",
    "observacoes",
]

# Valores que a IA costuma retornar no lugar de null
SUSPICIOUS = frozenset([
    "não informado", "nao informado", "n/a", "null", "none",
    "não consta", "nao consta", "desconhecido", "indefinido",
    "não identificado", "nao identificado", "-", "",
])

def _clean_str(value) -> str | None:
    """Retorna None se o valor for suspeito/vazio, senão retorna a string limpa."""
    if value is None:
        return None
    if isinstance(value, str) and value.lower().strip() in SUSPICIOUS:
        return None
    return value

def _clean_bool(value, default: bool) -> bool:
    """Garante que o valor seja booleano."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() in ("true", "sim", "yes", "1"):
            return True
        if value.lower() in ("false", "não", "nao", "no", "0"):
            return False
    return default

def _validate_result(data: dict) -> dict:
    """
    Validação pós-IA:
    - Limpa strings suspeitas → None
    - Garante booleanos corretos
    - Garante listas onde esperado
    - Normaliza campos de cada verba
    """
    cleaned = {}

    # ── Campos de texto simples ───────────────────────────────────────────────
    for campo in CAMPOS_TEXTO:
        cleaned[campo] = _clean_str(data.get(campo))

    # ── Booleanos ─────────────────────────────────────────────────────────────
    cleaned["justica_gratuita"] = _clean_bool(data.get("justica_gratuita"), default=False)

    # ── Lista de verbas ───────────────────────────────────────────────────────
    verbas_raw = data.get("verbas_deferidas", [])
    if not isinstance(verbas_raw, list):
        verbas_raw = []

    verbas_limpas = []
    for verba in verbas_raw:
        if not isinstance(verba, dict):
            continue

        v = {}

        # Campos de texto
        for campo in CAMPOS_VERBA_TEXTO:
            v[campo] = _clean_str(verba.get(campo))

        # Nome nunca pode ser null
        if not v.get("nome"):
            v["nome"] = "Verba não identificada"

        # status_final tem valor padrão
        if not v.get("status_final"):
            v["status_final"] = "não informado"

        # integracao_salarial: booleano ou null
        integ = verba.get("integracao_salarial")
        if isinstance(integ, bool):
            v["integracao_salarial"] = integ
        elif isinstance(integ, str) and integ.lower() in ("true", "sim"):
            v["integracao_salarial"] = True
        elif isinstance(integ, str) and integ.lower() in ("false", "não", "nao"):
            v["integracao_salarial"] = False
        else:
            v["integracao_salarial"] = None

        # reflexos: lista de strings limpas
        reflexos_raw = verba.get("reflexos", [])
        if isinstance(reflexos_raw, list):
            v["reflexos"] = [r for r in reflexos_raw if isinstance(r, str) and r.strip()]
        else:
            v["reflexos"] = []

        # P3: frações de avos (ex: "11/12", "2/12") pertencem ao campo período,
        # não à quantidade diária. A IA frequentemente confunde os dois.
        qtd = str(v.get("quantidade_diaria") or "")
        if re.search(r"^\d+/12$", qtd.strip()):
            if not v.get("periodo"):
                v["periodo"] = qtd.strip()
            v["quantidade_diaria"] = None

        verbas_limpas.append(v)

    cleaned["verbas_deferidas"] = verbas_limpas

    # ── Pós-processamento determinístico (zero tokens) ────────────────────────

    # 1. jornada_contratual — deriva do horario_trabalho quando a IA não extraiu
    if not cleaned.get("jornada_contratual") and cleaned.get("horario_trabalho"):
        h = cleaned["horario_trabalho"]
        m = re.search(
            r"(\d{1,2})(?::(\d{2}))?(?:h\d*)?\s*[àa][s]?\s*(\d{1,2})(?::(\d{2}))?(?:h\d*)?"
            r".*?com\s+(\d+(?:[,\.]\d+)?)\s*(?:h(?:ora)?|:00)",
            h, re.IGNORECASE
        )
        if m:
            try:
                entrada_h = int(m.group(1)); entrada_m = int(m.group(2) or 0)
                saida_h   = int(m.group(3)); saida_m   = int(m.group(4) or 0)
                intervalo = float(m.group(5).replace(",", "."))
                total_min = (saida_h * 60 + saida_m) - (entrada_h * 60 + entrada_m) - intervalo * 60
                diarias   = total_min / 60
                semanais  = diarias * 6
                if 0 < diarias <= 12:
                    cleaned["jornada_contratual"] = f"{diarias:.0f}h diárias / {semanais:.0f}h semanais"
                    print(f"[POSTP] jornada_contratual derivada: {cleaned['jornada_contratual']}")
            except Exception:
                pass

    # 2. fgts_periodo_completo — completa com datas reais quando genérico
    fgts = cleaned.get("fgts_periodo_completo") or ""
    if fgts and "/" not in fgts:
        adm   = cleaned.get("data_admissao")
        saida = cleaned.get("data_saida_ctps") or cleaned.get("data_demissao")
        if adm and saida:
            cleaned["fgts_periodo_completo"] = f"Todo o período contratual — {adm} a {saida}"
            print(f"[POSTP] fgts_periodo_completo completado: {cleaned['fgts_periodo_completo']}")

    # 3. prescricao_quinquenal — calcula automaticamente (ajuizamento - 5 anos)
    if not cleaned.get("prescricao_quinquenal") and cleaned.get("data_ajuizamento"):
        try:
            d, m_n, y = cleaned["data_ajuizamento"].split("/")
            ajuiz = date(int(y), int(m_n), int(d))
            # Prescrição quinquenal: 5 anos antes do ajuizamento
            prescricao = ajuiz.replace(year=ajuiz.year - 5)
            cleaned["prescricao_quinquenal"] = prescricao.strftime("%d/%m/%Y")
            print(f"[POSTP] prescricao_quinquenal calculada: {cleaned['prescricao_quinquenal']}")
        except Exception:
            pass

    # 4. divisor_horas — detecta por regex no texto do dispositivo / jornada
    if not cleaned.get("divisor_horas"):
        # Busca no horario_trabalho e jornada_contratual
        textos_busca = [
            cleaned.get("horario_trabalho") or "",
            cleaned.get("jornada_contratual") or "",
        ]
        # Também busca nas observações das verbas de horas extras
        for v in cleaned.get("verbas_deferidas", []):
            nome = (v.get("nome") or "").lower()
            if "hora" in nome and "extra" in nome:
                textos_busca.append(v.get("base_calculo") or "")
                textos_busca.append(v.get("observacoes") or "")

        texto_concat = " ".join(textos_busca)
        m_div = re.search(r"\b(150|180|200|220)\s*(?:h(?:oras?)?|\/\s*m[eê]s)?\b", texto_concat, re.IGNORECASE)
        if m_div:
            cleaned["divisor_horas"] = m_div.group(1)
            print(f"[POSTP] divisor_horas detectado: {cleaned['divisor_horas']}")
        else:
            # Inferência pela jornada calculada
            jornada = cleaned.get("jornada_contratual") or ""
            m_sem = re.search(r"(\d+)\s*h(?:oras?)?\s*semanais?", jornada, re.IGNORECASE)
            if m_sem:
                h_sem = int(m_sem.group(1))
                # Mapa fixo para jornadas padrão
                divisores = {30: "150", 35: "175", 36: "180", 40: "200", 44: "220"}
                if h_sem in divisores:
                    cleaned["divisor_horas"] = divisores[h_sem]
                    print(f"[POSTP] divisor_horas inferido da jornada ({h_sem}h/sem): {cleaned['divisor_horas']}")
                else:
                    # Fallback matemático: (h_semanais / 6) * 30 — fórmula TST
                    import math
                    divisor_calc = str(math.ceil((h_sem / 6) * 30))
                    cleaned["divisor_horas"] = divisor_calc
                    print(f"[POSTP] divisor_horas calculado matematicamente ({h_sem}h/sem → {divisor_calc})")

    # 5. evolucao_salarial — valor padrão se não extraído
    if not cleaned.get("evolucao_salarial"):
        salario = cleaned.get("salario_base")
        if salario:
            cleaned["evolucao_salarial"] = f"Salário fixo reconhecido: {salario}"

    return cleaned


# Campos obrigatórios mínimos para considerar extração completa
_CAMPOS_OBRIGATORIOS = [
    "numero_processo",
    "reclamante",
    "reclamada",
    "data_sentenca",
    "salario_base",
]
# Mínimo de verbas esperadas para uma sentença procedente típica
_MIN_VERBAS = 3


def _qualidade_ok(dados: dict) -> tuple[bool, str]:
    """
    Verifica se a extração tem qualidade mínima para ser cacheada.
    Retorna (ok, motivo).
    """
    # Checa campos obrigatórios
    faltando = [c for c in _CAMPOS_OBRIGATORIOS if not dados.get(c)]
    if faltando:
        return False, f"campos obrigatórios ausentes: {faltando}"

    # Checa verbas deferidas
    n_verbas = len(dados.get("verbas_deferidas") or [])
    if n_verbas < _MIN_VERBAS:
        return False, f"apenas {n_verbas} verbas extraídas (mínimo: {_MIN_VERBAS})"

    return True, "ok"


def process_lawsuit_pdf(user_id: str, file_bytes: bytes) -> dict:
    print(f"[PROCESSOR] user={user_id}")

    # 1. Freemium — verifica créditos
    credits = get_user_credits(user_id)
    if credits <= 0:
        return {"status": "erro", "msg": "Saldo esgotado. Adquira mais créditos."}

    # 2. Cache — só usa se tiver qualidade mínima
    pdf_hash = _hash_pdf(file_bytes)
    cached = get_cache(pdf_hash)
    if cached:
        ok, motivo = _qualidade_ok(cached)
        if ok:
            print("[PROCESSOR] Cache hit! (qualidade ok)")
            # Recupera doc_type do dado cacheado se disponível
            cached_doc_type = cached.get("_meta_doc_type", "sentenca")
            return {
                "status": "sucesso",
                "source": "cache",
                "doc_type": cached_doc_type,
                "data": cached,
            }
        else:
            print(f"[PROCESSOR] Cache descartado — qualidade insuficiente: {motivo}")

    # 3. Extração inteligente — detecta e recorta sentença/acórdão
    texto, doc_type = extract_sentence_from_pdf(file_bytes)
    if not texto.strip():
        return {"status": "erro", "msg": "PDF sem texto legível"}

    print(f"[PROCESSOR] Tipo detectado: {doc_type} | Chars extraídos: {len(texto)}")

    # 4. Carrega o playbook correto para o tipo de documento
    _PLAYBOOK_MAP = {
        "sentenca":   "sentenca_ordinaria.md",
        "acordao":    "acordao.md",
        "liquidacao": "calculo_liquidacao.md",
        "embargos":   "embargos_declaracao.md",
        "despacho":   "despacho_execucao.md",
        "completo":   "sentenca_ordinaria.md",
    }
    skill_file = _PLAYBOOK_MAP.get(doc_type, "sentenca_ordinaria.md")
    playbook = _load_skill(skill_file)

    # Se dispositivo não encontrado, carrega skill extra
    dispositivo_pos = find_section_hybrid(texto, "dispositivo")
    if dispositivo_pos < 0:
        print("[SKILL] Dispositivo não encontrado — carregando filtro_dispositivo.md")
        playbook += "\n\n" + _load_skill("filtro_dispositivo.md")

    # 5. IA com cascata + playbook
    ai_result = extract_data_with_gemini(texto, playbook=playbook)
    if ai_result["error"]:
        return {"status": "erro", "msg": ai_result["error"]}

    # 6. Validação pós-IA
    dados_limpos = _validate_result(ai_result["data"])

    # 7. Validação Pydantic
    try:
        processo = ProcessoTrabalhista(**dados_limpos)
        dados_finais = processo.model_dump()
    except Exception as e:
        return {"status": "erro", "msg": f"Dados inválidos da IA: {e}"}

    # 8. Validador lógico de reflexos (zero tokens — Python puro)
    alertas = validar_dados(dados_finais)
    dados_finais["alertas_juridicos"] = alertas

    # 9. Só cacheia e desconta crédito se qualidade mínima atingida
    ok, motivo = _qualidade_ok(dados_finais)
    if ok:
        # Salva doc_type como metadado dentro do cache para recuperação futura
        dados_finais["_meta_doc_type"] = doc_type
        save_cache(pdf_hash, dados_finais)
        doc_id = save_extraction(user_id, dados_finais)
        deduct_credit(user_id)
        print(f"[PROCESSOR] Resultado salvo (qualidade ok)")
    else:
        # Salva na extração para histórico mas não no cache (permite reprocessar)
        doc_id = save_extraction(user_id, dados_finais)
        print(f"[PROCESSOR] Qualidade insuficiente — NÃO cacheado: {motivo}")

    return {
        "status": "sucesso",
        "source": "ai",
        "doc_type": doc_type,
        "model_used": ai_result["model_used"],
        "doc_id": doc_id,
        "data": dados_finais,
        "alertas_juridicos": alertas,
        "qualidade_ok": ok,
        "qualidade_motivo": motivo if not ok else None,
    }