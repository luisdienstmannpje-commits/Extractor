"""
learning_io.py — Camada de persistência e I/O do Laboratório de Aprendizado.

Funções extraídas de learning_engine.py (Passo 1 da refatoração modular):
  - preview_aprendizado: conteúdo que seria gravado, sem gravar.
  - salvar_aprendizado: persiste regra/playbook e registra no log.
  - _salvar_rascunho_regra: grava arquivo .py em legal_engine/rules/.
  - _salvar_few_shot / _salvar_insight_em_markdown: append em skills/sentenca_ordinaria.md.
  - _registrar_log / _registrar_no_log_de_aprendizado: append em learning_log.jsonl.

Nota: _gerar_checksum_dados e _extrair_conteudo_pjc_zip não existem no codebase atual;
      foram referenciados no protocolo de refatoração para uma eventual implementação futura.
"""
from __future__ import annotations

import json
import os
import re
import textwrap
from datetime import datetime
from typing import Any, Dict, Optional

# ── Caminhos de saída (espelho do learning_engine para desacoplamento) ─────
_HERE = os.path.dirname(__file__)
_BACKEND = os.path.abspath(os.path.join(_HERE, "..", ".."))
_SKILLS_DIR = os.path.join(_BACKEND, "skills")
_RULES_DIR = os.path.join(_BACKEND, "services", "legal_engine", "rules")
_LEARNING_LOG = os.path.join(_BACKEND, "learning_log.jsonl")

# Export para learning_engine._registrar_log_enriquecido e outros consumidores
LEARNING_LOG_PATH = _LEARNING_LOG


def preview_aprendizado(aprendizado: Dict) -> Dict[str, Any]:
    """
    Retorna o conteúdo exato que seria gravado em disco, sem gravar nada.
    Usado pela tela de pré-visualização antes de confirmar o salvamento.

    Retorna:
        {
          "tipo":       "regra" | "playbook",
          "destino":    caminho relativo do arquivo de destino,
          "conteudo":   string com o conteúdo completo a ser gravado,
          "linguagem":  "python" | "markdown",
          "nome_arquivo": nome do arquivo (para regras),
        }
    """
    tipo = aprendizado.get("tipo", "playbook")
    titulo = aprendizado.get("titulo", "aprendizado")
    base_legal = aprendizado.get("base_legal", "")
    descricao = aprendizado.get("descricao", "")
    correcao = aprendizado.get("correcao", "")

    if tipo == "regra":
        slug = re.sub(r"[^\w]", "_", titulo.lower())[:40]
        slug = re.sub(r"_+", "_", slug).strip("_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"lab_{slug}_{timestamp}.py"
        prioridade = aprendizado.get("prioridade_sugerida", 50)

        conteudo = textwrap.dedent(f'''
            """
            {nome_arquivo} — RASCUNHO GERADO PELO LABORATÓRIO DE APRENDIZADO

            Título:      {titulo}
            Base legal:  {base_legal}
            Gerado em:   {datetime.now().isoformat()}

            ATENÇÃO: Revise o método `aplicar` antes de usar em produção.
            Para ativar: renomeie sem prefixo "lab_" e implemente a lógica.
            """
            from __future__ import annotations

            from services.legal_engine.rule_base import ContextoJuridico, LegalRule


            class LabRegra{timestamp.replace("_", "")}Rule(LegalRule):
                """
                {descricao}

                Correção identificada pela perita:
                {correcao}
                """

                id = "LAB_{slug.upper()}_{timestamp.upper()}"
                titulo = "{titulo}"
                base_legal = "{base_legal}"
                prioridade = {prioridade}
                descricao = "{descricao}"

                def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
                    try:
                        # TODO: implemente a condição de acionamento desta regra.
                        # Exemplo:
                        #   if not contexto.indice_correcao:
                        #       self._alerta(contexto, "Índice ausente", nivel="ERRO")
                        pass
                        self._registrar(contexto)
                    except Exception as e:
                        self._alerta(
                            contexto,
                            f"Erro ao aplicar regra {{self.id}}: {{e}}",
                            nivel="AVISO",
                        )
                    return contexto
        ''').lstrip()

        return {
            "tipo": tipo,
            "destino": f"services/legal_engine/rules/{nome_arquivo}",
            "nome_arquivo": nome_arquivo,
            "conteudo": conteudo,
            "linguagem": "python",
        }

    else:  # playbook
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        conteudo = textwrap.dedent(f"""
            ---
            ## Exemplo de Aprendizado — {timestamp}
            <!-- Adicionado automaticamente pelo Laboratório de Aprendizado -->

            **Fundamento jurídico:** {base_legal}
            **Situação identificada:** {titulo}

            **Descrição:**
            {descricao}

            <!-- Revisar e expandir com trecho real da sentença se necessário -->
        """).lstrip()

        return {
            "tipo": tipo,
            "destino": "skills/sentenca_ordinaria.md",
            "nome_arquivo": "sentenca_ordinaria.md",
            "conteudo": conteudo,
            "linguagem": "markdown",
        }


def _salvar_rascunho_regra(
    titulo: str,
    base_legal: str,
    descricao: str,
    correcao: str,
    aprendizado: dict,
) -> str:
    """Gera um arquivo .py com a estrutura padrão de LegalRule (rascunho para revisão)."""
    slug = re.sub(r"[^\w]", "_", titulo.lower())[:40]
    slug = re.sub(r"_+", "_", slug).strip("_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"lab_{slug}_{timestamp}.py"
    caminho = os.path.join(_RULES_DIR, nome_arquivo)

    prioridade = aprendizado.get("prioridade_sugerida", 50)
    nivel = aprendizado.get("nivel_sugerido", "AVISO")

    conteudo = textwrap.dedent(f'''
        """
        {nome_arquivo} — RASCUNHO GERADO PELO LABORATÓRIO DE APRENDIZADO

        Título:      {titulo}
        Base legal:  {base_legal}
        Gerado em:   {datetime.now().isoformat()}

        ATENÇÃO: Este arquivo é um RASCUNHO. Revise antes de usar em produção.
        Para ativar: renomeie para snake_case sem prefixo "lab_" e ajuste a lógica
        do método `aplicar`.
        """
        from __future__ import annotations

        from services.legal_engine.rule_base import ContextoJuridico, LegalRule


        class LabRegra{timestamp.replace("_", "")}Rule(LegalRule):
            """
            {descricao}

            Correção identificada pela perita:
            {correcao}
            """

            id = "LAB_{slug.upper()}_{timestamp.upper()}"
            titulo = "{titulo}"
            base_legal = "{base_legal}"
            prioridade = {prioridade}
            descricao = "{descricao}"

            def aplicar(self, contexto: ContextoJuridico) -> ContextoJuridico:
                try:
                    # TODO: implementar condição de acionamento com base na análise
                    # Exemplo: if not contexto.campo_x: self._alerta(...)
                    pass
                    self._registrar(contexto)
                except Exception as e:
                    self._alerta(
                        contexto,
                        f"Erro ao aplicar regra {{self.id}}: {{e}}",
                        nivel="AVISO",
                    )
                return contexto
    ''').lstrip()

    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)

    print(f"[LEARNING] Rascunho de regra criado: {caminho}", flush=True)
    return caminho


def _salvar_few_shot(
    titulo: str,
    base_legal: str,
    descricao: str,
    numero_processo: str,
) -> None:
    """Adiciona um bloco few-shot ao final de skills/sentenca_ordinaria.md."""
    skill_path = os.path.join(_SKILLS_DIR, "sentenca_ordinaria.md")
    if not os.path.exists(skill_path):
        print(f"[LEARNING] Skill nao encontrada: {skill_path}", flush=True)
        return

    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    bloco = textwrap.dedent(f"""

        ---
        ## Exemplo de Aprendizado — {timestamp}
        <!-- Adicionado automaticamente pelo Laboratório de Aprendizado -->

        **Processo de referência:** {numero_processo or "não informado"}
        **Fundamento jurídico:** {base_legal}
        **Situação identificada:** {titulo}

        **Descrição:**
        {descricao}

        <!-- Revisar e expandir com trecho real da sentença se necessário -->
    """)

    with open(skill_path, "a", encoding="utf-8") as f:
        f.write(bloco)

    print(f"[LEARNING] Few-shot adicionado a: {skill_path}", flush=True)


# Alias documentado no protocolo de refatoração
_salvar_insight_em_markdown = _salvar_few_shot


def _registrar_log(aprendizado: dict, numero_processo: str, caminho: str) -> None:
    """Registra o aprendizado em learning_log.jsonl (append-only). Mantido para compat."""
    registro = {
        "ts": datetime.now().isoformat(),
        "numero_processo": numero_processo,
        "tipo": aprendizado.get("tipo"),
        "titulo": aprendizado.get("titulo"),
        "base_legal": aprendizado.get("base_legal"),
        "caminho_gerado": caminho,
    }
    try:
        with open(_LEARNING_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[LEARNING] Erro ao registrar log: {e}", flush=True)


# Alias documentado no protocolo de refatoração
_registrar_no_log_de_aprendizado = _registrar_log


def salvar_aprendizado(
    aprendizado: Dict,
    numero_processo: str = "",
    conteudo_editado: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Salva o aprendizado selecionado pelo usuário.

    - tipo "regra"    → cria rascunho de arquivo .py em legal_engine/rules/
    - tipo "playbook" → adiciona bloco few-shot em skills/sentenca_ordinaria.md
    - Sempre → registra no learning_log.jsonl

    Se `conteudo_editado` for fornecido, grava esse conteúdo diretamente
    em vez de regenerar (usado após a tela de pré-visualização com edição).

    Retorna: {"salvo": bool, "tipo": str, "caminho": str, "msg": str}
    """
    tipo = aprendizado.get("tipo", "playbook")
    titulo = aprendizado.get("titulo", "aprendizado")
    base_legal = aprendizado.get("base_legal", "")
    descricao = aprendizado.get("descricao", "")
    correcao = aprendizado.get("correcao", "")

    resultado: Dict[str, Any] = {"salvo": False, "tipo": tipo}

    try:
        if tipo == "regra":
            if conteudo_editado is not None:
                slug = re.sub(r"[^\w]", "_", titulo.lower())[:40]
                slug = re.sub(r"_+", "_", slug).strip("_")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nome_arquivo = f"lab_{slug}_{timestamp}.py"
                caminho = os.path.join(_RULES_DIR, nome_arquivo)
                with open(caminho, "w", encoding="utf-8") as f:
                    f.write(conteudo_editado)
                print(f"[LEARNING] Regra (editada) salva: {caminho}", flush=True)
            else:
                caminho = _salvar_rascunho_regra(titulo, base_legal, descricao, correcao, aprendizado)
            resultado.update({"salvo": True, "caminho": caminho, "msg": f"Rascunho de regra criado: {caminho}"})

        elif tipo == "playbook":
            if conteudo_editado is not None:
                skill_path = os.path.join(_SKILLS_DIR, "sentenca_ordinaria.md")
                with open(skill_path, "a", encoding="utf-8") as f:
                    f.write("\n" + conteudo_editado)
                print(f"[LEARNING] Playbook (editado) salvo em: {skill_path}", flush=True)
                caminho = skill_path
            else:
                _salvar_few_shot(titulo, base_legal, descricao, numero_processo)
                caminho = os.path.join(_SKILLS_DIR, "sentenca_ordinaria.md")
            resultado.update({"salvo": True, "caminho": caminho, "msg": "Exemplo adicionado ao playbook sentenca_ordinaria.md"})

        _registrar_log(aprendizado, numero_processo, resultado.get("caminho", ""))
        return resultado

    except Exception as e:
        return {"salvo": False, "tipo": tipo, "msg": f"Erro ao salvar: {e}"}


__all__ = [
    "preview_aprendizado",
    "salvar_aprendizado",
    "LEARNING_LOG_PATH",
    "_salvar_insight_em_markdown",
    "_registrar_no_log_de_aprendizado",
]
