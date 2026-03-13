"""
learning_engine.py — Laboratório de Aprendizado da Perita

Fluxo: recebe 3 arquivos (Sentença PDF, Liquidação PDF/.PJC, Manifestação DOCX),
processa cada um de forma independente e gera um Relatório de Discrepância:

  "O juiz disse A, a empresa calculou B, a Juliana corrigiu para C usando a Súmula D"

Saída:
  - relatorio: dict com seções (sentenca, liquidacao, manifestacao, discrepancias)
  - aprendizados: list[dict] — cada item é um aprendizado extraível como regra/playbook
  - metadados: processo, data, origem

Salvamento do aprendizado (sem guardar arquivos):
  - Adiciona exemplo few-shot ao skills/sentenca_ordinaria.md
  - Gera arquivo de nova regra em services/legal_engine/rules/ (rascunho Python)
  - Registra aprendizado em learning_log.json (JSONL) para audit trail

SEGURANÇA: Nenhum arquivo binário é persistido. Apenas a lógica extraída é salva.
"""
from __future__ import annotations

import json
import os
import re
import textwrap
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional

# ── Caminhos de saída ─────────────────────────────────────────────────────────
_HERE = os.path.dirname(__file__)
_BACKEND = os.path.abspath(os.path.join(_HERE, ".."))
_SKILLS_DIR = os.path.join(_BACKEND, "skills")
_RULES_DIR = os.path.join(_BACKEND, "services", "legal_engine", "rules")
_LEARNING_LOG = os.path.join(_BACKEND, "learning_log.jsonl")


# ── Parser de DOCX (sem dependência externa) ─────────────────────────────────

def _extrair_texto_docx(docx_bytes: bytes) -> str:
    """
    Extrai texto puro de um DOCX (ZIP com word/document.xml).
    Sem dependência de python-docx — usa zipfile + minidom.
    """
    try:
        from xml.dom.minidom import parseString

        with zipfile.ZipFile(__import__("io").BytesIO(docx_bytes)) as z:
            if "word/document.xml" not in z.namelist():
                return ""
            xml_content = z.read("word/document.xml")

        dom = parseString(xml_content)
        # Coleta todos os nós <w:t> (texto) em ordem
        paragrafos = []
        for para in dom.getElementsByTagNameNS("*", "p"):
            textos = []
            for t in para.getElementsByTagNameNS("*", "t"):
                if t.firstChild:
                    textos.append(t.firstChild.nodeValue or "")
            linha = "".join(textos).strip()
            if linha:
                paragrafos.append(linha)

        return "\n".join(paragrafos)
    except Exception as e:
        print(f"[LEARNING] Erro ao extrair DOCX: {e}")
        return ""


# ── Extração da Sentença ─────────────────────────────────────────────────────

def _extrair_sentenca(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Reutiliza o pipeline existente para extrair dados da sentença.
    Retorna apenas os dados estruturados (não gera cache, não debita crédito).
    """
    try:
        from services.sentence_finder import extract_sentence_from_pdf
        from services.ai_client import extract_data_with_gemini
        from services.learning_skill_loader import carregar_skill_para_lab

        texto, doc_type = extract_sentence_from_pdf(pdf_bytes)
        if not texto.strip():
            return {"erro": "PDF sem texto legível", "doc_type": "desconhecido"}

        playbook = carregar_skill_para_lab(doc_type)
        ai_result = extract_data_with_gemini(texto, playbook=playbook)

        return {
            "doc_type": doc_type,
            "dados": ai_result.get("data") or {},
            "model_used": ai_result.get("model_used"),
            "erro": ai_result.get("error"),
        }
    except Exception as e:
        return {"erro": str(e), "doc_type": "desconhecido"}


# ── Extração da Liquidação (PDF ou .PJC) ─────────────────────────────────────

def _extrair_liquidacao(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Extrai parâmetros da liquidação.
    - Se .pjc / .xml  → PjcParser
    - Se .pdf         → extração de texto simples + regex para parâmetros-chave
    """
    fname = (filename or "").lower()

    if fname.endswith(".pjc") or fname.endswith(".xml"):
        try:
            from services.pjc_parser import PjcParser
            parser = PjcParser.from_string(file_bytes)
            dados = parser.extrair_dados_basicos()
            return {
                "tipo": "pjc",
                "indice_correcao": dados.indice_trabalhista,
                "juros_mora": dados.juros_trabalhistas,
                "divisor_horas": dados.divisor_horas,
                "verbas_calculadas": dados.nomes_verbas,
                "erro": None,
            }
        except Exception as e:
            return {"tipo": "pjc", "erro": str(e)}

    if fname.endswith(".pdf"):
        try:
            import pdfplumber
            import io
            texto = ""
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages[:10]:
                    texto += (page.extract_text() or "") + "\n"

            return {
                "tipo": "pdf",
                "texto_bruto": texto[:3000],
                "verbas_calculadas": _regex_verbas(texto),
                "indice_correcao": _regex_indice(texto),
                "juros_mora": _regex_juros(texto),
                "divisor_horas": _regex_divisor(texto),
                "erro": None,
            }
        except Exception as e:
            return {"tipo": "pdf", "erro": str(e)}

    return {"tipo": "desconhecido", "erro": "Formato não suportado"}


def _regex_verbas(texto: str) -> List[str]:
    padroes = [
        r"horas?\s*extras?", r"adicional\s*noturno", r"intervalo\s*intrajornada",
        r"insalubridade", r"periculosidade", r"f[eé]rias", r"13[°º]?\s*sal[aá]rio",
        r"aviso\s*pr[eé]vio", r"saldo\s*de\s*sal[aá]rio", r"multa\s*art\.?\s*467",
        r"multa\s*art\.?\s*477", r"dano\s*moral", r"FGTS"
    ]
    encontradas = []
    for p in padroes:
        if re.search(p, texto, re.IGNORECASE) and p not in encontradas:
            encontradas.append(p)
    return encontradas


def _regex_indice(texto: str) -> Optional[str]:
    m = re.search(r"\b(IPCAE|SELIC|TR|IPCA[_\-]?E|TRD)\b", texto, re.IGNORECASE)
    return m.group(0).upper() if m else None


def _regex_juros(texto: str) -> Optional[str]:
    m = re.search(r"\b(TRD_SIMPLES|SELIC\s*simples|juros\s+de\s+\d[\d,\.]+\s*%)\b", texto, re.IGNORECASE)
    return m.group(0) if m else None


def _regex_divisor(texto: str) -> Optional[str]:
    m = re.search(r"\b(150|180|200|220)\s*(?:h(?:oras?)?|\/\s*m[eê]s)?\b", texto, re.IGNORECASE)
    return m.group(1) if m else None


# ── Extração da Manifestação (DOCX) ─────────────────────────────────────────

def _extrair_manifestacao(docx_bytes: bytes) -> Dict[str, Any]:
    """
    Extrai texto da manifestação e identifica:
    - Fundamentos jurídicos mencionados (súmulas, OJs, artigos CLT, ADC)
    - Discrepâncias que a perita levantou
    - Correções propostas
    """
    texto = _extrair_texto_docx(docx_bytes)
    if not texto:
        return {"erro": "Não foi possível extrair texto do DOCX", "texto": ""}

    fundamentos = _extrair_fundamentos_juridicos(texto)
    discrepancias_levantadas = _extrair_discrepancias_perita(texto)

    return {
        "texto_bruto": texto[:4000],
        "fundamentos_juridicos": fundamentos,
        "discrepancias_levantadas": discrepancias_levantadas,
        "erro": None,
    }


def _extrair_fundamentos_juridicos(texto: str) -> List[str]:
    """Identifica referências jurídicas mencionadas na manifestação."""
    padroes = [
        (r"S[uú]mula\s+n[°º]?\s*\d+\s+(?:do\s+)?TST", "Súmula TST"),
        (r"S[uú]mula\s+n[°º]?\s*\d+\s+(?:do\s+)?STF", "Súmula STF"),
        (r"OJ\s+n[°º]?\s*\d+", "OJ"),
        (r"art(?:igo)?\.?\s*\d+[,\s\w]*(?:da\s+CLT|CLT)", "Art. CLT"),
        (r"ADC\s+\d+", "ADC"),
        (r"S[uú]mula\s+n[°º]?\s*\d+", "Súmula"),
        (r"Lei\s+n[°º]?\s*[\d\.]+", "Lei"),
        (r"Decreto[- ]Lei\s+n[°º]?\s*[\d\.]+", "Decreto-Lei"),
    ]
    encontrados = []
    for padrao, tipo in padroes:
        for m in re.finditer(padrao, texto, re.IGNORECASE):
            ref = m.group(0).strip()
            if ref not in encontrados:
                encontrados.append(ref)
    return encontrados[:20]


def _extrair_discrepancias_perita(texto: str) -> List[str]:
    """
    Tenta identificar frases que descrevem divergências levantadas pela perita.
    Heurística: sentenças com palavras de contraste jurídico.
    """
    palavras_chave = [
        r"diverge?\w*", r"incorreto\w*", r"equivocado\w*", r"erro\w*",
        r"deveria\w*", r"correto\w*", r"corrij\w*", r"recalcul\w*",
        r"indevido\w*", r"desconsider\w*", r"incluir\w*", r"acrescentar\w*",
    ]
    regex = re.compile("|".join(palavras_chave), re.IGNORECASE)
    linhas = texto.split("\n")
    discrepancias = []
    for linha in linhas:
        linha = linha.strip()
        if len(linha) > 20 and regex.search(linha):
            discrepancias.append(linha[:250])
        if len(discrepancias) >= 10:
            break
    return discrepancias


# ── Geração do Relatório de Discrepância ─────────────────────────────────────

def gerar_relatorio_discrepancia(
    dados_sentenca: Dict,
    dados_liquidacao: Dict,
    dados_manifestacao: Dict,
) -> Dict[str, Any]:
    """
    Compara os 3 conjuntos de dados e gera o relatório de discrepâncias:
    "O juiz disse A, a empresa calculou B, a Juliana corrigiu para C usando D"
    """
    discrepancias = []

    # 1. Verbas deferidas na sentença vs verbas calculadas na liquidação
    verbas_sentenca = [
        (v.get("nome") or "") for v in (dados_sentenca.get("dados") or {}).get("verbas_deferidas", [])
        if isinstance(v, dict)
    ]
    verbas_liquidacao = dados_liquidacao.get("verbas_calculadas") or []
    verbas_liq_norm = [str(v or "").lower() for v in verbas_liquidacao]

    for verba in verbas_sentenca:
        nome_norm = (verba or "").lower()
        presente = any(nome_norm in v or v in nome_norm for v in verbas_liq_norm)
        if not presente and verba:
            discrepancias.append({
                "tipo": "verba_ausente",
                "nivel": "ERRO",
                "juiz_disse": f"Deferido: {verba}",
                "empresa_calculou": "Verba ausente no arquivo de liquidação",
                "juliana_corrigiu": _sugerir_correcao_verba(verba, dados_manifestacao),
                "fundamento": _buscar_fundamento_para_verba(verba, dados_manifestacao),
            })

    # 2. Índice de correção
    indice_sentenca = (dados_sentenca.get("dados") or {}).get("indice_correcao") or ""
    indice_liq = dados_liquidacao.get("indice_correcao") or ""
    if indice_sentenca and indice_liq:
        n_sent = indice_sentenca.upper().replace("-", "").replace("_", "")
        n_liq  = indice_liq.upper().replace("-", "").replace("_", "")
        if n_sent not in n_liq and n_liq not in n_sent:
            discrepancias.append({
                "tipo": "indice_correcao",
                "nivel": "ERRO",
                "juiz_disse": f"Índice de correção: {indice_sentenca}",
                "empresa_calculou": f"Índice utilizado no cálculo: {indice_liq}",
                "juliana_corrigiu": "Corrigir índice para o determinado na sentença",
                "fundamento": "ADC 58 / Súmula 439 TST",
            })

    # 3. Juros de mora
    juros_sentenca = (dados_sentenca.get("dados") or {}).get("juros_mora") or ""
    juros_liq = dados_liquidacao.get("juros_mora") or ""
    if juros_sentenca and juros_liq:
        if juros_sentenca.lower() not in juros_liq.lower() and juros_liq.lower() not in juros_sentenca.lower():
            discrepancias.append({
                "tipo": "juros_mora",
                "nivel": "AVISO",
                "juiz_disse": f"Juros de mora: {juros_sentenca}",
                "empresa_calculou": f"Juros no cálculo: {juros_liq}",
                "juliana_corrigiu": "Corrigir taxa de juros conforme ADC 58",
                "fundamento": "ADC 58 / Art. 39 da Lei 8.177/91",
            })

    # 4. Fundamentos da manifestação da perita → aprendizados
    aprendizados = _extrair_aprendizados(
        dados_sentenca, dados_liquidacao, dados_manifestacao, discrepancias
    )

    # Número do processo para identificação
    numero_processo = (dados_sentenca.get("dados") or {}).get("numero_processo") or "desconhecido"

    return {
        "numero_processo": numero_processo,
        "data_analise": datetime.now().isoformat(),
        "resumo": {
            "verbas_sentenca": len(verbas_sentenca),
            "verbas_liquidacao": len(verbas_liquidacao),
            "discrepancias_encontradas": len(discrepancias),
        },
        "sentenca": {
            "doc_type": dados_sentenca.get("doc_type"),
            "model_used": dados_sentenca.get("model_used"),
            "campos_chave": _campos_chave_sentenca(dados_sentenca.get("dados") or {}),
            "verbas": verbas_sentenca,
            "erro": dados_sentenca.get("erro"),
        },
        "liquidacao": {
            "tipo": dados_liquidacao.get("tipo"),
            "indice_correcao": indice_liq,
            "juros_mora": juros_liq,
            "divisor_horas": dados_liquidacao.get("divisor_horas"),
            "verbas_calculadas": verbas_liquidacao,
            "erro": dados_liquidacao.get("erro"),
        },
        "manifestacao": {
            "fundamentos_juridicos": dados_manifestacao.get("fundamentos_juridicos") or [],
            "discrepancias_levantadas": dados_manifestacao.get("discrepancias_levantadas") or [],
            "erro": dados_manifestacao.get("erro"),
        },
        "discrepancias": discrepancias,
        "aprendizados": aprendizados,
    }


def _campos_chave_sentenca(dados: dict) -> dict:
    chaves = [
        "numero_processo", "reclamante", "reclamada", "data_sentenca",
        "salario_base", "data_admissao", "data_demissao", "indice_correcao",
        "juros_mora", "divisor_horas",
    ]
    return {k: dados.get(k) for k in chaves if dados.get(k)}


def _sugerir_correcao_verba(verba: str, manifestacao: dict) -> str:
    texto = manifestacao.get("texto_bruto") or ""
    trecho = ""
    verba_norm = (verba or "").lower()
    for linha in texto.split("\n"):
        if verba_norm in (linha or "").lower() and len(linha) > 20:
            trecho = linha.strip()[:200]
            break
    if trecho:
        return f"Incluir verba conforme sentença. Trecho da manifestação: {trecho}"
    return f"Incluir {verba} no cálculo conforme determinado na sentença"


def _buscar_fundamento_para_verba(verba: str, manifestacao: dict) -> str:
    fundamentos = manifestacao.get("fundamentos_juridicos") or []
    if fundamentos:
        return "; ".join(fundamentos[:3])
    return "Verificar fundamentação na manifestação"


def _extrair_aprendizados(
    dados_sentenca: dict,
    dados_liquidacao: dict,
    dados_manifestacao: dict,
    discrepancias: list,
) -> List[Dict]:
    """
    Cada discrepância com fundamento gera um aprendizado potencial:
    - tipo "regra"    → candidato a nova regra em legal_engine/rules/
    - tipo "playbook" → candidato a exemplo few-shot no skill
    """
    aprendizados = []

    for disc in discrepancias:
        fundamento = disc.get("fundamento") or ""
        if fundamento and disc.get("nivel") == "ERRO":
            aprendizados.append({
                "tipo": "regra",
                "titulo": f"Discrepância: {disc['tipo']}",
                "descricao": disc["juiz_disse"],
                "correcao": disc["juliana_corrigiu"],
                "base_legal": fundamento,
                "nivel_sugerido": "ERRO",
                "prioridade_sugerida": 40,
            })

    # Fundamentos da manifestação que não são cobertos por discrepâncias explícitas
    fundamentos_doc = dados_manifestacao.get("fundamentos_juridicos") or []
    tipos_cobertos = {d.get("fundamento") for d in discrepancias}
    for fund in fundamentos_doc:
        if fund not in tipos_cobertos:
            aprendizados.append({
                "tipo": "playbook",
                "titulo": f"Fundamento jurídico identificado: {fund}",
                "descricao": "Fundamento mencionado na manifestação da perita",
                "base_legal": fund,
            })

    return aprendizados


# ── Pré-visualização do Aprendizado (sem gravar) ─────────────────────────────

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
    tipo      = aprendizado.get("tipo", "playbook")
    titulo    = aprendizado.get("titulo", "aprendizado")
    base_legal = aprendizado.get("base_legal", "")
    descricao  = aprendizado.get("descricao", "")
    correcao   = aprendizado.get("correcao", "")

    if tipo == "regra":
        slug      = re.sub(r"[^\w]", "_", titulo.lower())[:40]
        slug      = re.sub(r"_+", "_", slug).strip("_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"lab_{slug}_{timestamp}.py"
        prioridade   = aprendizado.get("prioridade_sugerida", 50)

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


# ── Salvamento do Aprendizado ─────────────────────────────────────────────────

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
    tipo      = aprendizado.get("tipo", "playbook")
    titulo    = aprendizado.get("titulo", "aprendizado")
    base_legal = aprendizado.get("base_legal", "")
    descricao  = aprendizado.get("descricao", "")
    correcao   = aprendizado.get("correcao", "")

    resultado: Dict[str, Any] = {"salvo": False, "tipo": tipo}

    try:
        if tipo == "regra":
            if conteudo_editado is not None:
                # Grava o conteúdo editado diretamente
                slug      = re.sub(r"[^\w]", "_", titulo.lower())[:40]
                slug      = re.sub(r"_+", "_", slug).strip("_")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nome_arquivo = f"lab_{slug}_{timestamp}.py"
                caminho = os.path.join(_RULES_DIR, nome_arquivo)
                with open(caminho, "w", encoding="utf-8") as f:
                    f.write(conteudo_editado)
                print(f"[LEARNING] Regra (editada) salva: {caminho}")
            else:
                caminho = _salvar_rascunho_regra(titulo, base_legal, descricao, correcao, aprendizado)
            resultado.update({"salvo": True, "caminho": caminho, "msg": f"Rascunho de regra criado: {caminho}"})

        elif tipo == "playbook":
            if conteudo_editado is not None:
                skill_path = os.path.join(_SKILLS_DIR, "sentenca_ordinaria.md")
                with open(skill_path, "a", encoding="utf-8") as f:
                    f.write("\n" + conteudo_editado)
                print(f"[LEARNING] Playbook (editado) salvo em: {skill_path}")
                caminho = skill_path
            else:
                _salvar_few_shot(titulo, base_legal, descricao, numero_processo)
                caminho = os.path.join(_SKILLS_DIR, "sentenca_ordinaria.md")
            resultado.update({"salvo": True, "caminho": caminho, "msg": "Exemplo adicionado ao playbook sentenca_ordinaria.md"})

        # Audit trail em JSONL
        _registrar_log(aprendizado, numero_processo, resultado.get("caminho", ""))
        return resultado

    except Exception as e:
        return {"salvo": False, "tipo": tipo, "msg": f"Erro ao salvar: {e}"}


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

    print(f"[LEARNING] Rascunho de regra criado: {caminho}")
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
        print(f"[LEARNING] Skill não encontrada: {skill_path}")
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

    print(f"[LEARNING] Few-shot adicionado a: {skill_path}")


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
        print(f"[LEARNING] Erro ao registrar log: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# CODIFICAÇÃO DE INSIGHT — Camada dupla: Log + Lógica (Gemini)
# ══════════════════════════════════════════════════════════════════════════════

def _chamar_gemini_para_codify(prompt: str) -> tuple[str, str]:
    """
    Chama Gemini (modelo de raciocínio) para gerar conteúdo a partir de um prompt.
    Usa cascata gemini-2.5-pro → gemini-2.0-flash.
    Retorna (conteudo_gerado, model_used). Nunca lança exceção.
    """
    try:
        from google import genai as _genai
        from config import settings as _settings
        import time as _time

        _client = _genai.Client(api_key=_settings.GEMINI_API_KEY)
        cascade = ["models/gemini-2.5-pro", "gemini-2.0-flash"]

        for model in cascade:
            for attempt in range(1, 3):
                try:
                    response = _client.models.generate_content(
                        model=model,
                        contents=prompt,
                    )
                    text = (response.text or "").strip()
                    if text:
                        print(f"[CODIFY] Gerado com {model} (tentativa {attempt})")
                        return text, model
                except Exception as e:
                    err = str(e).lower()
                    if "429" in err or "quota" in err or "rate" in err:
                        _time.sleep(10 * attempt)
                        continue
                    print(f"[CODIFY] Erro em {model} tentativa {attempt}: {e}")
                    break

        print("[CODIFY] Todos os modelos falharam — retornando vazio")
        return "", "fallback"

    except Exception as e:
        print(f"[CODIFY] Erro crítico ao inicializar cliente Gemini: {e}")
        return "", "fallback"


def _gerar_regra_python_gemini(aprendizado: dict) -> tuple[str, str]:
    """
    Usa Gemini para gerar um arquivo Python LegalRule completo com lógica real.
    Retorna (codigo_python, model_used).
    """
    titulo     = aprendizado.get("titulo", "Regra sem título")
    descricao  = aprendizado.get("descricao", "")
    correcao   = aprendizado.get("correcao", "")
    base_legal = aprendizado.get("base_legal", "")
    nivel      = aprendizado.get("nivel_sugerido", "AVISO")
    prioridade = aprendizado.get("prioridade_sugerida", 40)

    slug       = re.sub(r"[^\w]", "_", titulo.lower())[:30].strip("_")
    slug       = re.sub(r"_+", "_", slug)
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    class_name = "Lab" + "".join(w.capitalize() for w in slug.split("_")[:4]) + "Rule"
    rule_id    = f"LAB_{slug.upper()}_{timestamp}"

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
        "            # Campos disponíveis em contexto:\n"
        "            #   numero_processo, reclamante, reclamada, data_admissao, data_demissao\n"
        "            #   salario_base, aviso_previo_dias, indice_correcao, juros_mora\n"
        "            #   verbas_deferidas (list[VerbaContexto]), fgts_*, autorizada_deducao\n"
        "            # self._alerta(contexto, 'mensagem', nivel='ERRO'|'AVISO'|'INFO')\n"
        "            # self._registrar(contexto)  # marca a regra como executada\n"
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
        "2. Use os campos corretos do ContextoJuridico para verificar a condição.\n"
        f'3. Chame self._alerta() com nivel="{nivel}" quando a condição for detectada.\n'
        "4. Chame self._registrar(contexto) ao final da execução bem-sucedida.\n"
        "5. A regra deve ser conservadora: disparar só com evidência clara.\n"
        "6. Retorne APENAS o código Python puro, sem blocos markdown (sem ```python).\n"
        "7. Mantenha o id, titulo, base_legal e prioridade exatamente como definidos acima.\n"
    )

    raw, model = _chamar_gemini_para_codify(prompt)

    # Remove blocos markdown se Gemini adicionou mesmo sendo instruído a não
    if raw.startswith("```"):
        lines = raw.split("\n")[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    return raw, model


def _gerar_exemplo_skill_gemini(aprendizado: dict, numero_processo: str = "") -> tuple[str, str]:
    """
    Usa Gemini para gerar um bloco de "Engenharia Reversa" para o skill file.
    Este bloco é um exemplo few-shot que melhora a interpretação textual do Gemini
    em casos futuros semelhantes.
    Retorna (bloco_markdown, model_used).
    """
    titulo     = aprendizado.get("titulo", "")
    descricao  = aprendizado.get("descricao", "")
    correcao   = aprendizado.get("correcao", "")
    base_legal = aprendizado.get("base_legal", "")
    timestamp  = datetime.now().strftime("%d/%m/%Y %H:%M")

    prompt = (
        "Você é perita calculista trabalhista especializada em documentar padrões de erro e correção.\n\n"
        "Crie uma seção de 'Engenharia Reversa' em Markdown para um arquivo de skill de IA.\n"
        "Esta seção treina o modelo de IA a identificar e corrigir padrões semelhantes em futuros processos.\n\n"
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
        "### Exemplo prático\n"
        "**Texto na sentença (padrão problemático):**\n"
        "> [exemplo de trecho problemático]\n\n"
        "**Interpretação correta:**\n"
        "[como interpretar corretamente]\n\n"
        "INSTRUÇÕES:\n"
        "1. Preencha cada subseção com informações técnicas e específicas do insight acima.\n"
        "2. Use linguagem técnica jurídico-trabalhista.\n"
        "3. O exemplo prático deve ser concreto e diretamente útil para um modelo de IA.\n"
        "4. Retorne APENAS o bloco Markdown, sem prefácio ou comentário externo.\n"
    )

    raw, model = _chamar_gemini_para_codify(prompt)
    return raw, model


def _registrar_log_enriquecido(
    aprendizado: dict,
    numero_processo: str,
    caminhos: list,
    model_used_rule: Optional[str] = None,
    model_used_skill: Optional[str] = None,
) -> None:
    """Registra o aprendizado no learning_log.jsonl com o formato enriquecido."""
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
        with open(_LEARNING_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[CODIFY] Erro ao registrar log: {e}")


def codify_insight(
    aprendizado: dict,
    numero_processo: str = "",
    conteudo_editado: Optional[str] = None,
) -> dict:
    """
    Consolida o aprendizado da perita em duas camadas simultâneas:

    CAMADA 1 — Lógica (Código/Skills):
      - tipo "regra":
          a) Salva o código Python em legal_engine/rules/ (conteudo_editado ou gerado pelo Gemini).
          b) Sempre injeta um exemplo de Engenharia Reversa em skills/sentenca_ordinaria.md.
      - tipo "playbook":
          Injeta bloco Markdown enriquecido pelo Gemini em skills/sentenca_ordinaria.md
          (usa conteudo_editado diretamente se o usuário editou o preview).

    CAMADA 2 — Log (Histórico):
      Grava registro enriquecido em learning_log.jsonl:
      {data, processo_id, discrepancia, correcao_aplicada, ...}

    Se `conteudo_editado` for fornecido para "regra", salva esse conteúdo exato;
    ainda assim gera o exemplo de Engenharia Reversa via Gemini para o skill.
    Se `conteudo_editado` for fornecido para "playbook", salva esse conteúdo exato no skill.

    Retorna: {"salvo": bool, "tipo": str, "caminho": str, "caminhos": list,
              "model_used_rule": str, "model_used_skill": str, "msg": str}
    """
    tipo       = aprendizado.get("tipo", "playbook")
    titulo     = aprendizado.get("titulo", "aprendizado")
    descricao  = aprendizado.get("descricao", "")
    base_legal = aprendizado.get("base_legal", "")
    correcao   = aprendizado.get("correcao", "")

    resultado: Dict[str, Any] = {
        "salvo": False,
        "tipo": tipo,
        "caminhos": [],
        "model_used_rule": None,
        "model_used_skill": None,
    }

    try:
        os.makedirs(_RULES_DIR,  exist_ok=True)
        os.makedirs(_SKILLS_DIR, exist_ok=True)

        skill_path = os.path.join(_SKILLS_DIR, "sentenca_ordinaria.md")

        # ── CAMADA 1 — LÓGICA ──────────────────────────────────────────────────

        if tipo == "regra":
            # 1a. Salvar arquivo Python da regra
            slug         = re.sub(r"[^\w]", "_", titulo.lower())[:40]
            slug         = re.sub(r"_+", "_", slug).strip("_")
            timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"lab_{slug}_{timestamp}.py"
            caminho_regra = os.path.join(_RULES_DIR, nome_arquivo)

            if conteudo_editado is not None:
                codigo_python = conteudo_editado
                resultado["model_used_rule"] = "user_edited"
                print(f"[CODIFY] Regra (editada pelo usuário) → {caminho_regra}")
            else:
                codigo_python, model_r = _gerar_regra_python_gemini(aprendizado)
                resultado["model_used_rule"] = model_r
                if not codigo_python.strip():
                    # Fallback: usa o template estático
                    codigo_python = preview_aprendizado(aprendizado)["conteudo"]
                    resultado["model_used_rule"] = "template_fallback"
                    print("[CODIFY] Gemini falhou para regra Python — usando template fallback")

            with open(caminho_regra, "w", encoding="utf-8") as f:
                f.write(codigo_python)
            print(f"[CODIFY] Regra salva: {caminho_regra} (via {resultado['model_used_rule']})")
            resultado["caminhos"].append(caminho_regra)
            resultado["caminho"] = caminho_regra

            # 1b. Sempre injetar exemplo de Engenharia Reversa no skill
            if os.path.exists(skill_path):
                exemplo_md, model_s = _gerar_exemplo_skill_gemini(aprendizado, numero_processo)
                resultado["model_used_skill"] = model_s
                if not exemplo_md.strip():
                    ts_fmt = datetime.now().strftime("%d/%m/%Y %H:%M")
                    exemplo_md = (
                        f"\n---\n## Engenharia Reversa — {titulo}\n"
                        f"<!-- Laboratório {ts_fmt} | Processo: {numero_processo or 'N/A'} -->\n\n"
                        f"**Base legal:** {base_legal}\n"
                        f"**Situação:** {descricao}\n"
                        f"**Correção:** {correcao}\n"
                    )
                    resultado["model_used_skill"] = "template_fallback"
                with open(skill_path, "a", encoding="utf-8") as f:
                    f.write("\n" + exemplo_md)
                print(f"[CODIFY] Skill enriquecida: {skill_path} (via {resultado['model_used_skill']})")
                resultado["caminhos"].append(skill_path)
                resultado["caminho_skill"] = skill_path

        else:  # playbook
            if conteudo_editado is not None:
                bloco_md = conteudo_editado
                resultado["model_used_skill"] = "user_edited"
                print(f"[CODIFY] Playbook (editado pelo usuário) → {skill_path}")
            else:
                bloco_md, model_s = _gerar_exemplo_skill_gemini(aprendizado, numero_processo)
                resultado["model_used_skill"] = model_s
                if not bloco_md.strip():
                    bloco_md = preview_aprendizado(aprendizado)["conteudo"]
                    resultado["model_used_skill"] = "template_fallback"
                    print("[CODIFY] Gemini falhou para playbook — usando template fallback")

            if os.path.exists(skill_path):
                with open(skill_path, "a", encoding="utf-8") as f:
                    f.write("\n" + bloco_md)
                print(f"[CODIFY] Skill atualizada: {skill_path} (via {resultado['model_used_skill']})")
            else:
                print(f"[CODIFY] Skill não encontrada: {skill_path}")

            resultado["caminhos"].append(skill_path)
            resultado["caminho"] = skill_path

        # ── CAMADA 2 — LOG ─────────────────────────────────────────────────────
        _registrar_log_enriquecido(
            aprendizado=aprendizado,
            numero_processo=numero_processo,
            caminhos=resultado["caminhos"],
            model_used_rule=resultado["model_used_rule"],
            model_used_skill=resultado["model_used_skill"],
        )

        resultado["salvo"] = True
        nomes = " + ".join(
            "/".join(c.replace("\\", "/").split("/")[-2:])
            for c in resultado["caminhos"]
        )
        resultado["msg"] = (
            f"Aprendizado consolidado: Log registrado e Manual de Instruções (Skills) "
            f"atualizado com sucesso. Arquivo(s): {nomes}"
        )

        return resultado

    except Exception as e:
        print(f"[CODIFY] Erro crítico: {e}")
        return {
            "salvo": False,
            "tipo": tipo,
            "caminhos": [],
            "msg": f"Erro ao codificar insight: {e}",
        }


# ── Extração de documento textual genérico (PDF, DOC, DOCX) ─────────────────

def _extrair_texto_arquivo(file_bytes: bytes, filename: str) -> str:
    """
    Extrai texto de PDF, DOC ou DOCX.
    - .pdf  → pdfplumber (primeiras 10 páginas)
    - .docx → _extrair_texto_docx (zipfile / XML)
    - .doc  → tenta decodificar como texto simples (fallback)
    """
    fname = (filename or "").lower()
    if fname.endswith(".pdf"):
        try:
            import pdfplumber
            import io
            texto = ""
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages[:10]:
                    texto += (page.extract_text() or "") + "\n"
            return texto.strip()
        except Exception as e:
            print(f"[LEARNING] Erro ao extrair PDF {filename}: {e}")
            return ""
    elif fname.endswith(".docx"):
        return _extrair_texto_docx(file_bytes)
    elif fname.endswith(".doc"):
        # .doc binário: tenta decodificar como Latin-1 e extrair strings legíveis
        try:
            raw = file_bytes.decode("latin-1", errors="ignore")
            linhas = [l.strip() for l in raw.split("\n") if len(l.strip()) > 20]
            return "\n".join(linhas[:200])
        except Exception:
            return ""
    return ""


# ── Extração do Processo / Sentença ─────────────────────────────────────────

def _extrair_processo(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Extrai dados estruturados do processo/sentença.
    - PDF → pipeline completo (sentence_finder + IA)
    - DOC/DOCX → extrai texto e chama IA com texto bruto
    """
    fname = (filename or "").lower()
    if fname.endswith(".pdf"):
        return _extrair_sentenca(file_bytes)

    # DOC/DOCX: extrai texto e usa IA
    try:
        from services.ai_client import extract_data_with_gemini
        from services.learning_skill_loader import carregar_skill_para_lab

        texto = _extrair_texto_arquivo(file_bytes, filename)
        if not texto.strip():
            return {"erro": "Documento sem texto legível", "doc_type": "sentenca"}

        playbook = carregar_skill_para_lab("sentenca")
        ai_result = extract_data_with_gemini(texto, playbook=playbook)
        return {
            "doc_type": "sentenca",
            "dados": ai_result.get("data") or {},
            "model_used": ai_result.get("model_used"),
            "erro": ai_result.get("error"),
        }
    except Exception as e:
        return {"erro": str(e), "doc_type": "sentenca"}


# ── Extração da Impugnação ───────────────────────────────────────────────────

def _extrair_impugnacao(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Extrai fundamentos e argumentos da impugnação da parte contrária.
    Estrutura idêntica à manifestação — fundamentos + trechos de contestação.
    """
    texto = _extrair_texto_arquivo(file_bytes, filename)
    if not texto:
        return {"erro": "Não foi possível extrair texto da impugnação", "texto": ""}

    fundamentos = _extrair_fundamentos_juridicos(texto)
    argumentos  = _extrair_discrepancias_perita(texto)  # reutiliza heurística

    return {
        "texto_bruto": texto[:3000],
        "fundamentos_juridicos": fundamentos,
        "argumentos_da_parte": argumentos,
        "erro": None,
    }


# ── Extração do Cálculo (.PJC, PDF, DOC, DOCX) ───────────────────────────────

def _extrair_calculo_pjc(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Extrai parâmetros do arquivo de cálculo PJe-Calc.
    - .pjc / .xml → PjcParser (parâmetros estruturados)
    - .pdf / .doc / .docx → extração de texto + regex
    """
    return _extrair_liquidacao(file_bytes, filename)


# ── Relatório ampliado com impugnação e cálculo PJC ──────────────────────────

def _enriquecer_relatorio_com_extras(
    relatorio: Dict[str, Any],
    dados_impugnacao: Optional[Dict],
    dados_calculo_pjc: Optional[Dict],
) -> Dict[str, Any]:
    """
    Adiciona seções de impugnação e cálculo PJC ao relatório base.
    Também cruza fundamentos da impugnação vs parecer para identificar pontos de conflito.
    """
    if dados_impugnacao:
        relatorio["impugnacao"] = {
            "fundamentos_juridicos": dados_impugnacao.get("fundamentos_juridicos") or [],
            "argumentos_da_parte":   dados_impugnacao.get("argumentos_da_parte") or [],
            "erro": dados_impugnacao.get("erro"),
        }
        # Fundamentos em conflito: mencionados na impugnação mas NÃO na manifestação/parecer
        fund_parecer    = set(relatorio.get("manifestacao", {}).get("fundamentos_juridicos") or [])
        fund_impugnacao = set(dados_impugnacao.get("fundamentos_juridicos") or [])
        relatorio["pontos_de_conflito"] = list(fund_impugnacao - fund_parecer)
    else:
        relatorio["impugnacao"] = None
        relatorio["pontos_de_conflito"] = []

    if dados_calculo_pjc:
        relatorio["calculo_pjc"] = {
            "tipo": dados_calculo_pjc.get("tipo"),
            "indice_correcao": dados_calculo_pjc.get("indice_correcao"),
            "juros_mora": dados_calculo_pjc.get("juros_mora"),
            "divisor_horas": dados_calculo_pjc.get("divisor_horas"),
            "verbas_calculadas": dados_calculo_pjc.get("verbas_calculadas") or [],
            "erro": dados_calculo_pjc.get("erro"),
        }

        # Adiciona divergências entre calculo_pjc e sentença ao relatório principal
        dados_sentenca_dados = relatorio.get("sentenca", {})
        # Checar índice se PJC tiver índice diferente do já detectado via liquidação
        indice_pjc = dados_calculo_pjc.get("indice_correcao") or ""
        indice_sent = dados_sentenca_dados.get("campos_chave", {}).get("indice_correcao") or ""
        if indice_pjc and indice_sent:
            n_pjc  = indice_pjc.upper().replace("-", "").replace("_", "")
            n_sent = indice_sent.upper().replace("-", "").replace("_", "")
            if n_pjc not in n_sent and n_sent not in n_pjc:
                relatorio["discrepancias"].append({
                    "tipo": "indice_calculo_pjc",
                    "nivel": "ERRO",
                    "juiz_disse": f"Índice determinado: {indice_sent}",
                    "empresa_calculou": f"Índice no .PJC: {indice_pjc}",
                    "juliana_corrigiu": "Corrigir índice no arquivo PJe-Calc",
                    "fundamento": "ADC 58 / Súmula 439 TST",
                })
        relatorio["resumo"]["discrepancias_encontradas"] = len(relatorio["discrepancias"])
    else:
        relatorio["calculo_pjc"] = None

    return relatorio


# ── Interface pública ─────────────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════════════════
# FASE DE CONHECIMENTO — Amostragem Pericial (PDF + Word)
# Analisa as provas produzidas pela perita para alimentar cross-reference e
# style transfer antes de comparar sentença ↔ liquidação ↔ parecer.
# ══════════════════════════════════════════════════════════════════════════════

def _extrair_amostragem_pdf(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Analisa o relatório de amostragem (PDF de holerites / cartões de ponto) para
    identificar a tese vencedora que a perita provou.

    Extrai:
    - teses_provadas:      lista das irregularidades comprovadas
    - verbas_prova:        verbas trabalhistas objeto da prova
    - evidencias:          tipos de documento usados como prova
    - irregularidades:     [{verba, irregularidade, art_clt}]
    - resumo:              descrição concisa do que foi provado

    Essa informação alimenta o cross-reference com a sentença para gerar regras
    preditivas do tipo: "Sempre que a sentença deferir X, verificar parâmetro Y
    no PJe-Calc pois a empresa omite isso sistematicamente."
    """
    texto = _extrair_texto_arquivo(file_bytes, filename)
    if not texto.strip():
        return {"erro": "PDF sem texto legível", "teses_provadas": [], "verbas_prova": [], "irregularidades": []}

    prompt = (
        "Você é um assistente jurídico especializado em Direito do Trabalho Brasileiro.\n"
        "Analise o relatório de amostragem pericial abaixo e extraia informações em JSON puro.\n\n"
        "O relatório de amostragem é uma prova produzida por um perito judicial que cruza\n"
        "holerites, cartões de ponto e dados da empresa para provar irregularidades trabalhistas.\n\n"
        "Extraia EXATAMENTE no formato JSON:\n"
        "{\n"
        '  "teses_provadas": ["lista das teses/irregularidades provadas pelo perito"],\n'
        '  "verbas_prova": ["lista de verbas trabalhistas objeto da prova"],\n'
        '  "evidencias_utilizadas": ["holerites", "cartões de ponto", "contracheques", etc.],\n'
        '  "periodo_analisado": "ex: jan/2020 a dez/2022 ou vazio se não identificado",\n'
        '  "irregularidades": [\n'
        '    {\n'
        '      "verba": "nome da verba trabalhista",\n'
        '      "irregularidade": "descrição objetiva do erro/omissão identificado",\n'
        '      "art_clt": "dispositivo legal aplicável, ex: Art. 58 §1º CLT"\n'
        '    }\n'
        '  ],\n'
        '  "resumo": "2-3 frases resumindo o que foi provado e qual era a irregularidade central"\n'
        "}\n\n"
        "IMPORTANTE: Responda APENAS com o JSON válido, sem markdown, sem texto antes ou depois.\n\n"
        f"TEXTO DA AMOSTRAGEM (primeiros 4000 caracteres):\n{texto[:4000]}"
    )

    conteudo, model = _chamar_gemini_para_codify(prompt)

    dados: Dict[str, Any] = {}
    try:
        conteudo_limpo = re.sub(r"```(?:json)?\s*|\s*```", "", conteudo).strip()
        dados = json.loads(conteudo_limpo)
    except Exception:
        dados = {
            "teses_provadas": [],
            "verbas_prova": [],
            "evidencias_utilizadas": [],
            "irregularidades": [],
            "resumo": (conteudo[:500] if conteudo else "Não foi possível analisar o relatório de amostragem"),
        }

    dados["model_used"] = model
    dados["texto_bruto"] = texto[:2000]
    return dados


def _extrair_amostragem_word(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Analisa a petição ou relatório Word da amostragem para:
    1. Extrair o vocabulário jurídico e o estilo argumentativo da perita (Style Transfer).
    2. Salvar os padrões aprendidos em skills/amostragem_style.md para uso futuro.

    Isso garante que o sistema replique o vocabulário, estrutura e tom da perita
    ao gerar futuros pareceres técnicos — quanto mais arquivos Word, mais fiel fica.
    """
    texto = _extrair_texto_arquivo(file_bytes, filename)
    if not texto.strip():
        return {"erro": "Documento sem texto legível", "style_atualizado": False, "estilo": {}}

    prompt = (
        "Você é especialista em análise de linguagem jurídica e style transfer.\n"
        "Analise o documento pericial trabalhista abaixo e extraia os padrões de escrita.\n\n"
        "Extraia em JSON puro:\n"
        "{\n"
        '  "vocabulario_tecnico": ["10-20 termos jurídicos/técnicos usados pela perita"],\n'
        '  "expressoes_caracteristicas": ["5-10 expressões ou frases típicas da escrita"],\n'
        '  "estrutura_argumentativa": "descrição da estrutura lógica (ex: tese → prova → conclusão)",\n'
        '  "tom": "objetivo|formal|técnico|misto",\n'
        '  "exemplo_paragrafo_abertura": "trecho real de como a perita abre um relatório/petição",\n'
        '  "exemplo_paragrafo_conclusao": "trecho real de como a perita conclui uma irregularidade",\n'
        '  "verbas_mencionadas": ["verbas trabalhistas identificadas no documento"],\n'
        '  "tabelas_comparativas": true,\n'
        '  "resumo_estilo": "2-3 frases descrevendo o estilo de escrita da perita"\n'
        "}\n\n"
        "IMPORTANTE: Responda APENAS com o JSON válido, sem markdown.\n\n"
        f"DOCUMENTO (primeiros 5000 caracteres):\n{texto[:5000]}"
    )

    conteudo, model = _chamar_gemini_para_codify(prompt)

    dados_estilo: Dict[str, Any] = {}
    try:
        conteudo_limpo = re.sub(r"```(?:json)?\s*|\s*```", "", conteudo).strip()
        dados_estilo = json.loads(conteudo_limpo)
    except Exception:
        dados_estilo = {
            "resumo_estilo": (conteudo[:500] if conteudo else "Não foi possível analisar o estilo"),
            "vocabulario_tecnico": [],
            "expressoes_caracteristicas": [],
            "tom": "desconhecido",
        }

    # Style Transfer: persiste em skills/amostragem_style.md
    style_salvo = _atualizar_skill_amostragem(dados_estilo, texto[:2000], filename)

    return {
        "estilo": dados_estilo,
        "model_used": model,
        "style_atualizado": style_salvo,
        "texto_bruto": texto[:1000],
        "erro": None,
    }


def _atualizar_skill_amostragem(dados_estilo: dict, trecho_original: str, filename: str = "") -> bool:
    """
    Cria ou atualiza skills/amostragem_style.md com os padrões de estilo extraídos
    do documento Word da perita. Cada chamada ADICIONA um novo bloco ao arquivo,
    acumulando aprendizado de múltiplas amostragens.
    """
    os.makedirs(_SKILLS_DIR, exist_ok=True)
    destino = os.path.join(_SKILLS_DIR, "amostragem_style.md")
    data = datetime.now().strftime("%Y-%m-%d %H:%M")

    vocabulario = "\n".join(
        f"- {v}" for v in (dados_estilo.get("vocabulario_tecnico") or [])[:20]
    )
    expressoes = "\n".join(
        f"- {e}" for e in (dados_estilo.get("expressoes_caracteristicas") or [])[:10]
    )

    bloco = f"""

---

## Amostragem Analisada — {data} | {filename}

**Resumo do estilo:**
{dados_estilo.get("resumo_estilo") or "Não identificado"}

**Tom:** {dados_estilo.get("tom") or "—"}
**Estrutura argumentativa:** {dados_estilo.get("estrutura_argumentativa") or "—"}
**Tabelas comparativas:** {"Sim" if dados_estilo.get("tabelas_comparativas") else "Não"}

**Vocabulário técnico identificado:**
{vocabulario or "— Não identificado"}

**Expressões características da perita:**
{expressoes or "— Não identificadas"}

**Exemplo de abertura:**
> {dados_estilo.get("exemplo_paragrafo_abertura") or "—"}

**Exemplo de conclusão de irregularidade:**
> {dados_estilo.get("exemplo_paragrafo_conclusao") or "—"}

**Trecho original (referência):**
```
{trecho_original[:500]}
```
"""

    try:
        if not os.path.exists(destino):
            cabecalho = (
                "# Guia de Estilo da Perita — Amostragens Analisadas\n\n"
                "Este arquivo é atualizado automaticamente pelo Laboratório de Aprendizado\n"
                "sempre que uma nova **Amostragem Word** é submetida.\n\n"
                "Ele serve como base para **Style Transfer**: garante que o sistema replique\n"
                "o vocabulário, a estrutura argumentativa e o tom da perita ao gerar pareceres.\n\n"
                "**Como usar:** inclua este arquivo no system prompt ao gerar pareceres técnicos.\n"
                "**Nota:** cada bloco abaixo representa uma amostragem diferente — mais blocos = mais fidelidade.\n"
            )
            with open(destino, "w", encoding="utf-8") as f:
                f.write(cabecalho + bloco)
        else:
            with open(destino, "a", encoding="utf-8") as f:
                f.write(bloco)
        print(f"[LEARNING] skills/amostragem_style.md atualizado com novos padrões de estilo ({filename}).")
        return True
    except Exception as e:
        print(f"[LEARNING] Erro ao atualizar amostragem_style.md: {e}")
        return False


def _gerar_regras_preditivas_amostragem(
    dados_amostragem_pdf: Dict,
    dados_sentenca: Dict,
    dados_liquidacao: Dict,
) -> List[Dict]:
    """
    Cross-reference entre Amostragem + Sentença + Liquidação para gerar regras preditivas.

    Lógica de causa e efeito:
      "Sempre que a sentença deferir [verba X] com base na tese [Y] (provada na amostragem),
       verifique [parâmetro Z] no PJe-Calc (Art. W CLT), pois é uma omissão sistemática."

    Essas regras são adicionadas com prioridade máxima aos aprendizados do relatório.
    """
    regras: List[Dict] = []
    irregularidades = dados_amostragem_pdf.get("irregularidades") or []
    teses           = dados_amostragem_pdf.get("teses_provadas") or []

    # Regras preditivas baseadas em irregularidades detalhadas
    for irreg in irregularidades:
        verba         = (irreg.get("verba") or "").strip()
        irregularidade = (irreg.get("irregularidade") or "").strip()
        art_clt       = (irreg.get("art_clt") or "CLT").strip()

        if verba and irregularidade:
            regras.append({
                "tipo": "regra",
                "titulo": f"Regra Preditiva: {verba} — {irregularidade[:60]}",
                "descricao": (
                    f"Tese vencedora identificada na amostragem pericial: {irregularidade}. "
                    f"Quando a sentença deferir '{verba}', auditar parametrização no PJe-Calc "
                    f"pois a empresa omite sistematicamente este parâmetro."
                ),
                "correcao": (
                    f"Verificar e corrigir parametrização de '{verba}' no PJe-Calc "
                    f"conforme {art_clt}. Usar holerites e cartões de ponto como contraprova."
                ),
                "base_legal": art_clt,
                "nivel_sugerido": "AVISO",
                "prioridade_sugerida": 25,
                "origem": "amostragem_cross_reference",
            })

    # Regras genéricas para teses sem irregularidades estruturadas
    for tese in teses[:5]:
        tese_norm = tese.lower()
        already_covered = any(tese_norm in r["titulo"].lower() for r in regras)
        if not already_covered:
            regras.append({
                "tipo": "playbook",
                "titulo": f"Tese Vencedora: {tese[:80]}",
                "descricao": (
                    f"Tese provada pela perita na amostragem pericial: {tese}. "
                    "Registrar como playbook para orientar auditoria futura de cálculos similares."
                ),
                "base_legal": "Amostragem pericial — cross-reference sentença/liquidação",
                "nivel_sugerido": "INFO",
                "prioridade_sugerida": 35,
                "origem": "amostragem_tese",
            })

    return regras


def _resumir_triada_pericial(
    dados_amostragem_pdf: Optional[Dict],
    dados_sentenca: Dict,
    dados_calculo_pjc: Optional[Dict],
) -> Dict[str, Any]:
    """
    Gera um resumo estruturado da "Tríade da Liquidação":
      - Tese na Amostragem (prova)
      - Deferimento na Sentença (direito)
      - Estado no cálculo (.PJC)

    Esse resumo é usado apenas para interface (view do Lab) e para logs;
    o aprendizado autônomo continua sendo feito pelo Self-Healing Rule Engine.
    """
    amos_ok = bool(dados_amostragem_pdf and (dados_amostragem_pdf.get("teses_provadas") or dados_amostragem_pdf.get("irregularidades")))
    sent_ok = bool(dados_sentenca)
    pjc_ok  = bool(dados_calculo_pjc)

    triade = {
        "amostragem_presente": amos_ok,
        "sentenca_presente": sent_ok,
        "pjc_presente": pjc_ok,
    }

    teses = (dados_amostragem_pdf or {}).get("teses_provadas") or []
    irregs = (dados_amostragem_pdf or {}).get("irregularidades") or []
    triade["tese_principal"] = teses[0] if teses else (irregs[0].get("irregularidade") if irregs else None)

    campos_sent = (dados_sentenca or {}).get("campos_chave") or {}
    triade["verba_chave_sentenca"] = None
    if (dados_sentenca or {}).get("verbas"):
        triade["verba_chave_sentenca"] = (dados_sentenca.get("verbas") or [None])[0]

    verbas_pjc = (dados_calculo_pjc or {}).get("verbas_calculadas") or []
    triade["tem_verbas_pjc"] = bool(verbas_pjc)

    ausentes = []
    if not amos_ok:
        ausentes.append("Amostragem")
    if not sent_ok:
        ausentes.append("Processo")
    if not pjc_ok:
        ausentes.append(".PJC")

    if not ausentes:
        triade["aviso"] = "Tríade completa: Amostragem, Processo e .PJC disponíveis para auditoria cruzada."
    elif not pjc_ok and sent_ok:
        triade["aviso"] = (
            "Cálculo .PJC não fornecido: a IA não pôde validar a parametrização matemática deste caso."
        )
    else:
        triade["aviso"] = (
            f"Análise parcial: {', '.join(ausentes)} não fornecido(s). "
            "Recomenda-se Amostragem + Processo + .PJC para auditoria completa."
        )

    return triade


# ══════════════════════════════════════════════════════════════════════════════
# SELF-HEALING RULE ENGINE — Aprendizado Autônomo
# Extrai lógica de correção em JSON estruturado, atualiza o Knowledge Base e
# avalia hipóteses shadow contra os pareceres reais submetidos ao laboratório.
# ══════════════════════════════════════════════════════════════════════════════

def _extrair_logica_correcao_gemini(relatorio: Dict) -> List[Dict]:
    """
    Usa Gemini para extrair, do relatório de discrepâncias, a lógica de correção
    em formato JSON estruturado — não gera código Python imediatamente.

    Cada item retornado representa uma hipótese de regra candidata ao Knowledge Base:
    {
      "descricao":   str,
      "condicao":    {"tipo": "verba_ausente|campo_diferente|...", "verba"?: str, "campo"?: str, "valor_esperado"?: str},
      "acao":        {"tipo": "alerta", "nivel": "AVISO|ERRO", "mensagem": str},
      "base_legal":  str
    }

    Tipos de condição suportados pelo DynamicLegalRule:
      verba_ausente   — verba deferida mas não calculada
      verba_presente  — verba inesperadamente presente
      indice_ausente  — índice de correção não informado
      campo_ausente   — campo obrigatório vazio
      campo_diferente — campo diverge do esperado
    """
    discrepancias = relatorio.get("discrepancias") or []
    verbas_sentenca = (relatorio.get("sentenca") or {}).get("verbas") or []
    verbas_liquidacao = (relatorio.get("liquidacao") or {}).get("verbas_calculadas") or []
    indice_sentenca = ((relatorio.get("sentenca") or {}).get("campos_chave") or {}).get("indice_correcao", "")
    indice_liq = (relatorio.get("liquidacao") or {}).get("indice_correcao", "")

    if not discrepancias and not verbas_sentenca:
        return []

    disc_txt = json.dumps(discrepancias[:10], ensure_ascii=False)
    prompt = (
        "Você é um Engenheiro de Machine Learning especializado em Direito Trabalhista.\n"
        "Analise o relatório de discrepâncias de um processo trabalhista abaixo e extraia\n"
        "a lógica de correção como uma lista de HIPÓTESES DE REGRA em JSON puro.\n\n"
        "Para cada discrepância identificada, gere um objeto com:\n"
        "{\n"
        '  "descricao": "frase curta descrevendo a situação problemática",\n'
        '  "condicao": {\n'
        '    "tipo": "verba_ausente" | "verba_presente" | "indice_ausente" | "campo_ausente" | "campo_diferente",\n'
        '    "verba": "nome da verba se aplicável (ex: horas extras)",\n'
        '    "campo": "nome do campo Python se aplicável (ex: indice_correcao)",\n'
        '    "valor_esperado": "valor correto esperado se aplicável"\n'
        "  },\n"
        '  "acao": {"tipo": "alerta", "nivel": "ERRO" | "AVISO", "mensagem": "texto do alerta para o perito"},\n'
        '  "base_legal": "ex: Art. 59 CLT, Súmula 264 TST"\n'
        "}\n\n"
        "REGRAS:\n"
        "- Gere APENAS hipóteses com fundamento nos dados abaixo (nenhuma invenção)\n"
        "- Máximo 5 hipóteses por análise\n"
        "- Responda APENAS com o array JSON, sem markdown\n\n"
        f"Verbas na sentença: {verbas_sentenca}\n"
        f"Verbas na liquidação: {verbas_liquidacao}\n"
        f"Índice sentença: {indice_sentenca} | Índice liquidação: {indice_liq}\n"
        f"Discrepâncias identificadas:\n{disc_txt}"
    )

    conteudo, model = _chamar_gemini_para_codify(prompt)
    logicas: List[Dict] = []

    try:
        limpo = re.sub(r"```(?:json)?\s*|\s*```", "", conteudo).strip()
        parsed = json.loads(limpo)
        if isinstance(parsed, list):
            logicas = [l for l in parsed if isinstance(l, dict) and "condicao" in l]
        elif isinstance(parsed, dict) and "condicao" in parsed:
            logicas = [parsed]
    except Exception:
        print(f"[KB] Aviso: Gemini não retornou JSON válido para extração de lógica.")

    print(f"[KB] {len(logicas)} hipótese(s) de regra extraída(s) com {model}")
    return logicas


def processar_aprendizado_autonomo(
    relatorio: Dict,
    numero_processo: str = "",
) -> Dict:
    """
    Ponto de entrada do aprendizado autônomo.

    Fluxo:
      1. Chama Gemini para extrair hipóteses de regra em JSON estruturado
      2. Para cada hipótese, verifica se já existe no Knowledge Base
         - Se existe → incrementa confidence_score (pode ativar se score >= 3)
         - Se não existe → cria nova regra shadow com score = 1
      3. Avalia regras shadow existentes contra as discrepâncias do relatorio
         (recompensa acertos, penaliza predições erradas)

    Retorna dict de sumário do que foi aprendido/atualizado.
    """
    from services.knowledge_base import KnowledgeBase

    kb = KnowledgeBase()
    numero = numero_processo or relatorio.get("numero_processo", "")

    # Fase 1: extração de novas hipóteses via Gemini
    logicas = _extrair_logica_correcao_gemini(relatorio)
    resultados_criacao = []

    for logica in logicas:
        resultado = kb.adicionar_ou_incrementar(logica, numero)
        resultados_criacao.append(resultado)

    # Fase 2: avaliar regras shadow existentes contra discrepâncias do relatorio
    resultados_avaliacao = _evaluate_shadow_rules(relatorio, kb)

    criadas     = sum(1 for r in resultados_criacao if r.get("acao") == "criada")
    incrementadas = sum(1 for r in resultados_criacao if r.get("acao") == "incrementada")
    ativadas    = sum(1 for r in resultados_criacao if r.get("acao") == "ativada")

    print(
        f"[KB] Aprendizado autônomo: "
        f"{criadas} criada(s), {incrementadas} incrementada(s), {ativadas} ativada(s)"
    )

    return {
        "hipoteses_extraidas":  len(logicas),
        "criadas":              criadas,
        "incrementadas":        incrementadas,
        "ativadas":             ativadas,
        "avaliacao_shadow":     resultados_avaliacao,
        "stats_kb":             kb.stats(),
    }


def _evaluate_shadow_rules(relatorio: Dict, kb=None) -> Dict:
    """
    Sistema de Punição / Autocorreção.

    Compara as predições das regras shadow do Knowledge Base contra as discrepâncias
    reais encontradas no relatório do laboratório:

      Acerto:  regra previu problema X → discrepância X confirmada no relatorio → +1 score
      Punição: regra previu problema X → discrepância X NÃO encontrada → -1 score

    As regras shadow que chegam a score <= -1 são automaticamente deletadas.
    """
    if kb is None:
        from services.knowledge_base import KnowledgeBase
        kb = KnowledgeBase()

    shadow_rules = kb.get_regras_shadow()
    if not shadow_rules:
        return {"acertos": 0, "punicoes": 0, "rules_updated": []}

    numero_processo = relatorio.get("numero_processo", "")
    discrepancias   = relatorio.get("discrepancias") or []

    # Indexa discrepâncias reais para lookup eficiente
    tipos_reais      = {d.get("tipo", "") for d in discrepancias}
    verbas_ausentes_reais = set()
    for d in discrepancias:
        texto = (d.get("juiz_disse") or "").lower()
        match = re.search(r"deferido:\s*(.+)", texto)
        if match:
            verbas_ausentes_reais.add(match.group(1).strip())

    acertos   = 0
    punicoes  = 0
    updated   = []

    for regra in shadow_rules:
        cond = regra.get("condicao") or {}
        tipo = cond.get("tipo", "")

        previu_problema = False
        problema_confirmado = False

        if tipo == "verba_ausente":
            verba_prev = (cond.get("verba") or "").lower().strip()
            previu_problema = bool(verba_prev)
            # Confirma se essa verba aparece como ausente nas discrepâncias reais
            problema_confirmado = (
                "verba_ausente" in tipos_reais and
                any(verba_prev in v or v in verba_prev for v in verbas_ausentes_reais)
            )

        elif tipo in ("indice_ausente", "campo_ausente", "campo_diferente"):
            previu_problema = True
            # Confirma se esse tipo de discrepância aparece no relatorio
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
        f"[KB] Avaliação shadow: {acertos} acerto(s), {punicoes} punição(ões) "
        f"em {len(shadow_rules)} regra(s) shadow"
    )
    return {"acertos": acertos, "punicoes": punicoes, "rules_updated": updated}


# ── Manifestação Pericial: retórica de combate + regras de Ataque/Defesa ─────

def _extrair_manifestacao_pericial(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Analisa a Manifestação (Petição de Resposta / Impugnação à Contestação) para extrair:
    1. Frases de impacto retórico da perita (tom combativo, expressões-chave)
    2. Súmulas, OJs e artigos usados como escudo jurídico
    3. Padrões de Ataque (argumento da empresa) → Defesa (rebate da perita)
    4. Parâmetros matemáticos expostos como fraudulentos
    5. Argumentos vencedores que o sistema deve replicar futuramente

    Suporta PDF, DOC e DOCX. Usa Gemini para análise semântica profunda.
    """
    texto = _extrair_texto_arquivo(file_bytes, filename)
    if not texto.strip():
        return {
            "erro": "Documento sem texto legível",
            "frases_impacto": [],
            "fundamentos_juridicos": [],
            "padroes_ataque_defesa": [],
            "parametros_fraudados": [],
            "argumento_vencedor": "",
            "resumo": "",
        }

    prompt = (
        "Você é especialista em análise de peças jurídicas trabalhistas e inteligência estratégica.\n"
        "Analise a Manifestação Pericial (Impugnação à Contestação de Cálculos) abaixo.\n\n"
        "Extraia em JSON puro os seguintes campos:\n"
        "{\n"
        '  "frases_impacto": ["5-10 expressões retóricas de alto impacto usadas pela perita, ex: \'Divergência aritmética flagrante\', \'Preclusão consumativa\'"],\n'
        '  "fundamentos_juridicos": ["Súmulas, OJs, artigos CLT, ADC usados na defesa (ex: Súmula 172 TST, ADC 58, Art. 477 CLT)"],\n'
        '  "padroes_ataque_defesa": [\n'
        '    {"ataque_empresa": "argumento que a empresa usou", "defesa_perita": "como a perita rebateu", "fundamento": "Súmula/OJ/Art. usado"}\n'
        "  ],\n"
        '  "parametros_fraudados": ["parâmetros matemáticos que a empresa omitiu ou manipulou, ex: \'reflexos em DSR omitidos\', \'gratificação de função não integrada\'"],\n'
        '  "argumento_vencedor": "resumo em 1-2 frases do argumento central vitorioso da perita",\n'
        '  "verbas_em_disputa": ["verbas trabalhistas que foram objeto de contestação"],\n'
        '  "tom": "assertivo|incisivo|técnico|combativo",\n'
        '  "resumo": "resumo geral da manifestação em 2-3 frases"\n'
        "}\n\n"
        "IMPORTANTE: Responda APENAS com o JSON válido, sem markdown.\n\n"
        f"MANIFESTAÇÃO (primeiros 6000 caracteres):\n{texto[:6000]}"
    )

    conteudo, model = _chamar_gemini_para_codify(prompt)

    dados: Dict[str, Any] = {}
    try:
        conteudo_limpo = re.sub(r"```(?:json)?\s*|\s*```", "", conteudo).strip()
        dados = json.loads(conteudo_limpo)
    except Exception:
        dados = {
            "frases_impacto": [],
            "fundamentos_juridicos": _extrair_fundamentos_juridicos(texto),
            "padroes_ataque_defesa": [],
            "parametros_fraudados": [],
            "argumento_vencedor": conteudo[:300] if conteudo else "Não foi possível analisar a manifestação",
            "resumo": "",
        }

    dados["model_used"] = model
    dados["texto_bruto"] = texto[:2000]
    dados["erro"] = None

    # Gera shadow rules para padrões de Ataque/Defesa identificados
    _codificar_padroes_ataque_defesa(dados)

    # Persiste estilo de manifestação em skills/manifestacao_style.md
    dados["style_atualizado"] = _atualizar_skill_manifestacao(dados, texto[:2000], filename)

    return dados


def _codificar_padroes_ataque_defesa(dados_manifestacao: Dict) -> None:
    """
    Para cada padrão Ataque→Defesa encontrado na Manifestação,
    cria uma Shadow Rule no Knowledge Base: quando o tema X aparecer
    em novo processo, a IA já sugere o fundamento Y que a perita usou.
    """
    padroes = dados_manifestacao.get("padroes_ataque_defesa") or []
    if not padroes:
        return

    from services.knowledge_base import KnowledgeBase
    kb = KnowledgeBase()
    for padrao in padroes[:8]:
        ataque   = (padrao.get("ataque_empresa")  or "").strip()[:80]
        defesa   = (padrao.get("defesa_perita")   or "").strip()[:120]
        fundamento = (padrao.get("fundamento")    or "").strip()[:60]
        if not ataque or not defesa:
            continue

        condicao = {
            "tipo": "campo_diferente",
            "campo": "argumento_empresa",
            "valor_esperado": ataque,
        }
        acao = f"Sugerir fundamento: {fundamento} — Rebate: {defesa}"
        descricao = f"[Manifestação] Quando empresa alega '{ataque}', aplicar: {defesa}"

        kb.adicionar_ou_incrementar(
            logica={
                "descricao": descricao,
                "condicao":  condicao,
                "acao":      {"tipo": "alerta", "nivel": "AVISO", "mensagem": acao},
                "base_legal": fundamento,
            },
        )
    print(f"[LEARNING] {len(padroes[:8])} padrão(ões) Ataque/Defesa codificado(s) no KB.")


def _atualizar_skill_manifestacao(dados: dict, trecho_original: str, filename: str = "") -> bool:
    """
    Cria ou atualiza skills/manifestacao_style.md com os padrões aprendidos.
    Cada chamada ADICIONA um novo bloco, acumulando retórica de múltiplas peças.
    """
    os.makedirs(_SKILLS_DIR, exist_ok=True)
    destino = os.path.join(_SKILLS_DIR, "manifestacao_style.md")
    data = datetime.now().strftime("%Y-%m-%d %H:%M")

    frases = "\n".join(f'- "{f}"' for f in (dados.get("frases_impacto") or [])[:10])
    fundamentos = "\n".join(f"- {f}" for f in (dados.get("fundamentos_juridicos") or [])[:15])
    parametros  = "\n".join(f"- {p}" for p in (dados.get("parametros_fraudados")  or [])[:8])
    padroes_txt = ""
    for p in (dados.get("padroes_ataque_defesa") or [])[:5]:
        ataque    = p.get("ataque_empresa", "—")
        defesa    = p.get("defesa_perita",  "—")
        fund      = p.get("fundamento",     "—")
        padroes_txt += f"  - **Empresa:** {ataque}\n    **Perita:** {defesa} ({fund})\n"

    bloco = f"""

---

## Manifestação Analisada — {data} | {filename}

**Argumento vencedor:**
> {dados.get("argumento_vencedor") or "—"}

**Resumo:**
{dados.get("resumo") or "—"}

**Tom:** {dados.get("tom") or "—"}

**Frases de impacto (retórica de combate):**
{frases or "— Não identificadas"}

**Fundamentos jurídicos usados:**
{fundamentos or "— Não identificados"}

**Parâmetros matemáticos expostos como indevidos:**
{parametros or "— Não identificados"}

**Padrões Ataque → Defesa:**
{padroes_txt or "— Não identificados"}

**Trecho original (referência):**
```
{trecho_original[:500]}
```
"""

    try:
        with open(destino, "a", encoding="utf-8") as f:
            f.write(bloco)
        print(f"[LEARNING] skills/manifestacao_style.md atualizado ({filename}).")
        return True
    except Exception as e:
        print(f"[LEARNING] Erro ao atualizar manifestacao_style.md: {e}")
        return False


# ── Processamento com 7 arquivos (Linha do Tempo completa) ───────────────────

def processar_sete_arquivos(
    processo_bytes: Optional[bytes] = None,
    processo_filename: str = "",
    liquidacao_bytes: Optional[bytes] = None,
    liquidacao_filename: str = "",
    parecer_bytes: Optional[bytes] = None,
    parecer_filename: str = "",
    impugnacao_bytes: Optional[bytes] = None,
    impugnacao_filename: str = "",
    calculo_pjc_bytes: Optional[bytes] = None,
    calculo_pjc_filename: str = "",
    amostragem_pdf_bytes: Optional[bytes] = None,
    amostragem_pdf_filename: str = "",
    amostragem_word_bytes: Optional[bytes] = None,
    amostragem_word_filename: str = "",
    manifestacao_bytes: Optional[bytes] = None,
    manifestacao_filename: str = "",
) -> Dict[str, Any]:
    """
    Ponto de entrada para o endpoint /lab/analisar (até 8 arquivos).

    Linha do Tempo da Fraude Trabalhista:
      [1] Amostragem PDF  — O que a perita provou (holerites / cartões de ponto)
      [2] Amostragem Word — Como a perita escreve (Style Transfer → amostragem_style.md)
      [3] Sentença         — O que o juiz deferiu (com base na prova)
      [4] Liquidação       — O que a empresa calculou (com omissões)
      [5] Parecer          — Como a perita corrigiu
      [6] Impugnação       — Como a empresa contestou (opcional)
      [7] Cálculo PJC      — Parâmetros PJe-Calc para auditoria (opcional)
      [8] Manifestação     — Como a perita rebateu a empresa — retórica de combate (opcional)

    Ao combinar todos os dados, o motor gera:
    - Regras preditivas baseadas na tese vencedora (amostragem × sentença)
    - Style transfer: atualiza skills/amostragem_style.md e skills/manifestacao_style.md
    - Padrões Ataque/Defesa codificados no Knowledge Base como Shadow Rules
    - Aprendizados para codificação (regras Python + playbook Markdown)

    Obrigatórios lógicos para discrepâncias ricas: processo, liquidacao, parecer.
    Porém, a API permite qualquer combinação (inclusive apenas processo ou apenas
    parecer). Quando algum estiver ausente, partes do relatório ficam vazias,
    mas o motor continua funcionando sem erro.
    """
    print(
        f"[LEARNING] Iniciando análise — linha do tempo completa:\n"
        f"  Amostragem PDF:  {amostragem_pdf_filename  or '(não enviado)'}\n"
        f"  Amostragem Word: {amostragem_word_filename or '(não enviado)'}\n"
        f"  Sentença:        {processo_filename}\n"
        f"  Liquidação:      {liquidacao_filename}\n"
        f"  Parecer:         {parecer_filename}\n"
        f"  Impugnação:      {impugnacao_filename    or '(não enviado)'}\n"
        f"  Cálculo PJC:     {calculo_pjc_filename   or '(não enviado)'}\n"
        f"  Manifestação:    {manifestacao_filename  or '(não enviado)'}"
    )

    # ── Fase base: lógica dos 5 arquivos existente ────────────────────────────
    relatorio = processar_cinco_arquivos(
        processo_bytes=processo_bytes,
        processo_filename=processo_filename,
        liquidacao_bytes=liquidacao_bytes,
        liquidacao_filename=liquidacao_filename,
        parecer_bytes=parecer_bytes,
        parecer_filename=parecer_filename,
        impugnacao_bytes=impugnacao_bytes,
        impugnacao_filename=impugnacao_filename,
        calculo_pjc_bytes=calculo_pjc_bytes,
        calculo_pjc_filename=calculo_pjc_filename,
    )

    dados_amostragem_pdf_result = None

    # ── Fase de Conhecimento 1: Amostragem PDF (tese vencedora) ───────────────
    if amostragem_pdf_bytes:
        print(f"[LEARNING] Analisando Amostragem PDF: {amostragem_pdf_filename}")
        dados_amostragem_pdf_result = _extrair_amostragem_pdf(amostragem_pdf_bytes, amostragem_pdf_filename)
        relatorio["amostragem_pdf"] = {
            "teses_provadas":      dados_amostragem_pdf_result.get("teses_provadas")      or [],
            "verbas_prova":        dados_amostragem_pdf_result.get("verbas_prova")        or [],
            "evidencias_utilizadas": dados_amostragem_pdf_result.get("evidencias_utilizadas") or [],
            "periodo_analisado":   dados_amostragem_pdf_result.get("periodo_analisado")   or "",
            "irregularidades":     dados_amostragem_pdf_result.get("irregularidades")     or [],
            "resumo":              dados_amostragem_pdf_result.get("resumo")              or "",
            "model_used":          dados_amostragem_pdf_result.get("model_used"),
            "erro":                dados_amostragem_pdf_result.get("erro"),
        }

    # ── Fase de Conhecimento 2: Amostragem Word (Style Transfer) ──────────────
    if amostragem_word_bytes:
        print(f"[LEARNING] Analisando Amostragem Word (Style Transfer): {amostragem_word_filename}")
        dados_word = _extrair_amostragem_word(amostragem_word_bytes, amostragem_word_filename)
        relatorio["amostragem_word"] = {
            "estilo":          dados_word.get("estilo")          or {},
            "style_atualizado": dados_word.get("style_atualizado", False),
            "model_used":      dados_word.get("model_used"),
            "erro":            dados_word.get("erro"),
        }

    # ── Cross-reference: Amostragem × Sentença → Regras Preditivas ───────────
    # (só executa quando Amostragem PDF foi enviada)
    if dados_amostragem_pdf_result:
        dados_sentenca_raw   = relatorio.get("sentenca")   or {}
        dados_liquidacao_raw = relatorio.get("liquidacao") or {}
        regras_preditivas = _gerar_regras_preditivas_amostragem(
            dados_amostragem_pdf_result,
            dados_sentenca_raw,
            dados_liquidacao_raw,
        )
        if regras_preditivas:
            relatorio["aprendizados"] = regras_preditivas + (relatorio.get("aprendizados") or [])
            print(f"[LEARNING] {len(regras_preditivas)} regra(s) preditiva(s) gerada(s) por cross-reference.")

    # ── Tríade Pericial: sempre montada com o que estiver disponível ──────────
    # Independe da presença de Amostragem PDF — garante que a UI nunca
    # exiba falso-negativo para arquivos que foram realmente enviados.
    _sentenca_raw   = relatorio.get("sentenca")    or {}
    _calculo_pjc_raw = relatorio.get("calculo_pjc") or None
    relatorio["triade_pericial"] = _resumir_triada_pericial(
        dados_amostragem_pdf_result,  # None se não enviada — tratado internamente
        _sentenca_raw,
        _calculo_pjc_raw,
    )

    # ── Fase de Conhecimento 3: Manifestação (retórica de combate) ───────────
    if manifestacao_bytes:
        print(f"[LEARNING] Analisando Manifestação Pericial: {manifestacao_filename}")
        dados_manifestacao_pericial = _extrair_manifestacao_pericial(manifestacao_bytes, manifestacao_filename)
        relatorio["manifestacao_pericial"] = {
            "frases_impacto":       dados_manifestacao_pericial.get("frases_impacto")       or [],
            "fundamentos_juridicos": dados_manifestacao_pericial.get("fundamentos_juridicos") or [],
            "padroes_ataque_defesa": dados_manifestacao_pericial.get("padroes_ataque_defesa") or [],
            "parametros_fraudados": dados_manifestacao_pericial.get("parametros_fraudados")  or [],
            "argumento_vencedor":   dados_manifestacao_pericial.get("argumento_vencedor")   or "",
            "verbas_em_disputa":    dados_manifestacao_pericial.get("verbas_em_disputa")    or [],
            "resumo":               dados_manifestacao_pericial.get("resumo")               or "",
            "style_atualizado":     dados_manifestacao_pericial.get("style_atualizado",     False),
            "model_used":           dados_manifestacao_pericial.get("model_used"),
            "erro":                 dados_manifestacao_pericial.get("erro"),
        }
        # Enriquece a Tríade (triade_pericial já existe agora, sempre)
        relatorio["triade_pericial"]["manifestacao"] = {
            "presente":           True,
            "argumento_vencedor": dados_manifestacao_pericial.get("argumento_vencedor") or "",
            "padroes_count":      len(dados_manifestacao_pericial.get("padroes_ataque_defesa") or []),
        }

    # ── Metadados completos ───────────────────────────────────────────────────
    arquivos = relatorio.get("arquivos_analisados") or {}
    arquivos["amostragem_pdf"]  = amostragem_pdf_filename  or None
    arquivos["amostragem_word"] = amostragem_word_filename or None
    arquivos["manifestacao"]    = manifestacao_filename    or None
    relatorio["arquivos_analisados"] = arquivos

    # ── Self-Healing Rule Engine: aprendizado autônomo ────────────────────────
    # Extrai hipóteses de regra das discrepâncias, atualiza o Knowledge Base e
    # avalia regras shadow existentes. Tudo em background, sem bloquear o fluxo.
    try:
        numero = relatorio.get("numero_processo", "")
        kb_resultado = processar_aprendizado_autonomo(relatorio, numero)
        relatorio["kb_aprendizado"] = kb_resultado
        print(
            f"[KB] Self-healing: {kb_resultado.get('hipoteses_extraidas', 0)} hipótese(s), "
            f"{kb_resultado.get('ativadas', 0)} regra(s) ativada(s), "
            f"stats={kb_resultado.get('stats_kb')}"
        )
    except Exception as e_kb:
        print(f"[KB] Aviso: erro no aprendizado autônomo (não crítico): {e_kb}")
        relatorio["kb_aprendizado"] = {"erro": str(e_kb)}

    total_disc = len(relatorio.get("discrepancias") or [])
    total_ap   = len(relatorio.get("aprendizados")  or [])
    print(f"[LEARNING] Análise completa — {total_disc} discrepância(s), {total_ap} aprendizado(s).")
    return relatorio


def processar_cinco_arquivos(
    processo_bytes: Optional[bytes] = None,
    processo_filename: str = "",
    liquidacao_bytes: Optional[bytes] = None,
    liquidacao_filename: str = "",
    parecer_bytes: Optional[bytes] = None,
    parecer_filename: str = "",
    impugnacao_bytes: Optional[bytes] = None,
    impugnacao_filename: str = "",
    calculo_pjc_bytes: Optional[bytes] = None,
    calculo_pjc_filename: str = "",
) -> Dict[str, Any]:
    """
    Ponto de entrada para o endpoint /lab/analisar (5 arquivos).

    Obrigatórios lógicos para discrepâncias cheias: processo, liquidação, parecer.
    Porém, o chamador pode omitir qualquer um; nesse caso o motor preenche
    dicionários vazios e apenas reduz a riqueza do relatório, sem erro.

    Opcionais: impugnação, cálculo .PJC.

    Não salva nada — apenas analisa. Salvamento é feito via /lab/salvar.
    """
    print(f"[LEARNING] Iniciando análise: "
          f"{processo_filename or '(sem processo)'} | {liquidacao_filename or '(sem liquidação)'} | {parecer_filename or '(sem parecer)'} "
          f"| {impugnacao_filename or '—'} | {calculo_pjc_filename or '—'}")

    # 1. Processo/Sentença — extração IA (opcional)
    if processo_bytes:
        dados_processo = _extrair_processo(processo_bytes, processo_filename or "processo.pdf")
    else:
        dados_processo = {"dados": {}}
        print("[LEARNING] Processo não enviado — sem dados de sentença.")

    # 2. Liquidação — opcional; sem ela, discrepâncias estarão vazias
    if liquidacao_bytes:
        dados_liquidacao = _extrair_liquidacao(liquidacao_bytes, liquidacao_filename)
    else:
        dados_liquidacao = {
            "verbas_calculadas": [],
            "indice_correcao": None,
            "juros_mora": None,
            "erro": "Liquidação não fornecida — comparação de verbas indisponível.",
        }
        print("[LEARNING] Liquidação não enviada — análise de discrepâncias parcial.")

    # 3. Parecer — fundamentos + trechos (igual manifestação anterior)
    if parecer_bytes:
        dados_parecer = _extrair_manifestacao(parecer_bytes)
    else:
        dados_parecer = {
            "texto_bruto": "",
            "fundamentos_juridicos": [],
            "discrepancias_levantadas": [],
            "erro": "Parecer não fornecido.",
        }
        print("[LEARNING] Parecer não enviado — sem fundamentos da perita.")

    # 4. Impugnação (opcional)
    dados_impugnacao = None
    if impugnacao_bytes:
        dados_impugnacao = _extrair_impugnacao(impugnacao_bytes, impugnacao_filename)

    # 5. Cálculo .PJC (opcional)
    dados_calculo_pjc = None
    if calculo_pjc_bytes:
        dados_calculo_pjc = _extrair_calculo_pjc(calculo_pjc_bytes, calculo_pjc_filename)

    # Relatório base (processo como sentença, liquidação, parecer como manifestação)
    relatorio = gerar_relatorio_discrepancia(
        dados_sentenca=dados_processo,
        dados_liquidacao=dados_liquidacao,
        dados_manifestacao=dados_parecer,
    )

    # Renomear chave "manifestacao" → "parecer" no relatório para consistência com a UI
    if "manifestacao" in relatorio:
        relatorio["parecer"] = relatorio.pop("manifestacao")

    # Enriquece com impugnação e cálculo PJC
    relatorio = _enriquecer_relatorio_com_extras(relatorio, dados_impugnacao, dados_calculo_pjc)

    # Metadados de origem dos arquivos
    relatorio["arquivos_analisados"] = {
        "processo":    processo_filename,
        "liquidacao":  liquidacao_filename,
        "parecer":     parecer_filename,
        "impugnacao":  impugnacao_filename or None,
        "calculo_pjc": calculo_pjc_filename or None,
    }

    print(f"[LEARNING] Análise concluída — {len(relatorio['discrepancias'])} discrepância(s).")
    return relatorio


# Mantém compatibilidade com versão anterior (3 arquivos)
def processar_trio_arquivos(
    sentenca_bytes: bytes,
    liquidacao_bytes: bytes,
    liquidacao_filename: str,
    manifestacao_bytes: bytes,
) -> Dict[str, Any]:
    return processar_cinco_arquivos(
        processo_bytes=sentenca_bytes,
        processo_filename="sentenca.pdf",
        liquidacao_bytes=liquidacao_bytes,
        liquidacao_filename=liquidacao_filename,
        parecer_bytes=manifestacao_bytes,
        parecer_filename="manifestacao.docx",
    )


__all__ = [
    "processar_sete_arquivos",
    "processar_cinco_arquivos",
    "processar_trio_arquivos",
    "preview_aprendizado",
    "salvar_aprendizado",
    "codify_insight",
    "processar_aprendizado_autonomo",
    "_evaluate_shadow_rules",
    "_LEARNING_LOG",
]
