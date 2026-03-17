"""
self_healing.py — Self-Healing Rule Engine e codificação de insight (Passo 6).

Gera novas regras Python automaticamente a partir dos aprendizados do Laboratório:
  - codify_insight: consolida aprendizado em regra Python + skill (Engenharia Reversa) + learning_log.
  - processar_aprendizado_autonomo: extrai hipóteses via Gemini, atualiza Knowledge Base (Multi-tenant
    via user_id), avalia regras shadow contra discrepâncias reais (acerto/punição).
  - evaluate_shadow_rules: compara predições das regras shadow com o relatório (punição/acerto).

Integração com services/knowledge_base.py mantida via tenant_id (user_id).
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from services.lab import learning_io
import logging

_logger = logging.getLogger("smart_extractor")


def _gerar_regra_python_gemini(
    aprendizado: dict, chamar_gemini_para_codify: Callable[[str], tuple]
) -> tuple:
    """Gera arquivo Python LegalRule completo com lógica real. Retorna (codigo_python, model_used)."""
    titulo = aprendizado.get("titulo", "Regra sem título")
    descricao = aprendizado.get("descricao", "")
    correcao = aprendizado.get("correcao", "")
    base_legal = aprendizado.get("base_legal", "")
    nivel = aprendizado.get("nivel_sugerido", "AVISO")
    prioridade = aprendizado.get("prioridade_sugerida", 40)

    slug = re.sub(r"[^\w]", "_", titulo.lower())[:30].strip("_")
    slug = re.sub(r"_+", "_", slug)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    class_name = "Lab" + "".join(w.capitalize() for w in slug.split("_")[:4]) + "Rule"
    rule_id = f"LAB_{slug.upper()}_{timestamp}"

    prompt = (
        "Você é engenheiro sênior de Python especializado em automação jurídica trabalhista.\n\n"
        "Gere um arquivo Python COMPLETO implementando uma regra para o motor LegalRuleEngine do PJeCalc.\n\n"
        "ESTRUTURA OBRIGATÓRIA (siga exatamente):\n\n"
        '"""\n'
        f"# {titulo}\n"
        f"# Base legal: {base_legal}\n"
        '"""\n'
        "from __future__ import annotations\n\n"
        "from services.legal_engine.rule_base import ContextoJuridico, LegalRule\n\n\n"
        f"class {class_name}(LegalRule):\n"
        '    """\n'
        f"    {descricao}\n\n"
        f"    Correção identificada pela perita: {correcao}\n"
        '    """\n\n'
        f'    id = "{rule_id}"\n'
        f'    titulo = "{titulo}"\n'
        f'    base_legal = "{base_legal}"\n'
        f"    prioridade = {prioridade}  # 10=STF 20=Súmulas TST 30=OJ 40=CLT 50=consistência\n"
        f'    descricao = "{descricao}"\n\n'
        "    def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:\n"
        "        try:\n"
        "            # IMPLEMENTE AQUI a condição de acionamento\n"
        "            # self._alerta(contexto, 'mensagem', nivel='ERRO'|'AVISO'|'INFO')\n"
        "            # self._registrar(contexto)\n"
        "            pass\n"
        "        except Exception as e:\n"
        '            self._alerta(contexto, f"Erro ao aplicar {self.id}: {e}", nivel="AVISO")\n'
        "        return contexto\n\n\n"
        f"INSIGHT A CODIFICAR:\n"
        f"- Situação: {titulo}\n"
        f"- Descrição: {descricao}\n"
        f"- Correção da perita: {correcao}\n"
        f"- Base legal: {base_legal}\n"
        f"- Nível: {nivel}\n\n"
        "INSTRUÇÕES:\n"
        "1. Substitua o bloco 'pass' por lógica REAL que detecta a violação descrita acima.\n"
        f'3. Chame self._alerta() com nivel="{nivel}" quando a condição for detectada.\n'
        "6. Retorne APENAS o código Python puro, sem blocos markdown (sem ```python).\n"
    )

    raw, model = chamar_gemini_para_codify(prompt)
    if raw.startswith("```"):
        lines = raw.split("\n")[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return raw, model


def _gerar_exemplo_skill_gemini(
    aprendizado: dict,
    numero_processo: str,
    chamar_gemini_para_codify: Callable[[str], tuple],
) -> tuple:
    """Gera bloco de Engenharia Reversa para o skill. Retorna (bloco_markdown, model_used)."""
    titulo = aprendizado.get("titulo", "")
    descricao = aprendizado.get("descricao", "")
    correcao = aprendizado.get("correcao", "")
    base_legal = aprendizado.get("base_legal", "")
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")

    prompt = (
        "Você é perita calculista trabalhista especializada em documentar padrões de erro e correção.\n\n"
        "Crie uma seção de 'Engenharia Reversa' em Markdown para um arquivo de skill de IA.\n\n"
        f"INSIGHT DA PERITA:\n"
        f"- Situação identificada: {titulo}\n"
        f"- Descrição da discrepância: {descricao}\n"
        f"- Correção aplicada: {correcao}\n"
        f"- Base legal: {base_legal}\n"
        f"- Processo de referência: {numero_processo or 'não informado'}\n\n"
        "GERE EXATAMENTE o bloco Markdown abaixo (substitua os conteúdos pelos dados do insight):\n\n"
        "---\n"
        f"## Engenharia Reversa — {titulo[:60]}\n"
        f"<!-- Laboratório de Aprendizado | {timestamp} | Processo: {numero_processo or 'N/A'} -->\n\n"
        "### Padrão de erro identificado\n"
        "[descreva o que geralmente está errado no cálculo ou na interpretação]\n\n"
        "### Como identificar na sentença\n"
        "[palavras-chave, padrões textuais, campos a verificar]\n\n"
        "### Correção correta\n"
        "[como a perita corrige; o que deve ser feito]\n\n"
        "### Base legal\n"
        f"[fundamento normativo: {base_legal}]\n\n"
        "4. Retorne APENAS o bloco Markdown, sem prefácio ou comentário externo.\n"
    )

    raw, model = chamar_gemini_para_codify(prompt)
    return raw, model


def _registrar_log_enriquecido(
    aprendizado: dict,
    numero_processo: str,
    caminhos: list,
    learning_log_path: str,
    model_used_rule: Optional[str] = None,
    model_used_skill: Optional[str] = None,
) -> None:
    """Registra o aprendizado no learning_log (JSONL) com formato enriquecido."""
    registro = {
        "data": datetime.now().isoformat(),
        "processo_id": numero_processo or "desconhecido",
        "tipo": aprendizado.get("tipo"),
        "titulo": aprendizado.get("titulo"),
        "discrepancia": aprendizado.get("descricao") or aprendizado.get("titulo") or "",
        "correcao_aplicada": aprendizado.get("correcao") or "não especificado",
        "base_legal": aprendizado.get("base_legal"),
        "caminhos_gerados": caminhos,
        "model_used_rule": model_used_rule,
        "model_used_skill": model_used_skill,
    }
    try:
        with open(learning_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except Exception as e:
        _logger.error(
            "codify_log_write_failed",
            extra={"error": str(e)},
        )


def codify_insight(
    aprendizado: dict,
    numero_processo: str = "",
    conteudo_editado: Optional[str] = None,
    *,
    rules_dir: str,
    skills_dir: str,
    learning_log_path: str,
    chamar_gemini_para_codify: Callable[[str], tuple],
) -> dict:
    """
    Consolida o aprendizado em duas camadas: (1) Lógica — regra Python + skill;
    (2) Log — learning_log (JSONL). Retorna dict com salvo, caminhos, msg, etc.
    """
    tipo = aprendizado.get("tipo", "playbook")
    titulo = aprendizado.get("titulo", "aprendizado")
    descricao = aprendizado.get("descricao", "")
    base_legal = aprendizado.get("base_legal", "")
    correcao = aprendizado.get("correcao", "")

    resultado: Dict[str, Any] = {
        "salvo": False,
        "tipo": tipo,
        "caminhos": [],
        "model_used_rule": None,
        "model_used_skill": None,
    }

    try:
        os.makedirs(rules_dir, exist_ok=True)
        os.makedirs(skills_dir, exist_ok=True)
        skill_path = os.path.join(skills_dir, "sentenca_ordinaria.md")
        preview_aprendizado = learning_io.preview_aprendizado

        if tipo == "regra":
            slug = re.sub(r"[^\w]", "_", titulo.lower())[:40]
            slug = re.sub(r"_+", "_", slug).strip("_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"lab_{slug}_{timestamp}.py"
            caminho_regra = os.path.join(rules_dir, nome_arquivo)

            if conteudo_editado is not None:
                codigo_python = conteudo_editado
                resultado["model_used_rule"] = "user_edited"
            else:
                codigo_python, model_r = _gerar_regra_python_gemini(
                    aprendizado, chamar_gemini_para_codify
                )
                resultado["model_used_rule"] = model_r
                if not codigo_python.strip():
                    codigo_python = preview_aprendizado(aprendizado)["conteudo"]
                    resultado["model_used_rule"] = "template_fallback"

            with open(caminho_regra, "w", encoding="utf-8") as f:
                f.write(codigo_python)
            resultado["caminhos"].append(caminho_regra)
            resultado["caminho"] = caminho_regra

            if os.path.exists(skill_path):
                exemplo_md, model_s = _gerar_exemplo_skill_gemini(
                    aprendizado, numero_processo, chamar_gemini_para_codify
                )
                resultado["model_used_skill"] = model_s
                if not exemplo_md.strip():
                    ts_fmt = datetime.now().strftime("%d/%m/%Y %H:%M")
                    exemplo_md = (
                        f"\n---\n## Engenharia Reversa — {titulo}\n"
                        f"<!-- Laboratório {ts_fmt} | Processo: {numero_processo or 'N/A'} -->\n\n"
                        f"**Base legal:** {base_legal}\n**Situação:** {descricao}\n**Correção:** {correcao}\n"
                    )
                    resultado["model_used_skill"] = "template_fallback"
                with open(skill_path, "a", encoding="utf-8") as f:
                    f.write("\n" + exemplo_md)
                resultado["caminhos"].append(skill_path)
                resultado["caminho_skill"] = skill_path

        else:
            if conteudo_editado is not None:
                bloco_md = conteudo_editado
                resultado["model_used_skill"] = "user_edited"
            else:
                bloco_md, model_s = _gerar_exemplo_skill_gemini(
                    aprendizado, numero_processo, chamar_gemini_para_codify
                )
                resultado["model_used_skill"] = model_s
                if not bloco_md.strip():
                    bloco_md = preview_aprendizado(aprendizado)["conteudo"]
                    resultado["model_used_skill"] = "template_fallback"

            if os.path.exists(skill_path):
                with open(skill_path, "a", encoding="utf-8") as f:
                    f.write("\n" + bloco_md)
            resultado["caminhos"].append(skill_path)
            resultado["caminho"] = skill_path

        _registrar_log_enriquecido(
            aprendizado=aprendizado,
            numero_processo=numero_processo,
            caminhos=resultado["caminhos"],
            learning_log_path=learning_log_path,
            model_used_rule=resultado["model_used_rule"],
            model_used_skill=resultado["model_used_skill"],
        )
        resultado["salvo"] = True
        nomes = " + ".join(
            "/".join(c.replace("\\", "/").split("/")[-2:]) for c in resultado["caminhos"]
        )
        resultado["msg"] = (
            f"Aprendizado consolidado: Log registrado e Manual de Instruções (Skills) "
            f"atualizado com sucesso. Arquivo(s): {nomes}"
        )
        return resultado

    except Exception as e:
        _logger.error(
            "codify_critical_error",
            extra={"error": str(e)},
        )
        return {
            "salvo": False,
            "tipo": tipo,
            "caminhos": [],
            "msg": f"Erro ao codificar insight: {e}",
        }


def evaluate_shadow_rules(
    relatorio: Dict,
    kb=None,
    user_id: Optional[str] = None,
) -> Dict:
    """
    Sistema de Punição / Autocorreção: compara predições das regras shadow do KB
    contra as discrepâncias reais do relatório. Acerto → +1; Punição → -1 (shadow com score <= -1 deletada).
    """
    if kb is None:
        from services.knowledge_base import KnowledgeBase
        from services.request_context import current_tenant_id

        tid = user_id or current_tenant_id()
        if not tid:
            _logger.warning("evaluate_shadow_rules_sem_tenant", extra={"tenant_id": "anonimo"})
            tid = "anonimo"
        kb = KnowledgeBase(tenant_id=tid)

    shadow_rules = kb.get_regras_shadow()
    if not shadow_rules:
        return {"acertos": 0, "punicoes": 0, "rules_updated": []}

    sentenca = relatorio.get("sentenca") or {}
    liquidacao = relatorio.get("liquidacao") or {}
    has_sentenca = bool((sentenca.get("verbas") or []))
    has_liquidacao = bool((liquidacao.get("verbas_calculadas") or []))
    if not (has_sentenca and has_liquidacao):
        _logger.info(
            "kb_modo_observacao_ativo",
            extra={"motivo": "sentenca_ou_liquidacao_incompletas"},
        )
        return {"acertos": 0, "punicoes": 0, "rules_updated": []}

    numero_processo = relatorio.get("numero_processo", "")
    discrepancias = relatorio.get("discrepancias") or []
    tipos_reais = {d.get("tipo", "") for d in discrepancias}
    verbas_ausentes_reais = set()
    for d in discrepancias:
        texto = (d.get("juiz_disse") or "").lower()
        match = re.search(r"deferido:\s*(.+)", texto)
        if match:
            verbas_ausentes_reais.add(match.group(1).strip())

    acertos = 0
    punicoes = 0
    updated = []

    for regra in shadow_rules:
        cond = regra.get("condicao") or {}
        tipo = cond.get("tipo", "")

        previu_problema = False
        problema_confirmado = False

        if tipo == "verba_ausente":
            verba_prev = (cond.get("verba") or "").lower().strip()
            previu_problema = bool(verba_prev)
            problema_confirmado = (
                "verba_ausente" in tipos_reais
                and any(verba_prev in v or v in verba_prev for v in verbas_ausentes_reais)
            )
        elif tipo in ("indice_ausente", "campo_ausente", "campo_diferente"):
            previu_problema = True
            problema_confirmado = tipo in tipos_reais or "indice_correcao" in tipos_reais

        if previu_problema:
            rule_id = regra["rule_id"]
            if problema_confirmado:
                kb.marcar_acerto(rule_id, numero_processo)
                acertos += 1
                updated.append({"rule_id": rule_id, "resultado": "acerto"})
            else:
                kb.marcar_punicao(rule_id)
                punicoes += 1
                updated.append({"rule_id": rule_id, "resultado": "punicao"})

    print(
        f"[KB] Avaliacao shadow: {acertos} acerto(s), {punicoes} punicao(oes) em {len(shadow_rules)} regra(s) shadow",
        flush=True,
    )
    return {"acertos": acertos, "punicoes": punicoes, "rules_updated": updated}


def processar_aprendizado_autonomo(
    relatorio: Dict,
    numero_processo: str = "",
    user_id: Optional[str] = None,
    *,
    extrair_logica_correcao_gemini: Callable[[Dict], List[Dict]],
    filtrar_logicas_verba_ausente_falsas: Callable[[List[Dict], Dict], List[Dict]],
) -> Dict:
    """
    Ponto de entrada do aprendizado autônomo. Extrai hipóteses via Gemini, atualiza
    o Knowledge Base (Multi-tenancy via user_id) e avalia regras shadow.
    """
    from services.knowledge_base import KnowledgeBase
    from services.request_context import current_tenant_id

    kb = KnowledgeBase(tenant_id=user_id or current_tenant_id())
    numero = numero_processo or relatorio.get("numero_processo", "")

    logicas = extrair_logica_correcao_gemini(relatorio)
    logicas = filtrar_logicas_verba_ausente_falsas(logicas, relatorio)
    resultados_criacao = []
    for logica in logicas:
        resultado = kb.adicionar_ou_incrementar(logica, numero)
        resultados_criacao.append(resultado)

    resultados_avaliacao = evaluate_shadow_rules(relatorio, kb=kb)

    criadas = sum(1 for r in resultados_criacao if r.get("acao") == "criada")
    incrementadas = sum(1 for r in resultados_criacao if r.get("acao") == "incrementada")
    ativadas = sum(1 for r in resultados_criacao if r.get("acao") == "ativada")

    print(
        f"[KB] Aprendizado autonomo: {criadas} criada(s), {incrementadas} incrementada(s), {ativadas} ativada(s)",
        flush=True,
    )

    return {
        "hipoteses_extraidas": len(logicas),
        "criadas": criadas,
        "incrementadas": incrementadas,
        "ativadas": ativadas,
        "avaliacao_shadow": resultados_avaliacao,
        "stats_kb": kb.stats(),
    }


__all__ = [
    "codify_insight",
    "processar_aprendizado_autonomo",
    "evaluate_shadow_rules",
]
