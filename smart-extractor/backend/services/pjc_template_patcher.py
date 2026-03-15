"""
pjc_template_patcher.py — T1 v1.0 (11/03/2026)

Estratégia B — Patch cirúrgico via lxml sobre template .pjc real do usuário.

PRINCÍPIO: nunca gerar XML do zero. O template fornecido pelo usuário já é
válido no PJeCalc 2.14.0. O patcher substitui apenas os campos de identidade
do processo, preservando verbas, fórmulas, parâmetros e todos os IDs internos.

CAMPOS PATCHEADOS (14 alvos):
─────────────────────────────────────────────────────────────────────────────
  gprec/nomeBeneficiario                    ← reclamante
  gprec/documentoFiscalBeneficiario         ← cpf_reclamante (se disponível)
  Calculo/dataAdmissao                      ← data_admissao → epoch ms BRT
  Calculo/dataDemissao                      ← data_demissao → epoch ms BRT
  Calculo/dataAjuizamento                   ← data_ajuizamento → epoch ms BRT
  Calculo/valorCargaHorariaPadrao           ← divisor_horas (float 4 casas)
  Processo/reclamante/Reclamante/nome       ← reclamante
  Processo/reclamado/Reclamado/nome         ← reclamada
  IdentificadorDoProcesso/numero            ← CNJ parseado
  IdentificadorDoProcesso/digito
  IdentificadorDoProcesso/ano
  IdentificadorDoProcesso/justica
  IdentificadorDoProcesso/regiao
  IdentificadorDoProcesso/vara
  parametrosDeAtualizacao/apartirDeOutroIndice    ← data_ajuizamento
  CombinacaoDeIndice/apartirDeOutroIndice         ← data_ajuizamento
  CombinacaoDeJuros/apartirDeOutroJuros           ← data_ajuizamento
  fgts/Fgts/periodoInicial                        ← data_admissao
  fgts/Fgts/periodoFinal                          ← data_demissao
  inss/.../InssSobreSalariosDevidos/dataInicioPeriodo  ← data_admissao
  inss/.../InssSobreSalariosDevidos/dataTerminoPeriodo ← data_demissao

CAMPOS PRESERVADOS (nunca tocados):
─────────────────────────────────────────────────────────────────────────────
  Todos os <id> e <versao> internos
  Estrutura completa de <verbas>
  Fórmulas e multiplicadores
  hashCodeLiquidacao / hashLiquidacao
  <municipio> (externalRef do tribunal)
  <versaoDoSistema> (mantém versão do template do usuário)
  Ocorrências de INSS já calculadas
  Histórico salarial

Interface pública:
─────────────────────────────────────────────────────────────────────────────
  aplicar_patch(template_xml: bytes, dados: dict) -> bytes
  validar_patch(xml_patcheado: bytes) -> list[str]
  extrair_versao_template(xml: bytes) -> str

Log prefix: [PJC-PATCH]
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Optional

from lxml import etree


# ── Constantes ────────────────────────────────────────────────────────────────

_ENCODING_PJC = "iso-8859-1"

# Campos obrigatórios que devem estar presentes após o patch
_CAMPOS_CRITICOS = [
    "dataAdmissao",
    "dataDemissao",
    "dataAjuizamento",
    "valorCargaHorariaPadrao",
]

_BRT = timezone(timedelta(hours=-3))


# ── Utilitários (portados do pjc_exporter_v5.9 — validados contra arquivo real) ──

def _para_epoch_ms(valor: Optional[str]) -> Optional[str]:
    """
    Converte data para epoch ms em BRT (UTC-3).

    Formatos aceitos: DD/MM/YYYY · YYYY-MM-DD · epoch ms (13 dígitos).
    Retorna None se inválida (diferente do exporter que retorna "null" —
    aqui None indica que o nó NÃO deve ser patcheado).

    Validado contra template real (calc_id=7099):
      01/02/2017 → 1485918000000  ✅ dataAdmissao
      08/05/2019 → 1557284400000  ✅ dataDemissao
      28/01/2020 → 1580180400000  ✅ dataAjuizamento
    """
    if not valor:
        return None
    valor = str(valor).strip()

    if re.match(r"^\d{13}$", valor):
        return valor

    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", valor)
    if m:
        try:
            dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), tzinfo=_BRT)
            return str(int(dt.timestamp() * 1000))
        except Exception:
            return None

    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", valor)
    if m:
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=_BRT)
            return str(int(dt.timestamp() * 1000))
        except Exception:
            return None

    return None


def _parsear_cnj(numero: Optional[str]) -> Optional[dict]:
    """
    Extrai 6 componentes do número CNJ: NNNNNNN-DD.AAAA.J.TT.OOOO.
    Retorna None se o formato não for reconhecido (não patcheia).
    """
    if not numero:
        return None
    m = re.search(r"(\d{7})-(\d{2})\.(\d{4})\.(\d{1})\.(\d{2})\.(\d{4})", numero.strip())
    if not m:
        return None
    return {
        "numero":  str(int(m.group(1))),
        "digito":  m.group(2),
        "ano":     m.group(3),
        "justica": m.group(4),
        "regiao":  str(int(m.group(5))),
        "vara":    str(int(m.group(6))),
    }


def _set_text(node: Optional[etree._Element], valor: str) -> bool:
    """
    Define o texto de um nó lxml de forma segura.
    Retorna True se o nó existe e foi atualizado.
    """
    if node is None:
        return False
    node.text = valor
    # Remover subelementos caso o nó fosse anteriormente um objeto complexo
    for child in list(node):
        node.remove(child)
    return True


def _find_first(root: etree._Element, *xpaths: str) -> Optional[etree._Element]:
    """
    Tenta múltiplos XPaths e retorna o primeiro resultado não-nulo.
    Útil para lidar com variações entre versões do template.
    """
    for xpath in xpaths:
        results = root.xpath(xpath)
        if results:
            return results[0]
    return None


# ── Funções de patch por grupo ────────────────────────────────────────────────

def _patch_gprec(root: etree._Element, dados: dict, log: list) -> None:
    """Patcha o bloco <gprec> — dados do beneficiário."""
    reclamante = dados.get("reclamante", "")
    cpf = dados.get("cpf_reclamante", "")

    if reclamante:
        node = _find_first(root, "gprec/nomeBeneficiario")
        if _set_text(node, reclamante):
            log.append("[PJC-PATCH] gprec/nomeBeneficiario → OK")
        else:
            log.append("[PJC-PATCH] WARN: gprec/nomeBeneficiario não encontrado")

    if cpf:
        node = _find_first(root, "gprec/documentoFiscalBeneficiario")
        if _set_text(node, cpf):
            log.append("[PJC-PATCH] gprec/documentoFiscalBeneficiario → OK")


def _patch_datas_calculo(root: etree._Element, dados: dict, log: list) -> None:
    """Patcha as datas principais do <Calculo> raiz."""
    mapeamento = [
        ("dataAdmissao",          dados.get("data_admissao")),
        ("dataDemissao",          dados.get("data_demissao")),
        ("dataAjuizamento",       dados.get("data_ajuizamento")),
    ]
    for campo, valor_raw in mapeamento:
        epoch = _para_epoch_ms(valor_raw)
        if epoch is None:
            log.append(f"[PJC-PATCH] SKIP: {campo} — valor ausente ou inválido ({valor_raw!r})")
            continue
        # XPath direto: filho imediato de <Calculo> raiz (não internalRef)
        nodes = root.xpath(f"{campo}[not(parent::Calculo/internalRef)]")
        # Fallback: qualquer filho direto da raiz com esse nome
        if not nodes:
            nodes = [child for child in root if child.tag == campo]
        if nodes:
            nodes[0].text = epoch
            log.append(f"[PJC-PATCH] {campo} → {epoch} ✓")
        else:
            log.append(f"[PJC-PATCH] WARN: {campo} não encontrado na raiz")


def _patch_carga_horaria(root: etree._Element, dados: dict, log: list) -> None:
    """Patcha o divisor de horas."""
    carga_raw = dados.get("divisor_horas") or dados.get("jornada", {})
    if isinstance(carga_raw, dict):
        carga_raw = carga_raw.get("divisor")

    if not carga_raw:
        log.append("[PJC-PATCH] SKIP: valorCargaHorariaPadrao — divisor_horas ausente")
        return

    try:
        carga_val = f"{float(str(carga_raw).replace(',', '.')):.4f}"
    except Exception:
        log.append(f"[PJC-PATCH] WARN: divisor_horas inválido ({carga_raw!r})")
        return

    nodes = [child for child in root if child.tag == "valorCargaHorariaPadrao"]
    if nodes:
        nodes[0].text = carga_val
        log.append(f"[PJC-PATCH] valorCargaHorariaPadrao → {carga_val} ✓")
    else:
        log.append("[PJC-PATCH] WARN: valorCargaHorariaPadrao não encontrado")


def _patch_processo(root: etree._Element, dados: dict, log: list) -> None:
    """Patcha reclamante, reclamada e identificador CNJ dentro de <processo>."""
    reclamante = dados.get("reclamante", "")
    reclamada  = dados.get("reclamada", "")
    numero     = dados.get("numero_processo", "")

    if reclamante:
        node = _find_first(root,
            "processo/Processo/reclamante/Reclamante/nome",
        )
        if _set_text(node, reclamante):
            log.append("[PJC-PATCH] Processo/reclamante/nome → OK")
        else:
            log.append("[PJC-PATCH] WARN: Processo/reclamante/nome não encontrado")

    if reclamada:
        node = _find_first(root,
            "processo/Processo/reclamado/Reclamado/nome",
        )
        if _set_text(node, reclamada):
            log.append("[PJC-PATCH] Processo/reclamado/nome → OK")
        else:
            log.append("[PJC-PATCH] WARN: Processo/reclamado/nome não encontrado")

    cnj = _parsear_cnj(numero)
    if cnj:
        base = "processo/Processo/identificador/IdentificadorDoProcesso"
        for campo, valor in cnj.items():
            node = _find_first(root, f"{base}/{campo}")
            if _set_text(node, valor):
                log.append(f"[PJC-PATCH] IdentificadorDoProcesso/{campo} → {valor} ✓")
            else:
                log.append(f"[PJC-PATCH] WARN: IdentificadorDoProcesso/{campo} não encontrado")
    else:
        log.append(f"[PJC-PATCH] SKIP: numero_processo CNJ inválido ({numero!r})")


def _patch_parametros_atualizacao(root: etree._Element, dados: dict, log: list) -> None:
    """
    Patcha data de ajuizamento nos blocos de índices e juros.
    Esses campos determinam a partir de quando incide SELIC (ADC 58).
    """
    epoch_ajuiz = _para_epoch_ms(dados.get("data_ajuizamento"))
    if epoch_ajuiz is None:
        log.append("[PJC-PATCH] SKIP: parametrosDeAtualizacao — data_ajuizamento ausente")
        return

    alvos = [
        # apartirDeOutroIndice (raiz de ParametrosDeAtualizacao)
        "parametrosDeAtualizacao/ParametrosDeAtualizacao/apartirDeOutroIndice",
        # CombinacaoDeIndice
        "parametrosDeAtualizacao/ParametrosDeAtualizacao/listaDeCombinacaoDeIndices/Set/CombinacaoDeIndice/apartirDeOutroIndice",
        # CombinacaoDeJuros — data em que SELIC passa a valer
        "parametrosDeAtualizacao/ParametrosDeAtualizacao/listaDeCombinacaoDeJuros/Set/CombinacaoDeJuros/apartirDeOutroJuros",
    ]
    for xpath in alvos:
        nodes = root.xpath(xpath)
        for node in nodes:
            node.text = epoch_ajuiz
        if nodes:
            log.append(f"[PJC-PATCH] {xpath.split('/')[-1]} → {epoch_ajuiz} ✓ ({len(nodes)} nó(s))")
        else:
            log.append(f"[PJC-PATCH] WARN: {xpath} não encontrado")


def _patch_fgts(root: etree._Element, dados: dict, log: list) -> None:
    """Patcha períodos do bloco <fgts>."""
    epoch_adm = _para_epoch_ms(dados.get("data_admissao"))
    epoch_dem = _para_epoch_ms(dados.get("data_demissao"))

    base = "fgts/Fgts"

    if epoch_adm:
        nodes = root.xpath(f"{base}/periodoInicial")
        for n in nodes:
            n.text = epoch_adm
        if nodes:
            log.append(f"[PJC-PATCH] fgts/periodoInicial → {epoch_adm} ✓")

    if epoch_dem:
        nodes = root.xpath(f"{base}/periodoFinal")
        for n in nodes:
            n.text = epoch_dem
        if nodes:
            log.append(f"[PJC-PATCH] fgts/periodoFinal → {epoch_dem} ✓")


def _patch_inss(root: etree._Element, dados: dict, log: list) -> None:
    """
    Patcha apenas os períodos do InssSobreSalariosDevidos (nó raiz do INSS).
    NÃO toca as ocorrências detalhadas — essas são calculadas e preservadas.
    """
    epoch_adm = _para_epoch_ms(dados.get("data_admissao"))
    epoch_dem = _para_epoch_ms(dados.get("data_demissao"))

    # Apenas o primeiro InssSobreSalariosDevidos (período global do contrato)
    xpath_base = "inss/Inss/inssSobreSalariosDevidos/InssSobreSalariosDevidos"

    if epoch_adm:
        nodes = root.xpath(f"{xpath_base}/dataInicioPeriodo")
        if nodes:
            nodes[0].text = epoch_adm
            log.append(f"[PJC-PATCH] inss/InssSobreSalariosDevidos/dataInicioPeriodo → {epoch_adm} ✓")

    if epoch_dem:
        nodes = root.xpath(f"{xpath_base}/dataTerminoPeriodo")
        if nodes:
            nodes[0].text = epoch_dem
            log.append(f"[PJC-PATCH] inss/InssSobreSalariosDevidos/dataTerminoPeriodo → {epoch_dem} ✓")


# ── API pública ───────────────────────────────────────────────────────────────

def aplicar_patch(template_xml: bytes, dados: dict) -> bytes:
    """
    Aplica patch cirúrgico nos campos de identidade do processo.

    Args:
        template_xml: Bytes do .pjc original do usuário (ISO-8859-1 ou UTF-8).
        dados:        Dict extraído pelo pipeline (mesmo formato de models.py).

    Returns:
        Bytes do .pjc patcheado, pronto para download.
        Encoding preservado: ISO-8859-1 com declaração XML.

    Raises:
        ValueError: Se o template_xml não for um XML válido do PJeCalc.
    """
    numero = dados.get("numero_processo", "N/A")
    log: list[str] = []

    log.append(f"[PJC-PATCH] Iniciando patch | Processo: {numero}")

    # Parse — lxml detecta encoding automaticamente via declaração XML
    try:
        parser = etree.XMLParser(encoding=_ENCODING_PJC, recover=True)
        root = etree.fromstring(template_xml, parser=parser)
    except etree.XMLSyntaxError as exc:
        raise ValueError(f"[PJC-PATCH] Template XML inválido: {exc}") from exc

    if root is None:
        raise ValueError("[PJC-PATCH] Template XML inválido: não foi possível fazer o parse.")

    if root.tag != "Calculo":
        raise ValueError(
            f"[PJC-PATCH] Tag raiz esperada: <Calculo>, encontrada: <{root.tag}>. "
            "Envie um .pjc gerado pelo PJeCalc."
        )

    # ── Aplicar patches em ordem de dependência ───────────────────────────────
    _patch_gprec(root, dados, log)
    _patch_datas_calculo(root, dados, log)
    _patch_carga_horaria(root, dados, log)
    _patch_processo(root, dados, log)
    _patch_parametros_atualizacao(root, dados, log)
    _patch_fgts(root, dados, log)
    _patch_inss(root, dados, log)

    # ── Serializar preservando ISO-8859-1 ─────────────────────────────────────
    resultado = etree.tostring(
        root,
        xml_declaration=True,
        encoding=_ENCODING_PJC,
        pretty_print=True,
    )

    # Garantir CRLF — PJeCalc espera \r\n (confirmado no template real)
    resultado = resultado.replace(b"\n", b"\r\n")

    log.append(f"[PJC-PATCH] ✓ Patch concluído | {len(resultado):,} bytes")
    for linha in log:
        print(linha)

    return resultado


def validar_patch(xml_patcheado: bytes) -> list[str]:
    """
    Valida o XML patcheado verificando campos críticos.

    Returns:
        Lista de erros encontrados. Lista vazia = patch válido.
    """
    erros: list[str] = []

    try:
        parser = etree.XMLParser(encoding=_ENCODING_PJC, recover=True)
        root = etree.fromstring(xml_patcheado, parser=parser)
    except etree.XMLSyntaxError as exc:
        return [f"XML inválido após patch: {exc}"]

    if root.tag != "Calculo":
        erros.append(f"Tag raiz incorreta: {root.tag}")
        return erros

    # Verificar campos críticos com valor não-nulo
    for campo in _CAMPOS_CRITICOS:
        nodes = [child for child in root if child.tag == campo]
        if not nodes:
            erros.append(f"Campo crítico ausente: {campo}")
            continue
        texto = (nodes[0].text or "").strip()
        if not texto or texto == "null":
            erros.append(f"Campo crítico sem valor: {campo} = {texto!r}")

    # Verificar processo
    reclamante_nodes = root.xpath("processo/Processo/reclamante/Reclamante/nome")
    if not reclamante_nodes or not (reclamante_nodes[0].text or "").strip():
        erros.append("Processo/reclamante/nome vazio após patch")

    reclamada_nodes = root.xpath("processo/Processo/reclamado/Reclamado/nome")
    if not reclamada_nodes or not (reclamada_nodes[0].text or "").strip():
        erros.append("Processo/reclamado/nome vazio após patch")

    # Verificar SELIC (ADC 58) — CombinacaoDeJuros deve existir
    selic_nodes = root.xpath(
        "parametrosDeAtualizacao/ParametrosDeAtualizacao"
        "/listaDeCombinacaoDeJuros/Set/CombinacaoDeJuros/outroJuros"
    )
    for node in selic_nodes:
        if node.text != "SELIC":
            erros.append(
                f"CombinacaoDeJuros/outroJuros esperado SELIC, encontrado: {node.text}"
            )

    if not erros:
        print("[PJC-PATCH] ✓ Validação OK — nenhum erro encontrado")
    else:
        for e in erros:
            print(f"[PJC-PATCH] ERRO: {e}")

    return erros


def extrair_versao_template(xml: bytes) -> str:
    """
    Extrai a versão do sistema a partir do campo <versaoDoSistema>.

    Returns:
        String da versão (ex: '2.14.0') ou 'desconhecida' se não encontrada.
    """
    try:
        parser = etree.XMLParser(encoding=_ENCODING_PJC, recover=True)
        root = etree.fromstring(xml, parser=parser)
        nodes = [child for child in root if child.tag == "versaoDoSistema"]
        if nodes and nodes[0].text:
            return nodes[0].text.strip()
    except Exception:
        pass
    return "desconhecida"


def gerar_nome_arquivo(dados: dict) -> str:
    """Gera nome do .pjc patcheado no padrão do PJeCalc."""
    numero = re.sub(r"[^0-9]", "", dados.get("numero_processo") or "PROCESSO")
    hoje   = datetime.now().strftime("%d%m%Y")
    return f"PROCESSO_{numero}_SMART_EXTRACTOR_{hoje}.pjc"