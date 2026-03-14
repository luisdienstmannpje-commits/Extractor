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
from services.legal_engine.rule_registry import carregar_todas_as_regras   # Gap 2
from services.legal_engine.engine import LegalRuleEngine                   # Gap 2
from services.legal_engine.dynamic_rule_loader import (                    # Self-Healing
    carregar_regras_ativas,
    executar_shadow_pipeline,
)
from services.explanation_engine import (
    gerar_explicacoes,
    gerar_parecer_parcelas_apuradas,
    obter_textos_padrao_criterios_parecer,
    gerar_parecer_tecnico_completo,
)
from services.jurisprudencia.consistencia.verba_deduplicator import deduplicar_verbas  # S11
from memoria_calculo import gerar_memoria                                               # M1
from models import ProcessoTrabalhista
from config import settings

# ── Singleton — carregado uma vez na inicialização do módulo ─────────────────
# Evita recarregar as 20 regras e reordenar por prioridade a cada request.
_RULE_ENGINE = LegalRuleEngine(carregar_todas_as_regras())

# ── Caminho da pasta de playbooks ────────────────────────────────────────────
SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "skills")

def _load_skill(filename: str) -> str:
    """Carrega um playbook .md da pasta skills/."""
    path = os.path.join(SKILLS_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    print(f"[SKILL] Aviso: playbook não encontrado: {filename}", flush=True)
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
    "advogado_reclamante",
    "juiz_responsavel",
    # Contrato
    "data_admissao",
    "data_demissao",
    "motivo_rescisao",
    "tipo_contrato",
    "salario_base",
    "jornada_contratual",
    "horario_trabalho",
    "aviso_previo_dias",
    "data_saida_ctps",
    "anotacao_ctps",
    "seguro_desemprego",
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
    "fgts_sobre_aviso_previo",
    "fgts_multa_40_aviso_previo",
    "fgts_sobre_ferias_indenizadas",
    "fgts_periodo_completo",
    "fgts_observacoes",
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
    """
    Retorna None se o valor for suspeito/vazio; caso contrário, retorna uma string.

    Importante: a IA às vezes retorna números (float/int) para campos textuais
    como `quantidade_diaria` ou `percentual`. Para não estourar validação Pydantic,
    convertemos qualquer valor não-nulo em string, mantendo apenas os marcadores
    "não informado"/etc. como None.
    """
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip()
        if v.lower() in SUSPICIOUS:
            return None
        return v
    # Qualquer outro tipo (int, float, etc.) é convertido para string
    return str(value)


def _dedup_alertas(*listas: list[str]) -> list[str]:
    """
    Mescla listas de alertas removendo duplicados, preservando a ordem
    de primeira aparição. Útil para evitar que o mesmo alerta jurídico
    apareça duas vezes quando proveniente de mais de uma camada.
    """
    vistos: set[str] = set()
    resultado: list[str] = []
    for lista in listas:
        if not lista:
            continue
        for alerta in lista:
            if alerta not in vistos:
                vistos.add(alerta)
                resultado.append(alerta)
    return resultado

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
                    print(f"[POSTP] jornada_contratual derivada: {cleaned['jornada_contratual']}", flush=True)
            except Exception:
                pass

    # 2. fgts_periodo_completo — completa com datas reais quando genérico
    fgts = cleaned.get("fgts_periodo_completo") or ""
    if fgts and "/" not in fgts:
        adm   = cleaned.get("data_admissao")
        saida = cleaned.get("data_saida_ctps") or cleaned.get("data_demissao")
        if adm and saida:
            cleaned["fgts_periodo_completo"] = f"Todo o período contratual — {adm} a {saida}"
            print(f"[POSTP] fgts_periodo_completo completado: {cleaned['fgts_periodo_completo']}", flush=True)

    # 3. prescricao_quinquenal — calcula automaticamente (ajuizamento - 5 anos)
    if not cleaned.get("prescricao_quinquenal") and cleaned.get("data_ajuizamento"):
        try:
            d, m_n, y = cleaned["data_ajuizamento"].split("/")
            ajuiz = date(int(y), int(m_n), int(d))
            prescricao = ajuiz.replace(year=ajuiz.year - 5)
            cleaned["prescricao_quinquenal"] = prescricao.strftime("%d/%m/%Y")
            print(f"[POSTP] prescricao_quinquenal calculada: {cleaned['prescricao_quinquenal']}", flush=True)
        except Exception:
            pass

    # 4. divisor_horas — detecta por regex no texto do dispositivo / jornada
    if not cleaned.get("divisor_horas"):
        textos_busca = [
            cleaned.get("horario_trabalho") or "",
            cleaned.get("jornada_contratual") or "",
        ]
        for v in cleaned.get("verbas_deferidas", []):
            nome = (v.get("nome") or "").lower()
            if "hora" in nome and "extra" in nome:
                textos_busca.append(v.get("base_calculo") or "")
                textos_busca.append(v.get("observacoes") or "")

        texto_concat = " ".join(textos_busca)
        m_div = re.search(r"\b(150|180|200|220)\s*(?:h(?:oras?)?|\/\s*m[eê]s)?\b", texto_concat, re.IGNORECASE)
        if m_div:
            cleaned["divisor_horas"] = m_div.group(1)
            print(f"[POSTP] divisor_horas detectado: {cleaned['divisor_horas']}", flush=True)
        else:
            jornada = cleaned.get("jornada_contratual") or ""
            m_sem = re.search(r"(\d+)\s*h(?:oras?)?\s*semanais?", jornada, re.IGNORECASE)
            if m_sem:
                h_sem = int(m_sem.group(1))
                divisores = {30: "150", 35: "175", 36: "180", 40: "200", 44: "220"}
                if h_sem in divisores:
                    cleaned["divisor_horas"] = divisores[h_sem]
                    print(f"[POSTP] divisor_horas inferido da jornada ({h_sem}h/sem): {cleaned['divisor_horas']}", flush=True)
                else:
                    import math
                    divisor_calc = str(math.ceil((h_sem / 6) * 30))
                    cleaned["divisor_horas"] = divisor_calc
                    print(f"[POSTP] divisor_horas calculado matematicamente ({h_sem}h/sem -> {divisor_calc})", flush=True)

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
    faltando = [c for c in _CAMPOS_OBRIGATORIOS if not dados.get(c)]
    if faltando:
        return False, f"campos obrigatórios ausentes: {faltando}"

    n_verbas = len(dados.get("verbas_deferidas") or [])
    if n_verbas < _MIN_VERBAS:
        return False, f"apenas {n_verbas} verbas extraídas (mínimo: {_MIN_VERBAS})"

    return True, "ok"


def process_lawsuit_pdf(user_id: str, file_bytes: bytes, job_id: str = "") -> dict:
    """
    Pipeline completo de extração.

    Parâmetros
    ----------
    user_id    : identificador do usuário (freemium / créditos)
    file_bytes : bytes do PDF
    job_id     : identificador do job vindo do main.py — usado na memória de cálculo (M1).
                 Opcional: se vazio, usa doc_id como fallback após salvar no banco.
    """
    print(f"[PROCESSOR] user={user_id}", flush=True)

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
            print("[PROCESSOR] Cache hit! (qualidade ok)", flush=True)
            cached_doc_type = cached.get("_meta_doc_type", "sentenca")
            return {
                "status": "sucesso",
                "source": "cache",
                "doc_type": cached_doc_type,
                "data": cached,
            }
        else:
            print(f"[PROCESSOR] Cache descartado — qualidade insuficiente: {motivo}", flush=True)

    # 3. Extração inteligente — detecta e recorta sentença/acórdão
    texto, doc_type = extract_sentence_from_pdf(file_bytes)
    if not texto.strip():
        return {"status": "erro", "msg": "PDF sem texto legível"}

    print(f"[PROCESSOR] Tipo detectado: {doc_type} | Chars extraídos: {len(texto)}", flush=True)

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
        print("[SKILL] Dispositivo não encontrado — carregando filtro_dispositivo.md", flush=True)
        playbook += "\n\n" + _load_skill("filtro_dispositivo.md")

    # 5. IA com cascata + playbook
    ai_result = extract_data_with_gemini(texto, playbook=playbook)
    if ai_result["error"]:
        return {"status": "erro", "msg": ai_result["error"]}

    # 6. Validação pós-IA
    dados_limpos = _validate_result(ai_result["data"])

    # 6b. Deduplicação de verbas — S11 (zero tokens — Python puro)
    if dados_limpos.get("verbas_deferidas"):
        verbas_dedup, avisos_dedup = deduplicar_verbas(dados_limpos["verbas_deferidas"])
        dados_limpos["verbas_deferidas"] = verbas_dedup
        if avisos_dedup:
            print(f"[DEDUP] {len(avisos_dedup)} duplicata(s) removida(s)", flush=True)
    else:
        avisos_dedup = []

    # 7. Validação Pydantic
    try:
        processo = ProcessoTrabalhista(**dados_limpos)
        dados_finais = processo.model_dump()
    except Exception as e:
        return {"status": "erro", "msg": f"Dados inválidos da IA: {e}"}

    # 8. Validação jurídica — duas camadas, zero tokens
    # 8a. legal_validator: alertas de reflexos e consistência de campos
    alertas_validator = validar_dados(dados_finais)

    # 8b. LegalRuleEngine: aplica as regras jurídicas estáticas (20 fixas)
    resultado_engine  = _RULE_ENGINE.executar(dados_finais)
    alertas_engine    = resultado_engine["alertas"]            # list[str]
    regras_aplicadas  = resultado_engine["regras_aplicadas"]   # list[str] — IDs
    memorial_juridico = resultado_engine["memorial_juridico"]  # list[dict]

    # 8b+. Self-Healing: injeta regras dinâmicas ATIVAS (Knowledge Base)
    # Apenas as regras com confidence_score >= 3 (status "active") geram alertas reais.
    try:
        regras_dinamicas = carregar_regras_ativas()
        if regras_dinamicas:
            engine_dyn = LegalRuleEngine(regras_dinamicas)
            res_dyn = engine_dyn.executar(dados_finais)
            alertas_engine  = alertas_engine + res_dyn.get("alertas", [])
            regras_aplicadas = regras_aplicadas + res_dyn.get("regras_aplicadas", [])
    except Exception as _e_dyn:
        print(f"[PROCESSOR] Aviso: erro nas regras dinâmicas (não crítico): {_e_dyn}", flush=True)

    # 8c. Explanation Engine: texto jurídico por verba (sem LLM)
    explicacoes = gerar_explicacoes(
        verbas=dados_finais.get("verbas_deferidas", []),
        memorial_juridico=memorial_juridico,
    )

    # Mescla todos os alertas — validator + engine + dinâmicas + dedup (sem duplicatas textuais)
    dados_finais["alertas_juridicos"] = _dedup_alertas(alertas_validator, alertas_engine, avisos_dedup)
    dados_finais["regras_aplicadas"]  = regras_aplicadas
    dados_finais["memorial_juridico"] = memorial_juridico
    dados_finais["explicacoes"]       = explicacoes

    # Parecer técnico — I. PARCELAS APURADAS (modelo perita: intro + itens com titulo/texto)
    parecer_secao_i = gerar_parecer_parcelas_apuradas(
        dados_finais.get("verbas_deferidas", []),
        dados_finais,
    )
    dados_finais["parecer_intro_parcelas"] = parecer_secao_i.get("intro", "")
    dados_finais["parecer_parcelas_apuradas"] = parecer_secao_i.get("itens", [])
    # Textos padrão da seção II. CRITÉRIOS UTILIZADOS (INSS e IRRF — redação oficial dos peritos)
    criterios_padrao = obter_textos_padrao_criterios_parecer()
    dados_finais["parecer_criterios_inss"] = criterios_padrao.get("inss", "")
    dados_finais["parecer_criterios_irrf"] = criterios_padrao.get("irrf", "")

    # Parecer técnico completo — template fixo + slot gerado pela IA no Padrão Ouro
    # Gera o texto final contínuo: cabeçalho + I. PARCELAS (IA) + II. CRITÉRIOS (fixo)
    # Armazenado em parecer_texto para uso no Excel/Word sem necessidade de montagem.
    try:
        parecer_completo = gerar_parecer_tecnico_completo(
            dados_finais,
            dados_finais.get("verbas_deferidas", []),
        )
        dados_finais["parecer_texto"]              = parecer_completo.get("texto", "")
        dados_finais["parecer_parcelas_ia"]        = parecer_completo.get("parcelas", "")
        dados_finais["parecer_model_used"]         = parecer_completo.get("model_used")
        if parecer_completo.get("error"):
            print(f"[PARECER] Aviso: IA retornou erro ao gerar parcelas — {parecer_completo['error']}", flush=True)
    except Exception as _e_parecer:
        dados_finais["parecer_texto"]       = ""
        dados_finais["parecer_parcelas_ia"] = ""
        dados_finais["parecer_model_used"]  = None
        print(f"[PARECER] Erro ao gerar parecer completo (não crítico): {_e_parecer}", flush=True)

    # 8d. Shadow Mode: executa regras shadow silenciosamente (métricas internas, sem output)
    # Não polui os alertas do usuário — usado apenas para coletar acertos/erros das hipóteses.
    try:
        executar_shadow_pipeline(dados_finais)
    except Exception as _e_shadow:
        print(f"[SHADOW] Aviso: erro no shadow pipeline (não crítico): {_e_shadow}", flush=True)

    # 9. Só cacheia e desconta crédito se qualidade mínima atingida
    ok, motivo = _qualidade_ok(dados_finais)
    if ok:
        dados_finais["_meta_doc_type"] = doc_type
        save_cache(pdf_hash, dados_finais)
        doc_id = save_extraction(user_id, dados_finais)
        deduct_credit(user_id)
        print(f"[PROCESSOR] Resultado salvo (qualidade ok)", flush=True)
    else:
        doc_id = save_extraction(user_id, dados_finais)
        print(f"[PROCESSOR] Qualidade insuficiente — NÃO cacheado: {motivo}", flush=True)

    # 10. Memória de cálculo — M1 (trilha de auditoria por extração)
    # Gerada apenas para extrações novas via IA — cache hits não reprocessam o pipeline.
    # job_id vindo do main.py tem precedência; fallback para doc_id do banco.
    gerar_memoria(
        job_id=job_id or str(doc_id),
        dados=dados_finais,
        model_used=ai_result["model_used"],
        doc_type=doc_type,
        avisos_dedup=avisos_dedup,
        explicacoes=explicacoes,
    )

    return {
        "status": "sucesso",
        "source": "ai",
        "doc_type": doc_type,
        "model_used": ai_result["model_used"],
        "doc_id": doc_id,
        "data": dados_finais,
        "alertas_juridicos":  dados_finais["alertas_juridicos"],
        "regras_aplicadas":   regras_aplicadas,
        "memorial_juridico":  memorial_juridico,
        "explicacoes":        explicacoes,
        "qualidade_ok":       ok,
        "qualidade_motivo":   motivo if not ok else None,
    }