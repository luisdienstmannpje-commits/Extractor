"""
pjc_exporter.py — v5.9: Patch campos novos PJeCalc 2.14.0 (PJEKZ-88144)

CORREÇÕES v5.9 (10/03/2026) — causa raiz do "Arquivo inválido" identificada
──────────────────────────────────────────────────────────────────────────────────────
  ✅ CRÍTICO: 5 campos novos adicionados em <ParametrosDeAtualizacao>
             Descobertos via análise dos SQLs de migração 2.14.0:
             PJC_2.14.0_002__DDL_PJEKZ-88144_ESTRUTURA.sql

             ALTER TABLE TBATUALIZACAO ADD SFLATUALIZARREGRAPRECATORIO DEFAULT 'N' NOT NULL
             → <atualizarRegraPrecatorio>false</atualizarRegraPrecatorio>  ← OBRIGATÓRIO

             ALTER TABLE TBATUALIZACAO ADD STPESFERAPRECATORIO VARCHAR(1)
             → <esferaPrecatorio>null</esferaPrecatorio>

             ALTER TABLE TBATUALIZACAO ADD STPPRECATORIO VARCHAR(3)  (domínio: PRE/RPV)
             → <tipoPrecatorio>null</tipoPrecatorio>

             ALTER TABLE TBATUALIZACAO ADD DDTINICIOPERIODOGRACA DATE
             → <dataInicioPeriodoGraca>null</dataInicioPeriodoGraca>

             ALTER TABLE TBATUALIZACAO ADD DDTFIMPERIODOGRACA DATE
             → <dataFimPeriodoGraca>null</dataFimPeriodoGraca>

  DIAGNÓSTICO COMPLETO:
  - Arquivo real 2.13.0 também falha no 2.14.0 → incompatibilidade de schema
  - HTTP 200 com "Arquivo inválido" → validação de negócio no JSF/RichFaces
  - XStream tenta deserializar ParametrosDeAtualizacao e falha nos campos novos
  - SFLATUALIZARREGRAPRECATORIO tem DEFAULT 'N' NOT NULL → campo obrigatório
  - Campos descobertos via unzip dos JARs + análise dos SQLs de migração

CORREÇÕES v5.8 (09/03/2026) — diff direto contra arquivo real PJeCalc 2.13.0
──────────────────────────────────────────────────────────────────────────────────────
  ✅ CRÍTICO: indicesAcumulados → MES_SUBSEQUENTE_E_MES_DO_VENCIMENTO
  ✅ CRÍTICO: CombinacaoDeJuros.outroJuros → SELIC (ADC 58)
  ✅ CRÍTICO: CombinacaoDeJuros.apartirDeOutroJuros → epoch_ajuizamento
  ✅ CRÍTICO: baseDeJurosDasVerbas → VERBAS
  ✅ ALTO:    combinarOutroIndice → true
  ✅ ALTO:    apartirDeOutroIndice → epoch_ajuizamento
  ✅ ALTO:    ignorarTaxaNegativa → true
  ✅ ALTO:    Inss.limitarTeto → false
  ✅ ALTO:    Fgts.excluirAvisoDaMulta → false
  ✅ ALTO:    correcaoPrevidenciariaDosSalariosPagosDoINSS → false
  ✅ ALTO:    jurosPrevidenciariosDosSalariosPagosDoINSS → false
  ✅ ALTO:    aplicarMultaDosSalariosPagosDoINSS → false
  ✅ MÉDIO:   salarioPagoFormaAplicacao → null

CORREÇÕES v5.5 (09/03/2026) — análise direta do arquivo real
──────────────────────────────────────────────────────────────────────────────────────
  ✅ CRÍTICO: Removido ZIP wrapper — arquivo real é XML puro ISO-8859-1
  ✅ CRÍTICO: Adicionado <gprec> como 1º filho obrigatório de <Calculo>
  ✅ CRÍTICO: Adicionado <dadosEstruturados> como 2º filho obrigatório
  ✅ CRÍTICO: <versao>11</versao>
  ✅ CRÍTICO: <id>0</id> em todos os blocos filhos com Long Java
  ✅ ALTO:    <versaoDoSistema>2.14.0</versaoDoSistema>
  ✅ ALTO:    <municipio>null</municipio>
  ✅ MÉDIO:   _gerar_id() com contador sequencial local

RELACIONAMENTO DE IDs (confirmado no arquivo real, calc_id=7099):
──────────────────────────────────────────────────────────────────
  Calculo.id              = calc_id        (ex: 1000)
  Processo.id             = calc_id
  ParametrosDeAtualizacao.id = calc_id
  CustasJudiciais.id      = calc_id
  Fgts.id                 = calc_id - 3   (ex:  997)
  Inss.id                 = calc_id - 2   (ex:  998)
  InssSobreSalariosDevidos.id = calc_id - 2
  CombinacaoDeJuros.id    = calc_id + 4   (ex: 1004)
  Irpf.id                 = 0
  SeguroDesemprego.id     = 0
  SalarioFamilia.id       = 0
  Todos <internalRef>     = calc_id

Uso:
    from services.pjc_exporter import exportar_pjc, gerar_nome_arquivo
    pjc_bytes = exportar_pjc(dados_finais)
    nome      = gerar_nome_arquivo(dados_finais)
"""

import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional


# ── Constantes ────────────────────────────────────────────────────────────────

_CALC_ID_BASE = 1000

_VERSAO_SISTEMA = "2.14.0"
_VERSAO_CALCULO = "11"


# ── Conversor de data ─────────────────────────────────────────────────────────

def _para_epoch_ms(valor: Optional[str]) -> str:
    """
    Converte data para epoch em milissegundos no padrão PJeCalc.

    DESCOBERTA CRÍTICA (09/03/2026) — confirmada contra arquivo real:
    O PJeCalc armazena datas como midnight UTC-3 (horário de Brasília).

    Validação contra PROCESSO_00100708720205030092:
      01/02/2017 → 1485918000000  ✅ (dataAdmissao)
      08/05/2019 → 1557284400000  ✅ (dataDemissao)
      28/01/2020 → 1580180400000  ✅ (dataAjuizamento)

    Aceita: DD/MM/YYYY, YYYY-MM-DD, epoch ms (string de 13 dígitos).
    Retorna "null" se inválida.
    """
    if not valor:
        return "null"
    valor = str(valor).strip()

    if re.match(r"^\d{13}$", valor):
        return valor

    _BRT = timezone(timedelta(hours=-3))

    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", valor)
    if m:
        try:
            dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)),
                          tzinfo=_BRT)
            return str(int(dt.timestamp() * 1000))
        except Exception:
            return "null"

    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", valor)
    if m:
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                          tzinfo=_BRT)
            return str(int(dt.timestamp() * 1000))
        except Exception:
            return "null"

    return "null"


def _hoje_epoch_ms() -> str:
    """Epoch ms do momento atual em BRT (UTC-3)."""
    _BRT = timezone(timedelta(hours=-3))
    return str(int(datetime.now(tz=_BRT).timestamp() * 1000))


# ── Parser CNJ ────────────────────────────────────────────────────────────────

def _parsear_cnj(numero: Optional[str]) -> dict:
    """
    Extrai componentes do número CNJ: NNNNNNN-DD.AAAA.J.TT.OOOO.
    Retorna defaults de JT 5ª Região se o formato não for reconhecido.
    """
    vazio = {
        "numero": "0", "digito": "0", "ano": "2024",
        "justica": "5", "regiao": "3", "vara": "0",
    }
    if not numero:
        return vazio
    m = re.search(r"(\d{7})-(\d{2})\.(\d{4})\.(\d{1})\.(\d{2})\.(\d{4})", numero.strip())
    if m:
        return {
            "numero":  str(int(m.group(1))),
            "digito":  m.group(2),
            "ano":     m.group(3),
            "justica": m.group(4),
            "regiao":  str(int(m.group(5))),
            "vara":    str(int(m.group(6))),
        }
    return vazio


# ── Escape seguro para ISO-8859-1 ─────────────────────────────────────────────

def _safe(valor: Optional[str]) -> str:
    """
    Escapa valor para uso seguro em XML ISO-8859-1.
    Caracteres fora de latin-1 → &#NNN;
    Caracteres especiais XML (&, <, >) → entidades XML.
    """
    if not valor:
        return ""
    resultado = []
    for ch in str(valor):
        if ch == "&":
            resultado.append("&amp;")
        elif ch == "<":
            resultado.append("&lt;")
        elif ch == ">":
            resultado.append("&gt;")
        else:
            try:
                ch.encode("iso-8859-1")
                resultado.append(ch)
            except UnicodeEncodeError:
                resultado.append(f"&#{ord(ch)};")
    return "".join(resultado)


# ── Bloco <gprec> ─────────────────────────────────────────────────────────────

def _build_gprec(epoch_hoje: str, reclamante: str) -> str:
    nome = _safe(reclamante) if reclamante else ""
    return (
        "<gprec>"
        f"<dataCalculo>{epoch_hoje}</dataCalculo>"
        f"<nomeBeneficiario>{nome}</nomeBeneficiario>"
        "<documentoFiscalBeneficiario></documentoFiscalBeneficiario>"
        "<liquidoExequente>0</liquidoExequente>"
        "<inssBeneficiario>0</inssBeneficiario>"
        "<inssExecutado>0</inssExecutado>"
        "<impostoRenda>0.00</impostoRenda>"
        "<depositoFgts>0</depositoFgts>"
        "<custasJudiciais>0</custasJudiciais>"
        "<honorariosReclamante></honorariosReclamante>"
        "<honorariosReclamado></honorariosReclamado>"
        "</gprec>"
    )


# ── Bloco <dadosEstruturados> ─────────────────────────────────────────────────

def _build_dados_estruturados(epoch_hoje: str) -> str:
    return (
        "<dadosEstruturados>"
        f"<dataLiquidacao>{epoch_hoje}</dataLiquidacao>"
        "<hashLiquidacao></hashLiquidacao>"
        "<contrSocialDezPorcento>0</contrSocialDezPorcento>"
        "<contrSocialMeioPorcento>0</contrSocialMeioPorcento>"
        "<custasReclamado>0</custasReclamado>"
        "<custasReclamante>0</custasReclamante>"
        "<debitoReclamantePensaoAlimenticia>0</debitoReclamantePensaoAlimenticia>"
        "<debitoReclamantePrevidenciaPrivada>0</debitoReclamantePrevidenciaPrivada>"
        "<fgtsDepositoContaVinculada>0</fgtsDepositoContaVinculada>"
        "<impostoRenda>0.00</impostoRenda>"
        "<inssReclamado>0</inssReclamado>"
        "<inssReclamante>0</inssReclamante>"
        "<jurosMora>null</jurosMora>"
        "<jurosPrevidenciaPrivada>null</jurosPrevidenciaPrivada>"
        "<valorPrincipal>0</valorPrincipal>"
        "<tipoRegistroCalculo>CALCULO</tipoRegistroCalculo>"
        "<multas></multas>"
        "<honorarios></honorarios>"
        "</dadosEstruturados>"
    )


# ── Builder do histórico salarial ─────────────────────────────────────────────

def _build_historico_salarial(calc_id: str,
                               epoch_admissao: str,
                               salario_base: Optional[str]) -> str:
    _ = calc_id, epoch_admissao, salario_base
    return "<historicosSalariais><Set></Set></historicosSalariais>"


# ── Builder do XML principal ──────────────────────────────────────────────────

def _build_xml(dados: dict) -> bytes:

    calc_id  = str(_CALC_ID_BASE)
    fgts_id  = str(_CALC_ID_BASE - 3)
    inss_id  = str(_CALC_ID_BASE - 2)
    param_id = calc_id
    comb_id  = str(_CALC_ID_BASE + 4)

    cnj            = _parsear_cnj(dados.get("numero_processo"))
    epoch_admissao = _para_epoch_ms(dados.get("data_admissao"))
    epoch_demissao = _para_epoch_ms(dados.get("data_demissao"))
    epoch_ajuiz    = _para_epoch_ms(dados.get("data_ajuizamento"))
    epoch_hoje     = _hoje_epoch_ms()

    carga = dados.get("divisor_horas") or "220"
    try:
        carga_val = f"{float(str(carga).replace(',', '.')):.4f}"
    except Exception:
        carga_val = "220.0000"

    multa_fgts    = "true" if dados.get("fgts_periodo_completo") else "false"
    historico_xml = _build_historico_salarial(calc_id, epoch_admissao, dados.get("salario_base"))

    reclamante_nome  = dados.get("reclamante") or ""
    reclamada_nome   = dados.get("reclamada") or ""

    xml = (
        '<?xml version="1.0" encoding="ISO-8859-1"?>'
        "<Calculo>"

        + _build_gprec(epoch_hoje, reclamante_nome) +
        _build_dados_estruturados(epoch_hoje) +

        f"<id>{calc_id}</id>"
        f"<versao>{_VERSAO_CALCULO}</versao>"
        "<atualizacao>null</atualizacao>"
        "<hashCodeLiquidacao>null</hashCodeLiquidacao>"
        f"<dataCriacao>{epoch_hoje}</dataCriacao>"
        f"<dataAdmissao>{epoch_admissao}</dataAdmissao>"
        f"<dataDemissao>{epoch_demissao}</dataDemissao>"
        f"<dataAjuizamento>{epoch_ajuiz}</dataAjuizamento>"
        "<valorUltimaRemuneracao>null</valorUltimaRemuneracao>"
        "<valorMaiorRemuneracao>null</valorMaiorRemuneracao>"
        "<dataInicioCalculo>null</dataInicioCalculo>"
        "<dataTerminoCalculo>null</dataTerminoCalculo>"
        f"<valorCargaHorariaPadrao>{carga_val}</valorCargaHorariaPadrao>"
        "<sabadoDiaUtil>true</sabadoDiaUtil>"
        "<projetaAvisoIndenizado>true</projetaAvisoIndenizado>"
        "<consideraFeriadoEstadual>true</consideraFeriadoEstadual>"
        "<prescricaoFgts>false</prescricaoFgts>"
        "<prescricaoQuinquenal>false</prescricaoQuinquenal>"
        "<limitarAvosAoPeriodoDoCalculo>false</limitarAvosAoPeriodoDoCalculo>"
        "<zeraValorNegativo>false</zeraValorNegativo>"
        "<consideraFeriadoMunicipal>true</consideraFeriadoMunicipal>"
        "<tipoCalculo>ADVOGADO</tipoCalculo>"
        "<prazoFeriasProporcional>null</prazoFeriasProporcional>"
        "<dataDeLiquidacao>null</dataDeLiquidacao>"
        "<regimeDoContrato>INTEGRAL</regimeDoContrato>"
        "<indicesAcumulados>MES_SUBSEQUENTE_E_MES_DO_VENCIMENTO</indicesAcumulados>"
        "<usuarioCriador>offline</usuarioCriador>"
        "<apuracaoPrazoDoAvisoPrevio>APURACAO_CALCULADA</apuracaoPrazoDoAvisoPrevio>"
        "<prazoAvisoInformado>null</prazoAvisoInformado>"
        "<ativo>true</ativo>"
        "<processoInformadoManualmente>false</processoInformadoManualmente>"
        "<comentarios></comentarios>"
        "<idSetor>0</idSetor>"
        "<instancia>null</instancia>"
        "<validado>false</validado>"
        "<hashCalculoCorreto>false</hashCalculoCorreto>"
        "<hashAtualizacaoCorreto>false</hashAtualizacaoCorreto>"
        "<diaFechamentoMes>31</diaFechamentoMes>"
        "<calculoExterno>false</calculoExterno>"
        "<parcelasAtualizaveisCreditosReclamante>null</parcelasAtualizaveisCreditosReclamante>"
        "<parcelasAtualizaveisDescontoCreditosReclamante>null</parcelasAtualizaveisDescontoCreditosReclamante>"
        "<parcelasAtualizaveisOutrosDebitosReclamado>null</parcelasAtualizaveisOutrosDebitosReclamado>"
        "<parcelasAtualizaveisDebitosReclamante>null</parcelasAtualizaveisDebitosReclamante>"
        f"<versaoDoSistema>{_VERSAO_SISTEMA}</versaoDoSistema>"

        # ── processo ──────────────────────────────────────────────────────────
        "<processo><Processo>"
        f"<id>{calc_id}</id>"
        "<versao>0</versao>"
        "<valorDaCausa>null</valorDaCausa>"
        "<dataAutuacao>null</dataAutuacao>"
        f"<calculo><Calculo><internalRef>{calc_id}</internalRef></Calculo></calculo>"
        "<identificador><IdentificadorDoProcesso>"
        f"<numero>{cnj['numero']}</numero>"
        f"<ano>{cnj['ano']}</ano>"
        f"<justica>{cnj['justica']}</justica>"
        f"<regiao>{cnj['regiao']}</regiao>"
        f"<vara>{cnj['vara']}</vara>"
        f"<digito>{cnj['digito']}</digito>"
        "</IdentificadorDoProcesso></identificador>"
        "<reclamante><Reclamante>"
        "<tipoDocumentoPrevidenciario>null</tipoDocumentoPrevidenciario>"
        "<numeroDocumentoPrevidenciario>null</numeroDocumentoPrevidenciario>"
        f"<nome>{_safe(reclamante_nome)}</nome>"
        "<tipoDocumentoFiscal>null</tipoDocumentoFiscal>"
        "<numeroDocumentoFiscal>null</numeroDocumentoFiscal>"
        "</Reclamante></reclamante>"
        "<reclamado><Reclamado>"
        f"<nome>{_safe(reclamada_nome)}</nome>"
        "<tipoDocumentoFiscal>null</tipoDocumentoFiscal>"
        "<numeroDocumentoFiscal>null</numeroDocumentoFiscal>"
        "</Reclamado></reclamado>"
        "<advogadosReclamante><List></List></advogadosReclamante>"
        "<advogadosReclamado><List></List></advogadosReclamado>"
        "</Processo></processo>"

        "<municipio>null</municipio>"

        "<verbas><Set></Set></verbas>"

        + historico_xml +

        "<listaDeFerias><Set></Set></listaDeFerias>"
        "<apuracoesDeJuros><Set></Set></apuracoesDeJuros>"
        "<excecoesDaCargaHoraria><Set></Set></excecoesDaCargaHoraria>"
        "<excecoesDoSabado><Set></Set></excecoesDoSabado>"
        "<faltas><Set></Set></faltas>"

        # ── fgts ──────────────────────────────────────────────────────────────
        "<fgts><Fgts>"
        f"<id>{fgts_id}</id>"
        "<versao>0</versao>"
        f"<periodoInicial>{epoch_admissao}</periodoInicial>"
        f"<periodoFinal>{epoch_demissao}</periodoFinal>"
        "<destinoDoFgts>PAGAR</destinoDoFgts>"
        "<aliquota>OITO_POR_CENTO</aliquota>"
        f"<multa>{multa_fgts}</multa>"
        "<excluirAvisoDaMulta>false</excluirAvisoDaMulta>"
        "<tipoDoValorDaMulta>CALCULADA</tipoDoValorDaMulta>"
        "<valorInformadoDaMulta>null</valorInformadoDaMulta>"
        "<multaDoFgts>QUARENTA_POR_CENTO</multaDoFgts>"
        "<incidenciaDoFgts>SOBRE_O_TOTAL_DEVIDO</incidenciaDoFgts>"
        "<multaDoArtigo467>false</multaDoArtigo467>"
        "<multa10>false</multa10>"
        "<contribuicaoSocial05>false</contribuicaoSocial05>"
        "<deduzirDoFGTS>false</deduzirDoFGTS>"
        "<incidenciaPensaoAlimenticia>false</incidenciaPensaoAlimenticia>"
        "<incidenciaPensaoAlimenticiaSobreMulta>false</incidenciaPensaoAlimenticiaSobreMulta>"
        "<indiceMulta>null</indiceMulta>"
        "<indiceMulta467>null</indiceMulta467>"
        "<taxaDeJurosParaDataDemissao>null</taxaDeJurosParaDataDemissao>"
        "<comporPrincipal>SIM</comporPrincipal>"
        f"<calculo><Calculo><internalRef>{calc_id}</internalRef></Calculo></calculo>"
        "<operacoesDeFgts><Set></Set></operacoesDeFgts>"
        "<ocorrencias><Set></Set></ocorrencias>"
        "</Fgts></fgts>"

        # ── inss ──────────────────────────────────────────────────────────────
        "<inss><Inss>"
        f"<id>{inss_id}</id>"
        "<versao>0</versao>"
        "<tipoAliquotaSegurado>SEGURADO_EMPREGADO</tipoAliquotaSegurado>"
        "<aliquotaSeguradoFixa>null</aliquotaSeguradoFixa>"
        "<limitarTeto>false</limitarTeto>"
        "<tipoAliquotaEmpregador>FIXA</tipoAliquotaEmpregador>"
        "<aliquotaEmpresaFixa>20.0000</aliquotaEmpresaFixa>"
        "<aliquotaRATFixa>3.0000</aliquotaRATFixa>"
        "<aliquotaTerceirosFixa>null</aliquotaTerceirosFixa>"
        "<apurarEmpresaPorAtividade>false</apurarEmpresaPorAtividade>"
        "<apurarRATPorAtividade>false</apurarRATPorAtividade>"
        "<apurarTerceirosPorAtividade>false</apurarTerceirosPorAtividade>"
        "<atividadeEconomica>null</atividadeEconomica>"
        "<apurarInssSobreSalariosPagos>false</apurarInssSobreSalariosPagos>"
        f"<calculo><Calculo><internalRef>{calc_id}</internalRef></Calculo></calculo>"
        "<aliquotasPorPeriodos><List></List></aliquotasPorPeriodos>"
        "<periodosComOpcaoSimples><List></List></periodosComOpcaoSimples>"
        "<inssSobreSalariosDevidos><InssSobreSalariosDevidos>"
        f"<id>{inss_id}</id>"
        "<apurarInssSegurado>true</apurarInssSegurado>"
        "<cobrarInssDoReclamante>true</cobrarInssDoReclamante>"
        "<corrigirDescontoReclamante>false</corrigirDescontoReclamante>"
        "<versao>0</versao>"
        f"<dataInicioPeriodo>{epoch_admissao}</dataInicioPeriodo>"
        f"<dataTerminoPeriodo>{epoch_demissao}</dataTerminoPeriodo>"
        "<ocorrencias><Set></Set></ocorrencias>"
        "<ocorrenciasAtualizacao><Set></Set></ocorrenciasAtualizacao>"
        f"<inss><Inss><internalRef>{inss_id}</internalRef></Inss></inss>"
        "</InssSobreSalariosDevidos></inssSobreSalariosDevidos>"
        "<inssSobreSalariosPagos><InssSobreSalariosPagos>"
        f"<id>{inss_id}</id>"
        "<versao>0</versao>"
        f"<dataInicioPeriodo>{epoch_admissao}</dataInicioPeriodo>"
        f"<dataTerminoPeriodo>{epoch_demissao}</dataTerminoPeriodo>"
        "<ocorrencias><Set></Set></ocorrencias>"
        "<ocorrenciasAtualizacao><Set></Set></ocorrenciasAtualizacao>"
        f"<inss><Inss><internalRef>{inss_id}</internalRef></Inss></inss>"
        "</InssSobreSalariosPagos></inssSobreSalariosPagos>"
        "</Inss></inss>"

        # ── previdenciaPrivada ────────────────────────────────────────────────
        "<previdenciaPrivada><PrevidenciaPrivada>"
        "<id>0</id><versao>0</versao>"
        "<apurarPrevidenciaPrivada>false</apurarPrevidenciaPrivada>"
        f"<calculo><Calculo><internalRef>{calc_id}</internalRef></Calculo></calculo>"
        "<aliquotas><Set></Set></aliquotas>"
        "<ocorrencias><Set></Set></ocorrencias>"
        "</PrevidenciaPrivada></previdenciaPrivada>"

        # ── pensaoAlimenticia ─────────────────────────────────────────────────
        "<pensaoAlimenticia><PensaoAlimenticia>"
        "<id>0</id><versao>0</versao>"
        "<apurarPensaoAlimenticia>false</apurarPensaoAlimenticia>"
        "<aliquota>null</aliquota>"
        "<incidirSobreJuros>false</incidirSobreJuros>"
        "<valorBaseVerbas>null</valorBaseVerbas>"
        "<valorBaseVerbasTributaveis>null</valorBaseVerbasTributaveis>"
        "<valorBaseFgts>null</valorBaseFgts>"
        "<valorBaseMultaDoFgts>null</valorBaseMultaDoFgts>"
        "<origemRegistro>CALCULO</origemRegistro>"
        "<dataEvento>null</dataEvento>"
        "<folhaDoEvento>null</folhaDoEvento>"
        "<percPrincipalTributavel>null</percPrincipalTributavel>"
        "<percPrincipalNaoTributavel>null</percPrincipalNaoTributavel>"
        "<incidirSobrePrincipalTributavel>true</incidirSobrePrincipalTributavel>"
        "<incidirSobrePrincipalNaoTributavel>false</incidirSobrePrincipalNaoTributavel>"
        f"<calculo><Calculo><internalRef>{calc_id}</internalRef></Calculo></calculo>"
        "</PensaoAlimenticia></pensaoAlimenticia>"

        # ── parametrosDeAtualizacao ───────────────────────────────────────────
        "<parametrosDeAtualizacao><ParametrosDeAtualizacao>"
        f"<id>{param_id}</id><versao>0</versao>"
        "<indiceTrabalhista>IPCAE</indiceTrabalhista>"
        "<outroIndiceTrabalhista>null</outroIndiceTrabalhista>"
        "<combinarOutroIndice>true</combinarOutroIndice>"
        f"<apartirDeOutroIndice>{epoch_ajuiz}</apartirDeOutroIndice>"
        "<ignorarTaxaNegativa>true</ignorarTaxaNegativa>"
        "<jurosPadrao>null</jurosPadrao>"
        "<entePublico>null</entePublico>"
        "<apertirDe>null</apertirDe>"
        "<juros>TRD_SIMPLES</juros>"
        "<aplicarJurosFasePreJudicial>true</aplicarJurosFasePreJudicial>"
        "<combinarOutroJuros>true</combinarOutroJuros>"
        "<baseDeJurosDasVerbas>VERBAS</baseDeJurosDasVerbas>"
        "<indiceDeCorrecaoDoFGTS>UTILIZAR_INDICE_TRABALHISTA</indiceDeCorrecaoDoFGTS>"
        "<jurosDeFgtsComJam>false</jurosDeFgtsComJam>"
        "<indiceDeCorrecaoDePrevidenciaPrivada>UTILIZAR_INDICE_TRABALHISTA</indiceDeCorrecaoDePrevidenciaPrivada>"
        "<outroIndiceDeCorrecaoDePrevidenciaPrivada>null</outroIndiceDeCorrecaoDePrevidenciaPrivada>"
        "<jurosDePrevidenciaPrivada>false</jurosDePrevidenciaPrivada>"
        "<indiceDeCorrecaoDasCustas>UTILIZAR_INDICE_TRABALHISTA</indiceDeCorrecaoDasCustas>"
        "<outroIndiceDeCorrecaoDasCustas>null</outroIndiceDeCorrecaoDasCustas>"
        "<jurosDeCustas>false</jurosDeCustas>"
        "<correcaoTrabalhistaDosSalariosDevidosDoINSS>true</correcaoTrabalhistaDosSalariosDevidosDoINSS>"
        "<jurosTrabalhistasDosSalariosDevidosDoINSS>false</jurosTrabalhistasDosSalariosDevidosDoINSS>"
        "<aplicarAteDosSalariosDevidosDoINSS>null</aplicarAteDosSalariosDevidosDoINSS>"
        "<correcaoPrevidenciariaDosSalariosDevidosDoINSS>false</correcaoPrevidenciariaDosSalariosDevidosDoINSS>"
        "<jurosPrevidenciariosDosSalariosDevidosDoINSS>false</jurosPrevidenciariosDosSalariosDevidosDoINSS>"
        "<aplicarMultaDosSalariosDevidosDoINSS>false</aplicarMultaDosSalariosDevidosDoINSS>"
        "<tipoDeMultaDosSalariosDevidosDoINSS>URBANA</tipoDeMultaDosSalariosDevidosDoINSS>"
        "<pagamentoDaMultaDosSalariosDevidosDoINSS>INTEGRAL</pagamentoDaMultaDosSalariosDevidosDoINSS>"
        "<salarioDevidoFormaAplicacao>null</salarioDevidoFormaAplicacao>"
        "<salarioPagoFormaAplicacao>null</salarioPagoFormaAplicacao>"
        "<correcaoTrabalhistaDosSalariosPagosDoINSS>false</correcaoTrabalhistaDosSalariosPagosDoINSS>"
        "<jurosTrabalhistasDosSalariosPagosDoINSS>false</jurosTrabalhistasDosSalariosPagosDoINSS>"
        "<aplicarAteDosSalariosPagosDoINSS>null</aplicarAteDosSalariosPagosDoINSS>"
        "<correcaoPrevidenciariaDosSalariosPagosDoINSS>false</correcaoPrevidenciariaDosSalariosPagosDoINSS>"
        "<jurosPrevidenciariosDosSalariosPagosDoINSS>false</jurosPrevidenciariosDosSalariosPagosDoINSS>"
        "<aplicarMultaDosSalariosPagosDoINSS>false</aplicarMultaDosSalariosPagosDoINSS>"
        "<tipoDeMultaDosSalariosPagosDoINSS>URBANA</tipoDeMultaDosSalariosPagosDoINSS>"
        "<pagamentoDaMultaDosSalariosPagosDoINSS>INTEGRAL</pagamentoDaMultaDosSalariosPagosDoINSS>"
        "<dataInicialDoJurosPadrao>null</dataInicialDoJurosPadrao>"
        "<dataFinalDoJurosPadrao>null</dataFinalDoJurosPadrao>"
        "<dataInicialDoJurosFazendaPublica>null</dataInicialDoJurosFazendaPublica>"
        "<dataFinalDoJurosFazendaPublica>null</dataFinalDoJurosFazendaPublica>"
        "<correcaoDasCustas>true</correcaoDasCustas>"
        "<lei11941>true</lei11941>"
        "<apartirDeLei11941>1236222000000</apartirDeLei11941>"
        "<apartirDeLei11941Multa>null</apartirDeLei11941Multa>"
        "<lei11941Pago>false</lei11941Pago>"
        "<lei11941Multa>true</lei11941Multa>"
        "<apartirDeLei11941Pago>1236222000000</apartirDeLei11941Pago>"
        "<lei11941PagoMulta>false</lei11941PagoMulta>"
        "<apartirDeLei11941PagoMulta>null</apartirDeLei11941PagoMulta>"
        "<informacaoUltimoIndice></informacaoUltimoIndice>"
        "<informacaoUltimoIndiceAtualizacao></informacaoUltimoIndiceAtualizacao>"

        # ── PATCH v5.9 — campos novos 2.14.0 (PJEKZ-88144) ───────────────────
        # Descobertos via: PJC_2.14.0_002__DDL_PJEKZ-88144_ESTRUTURA.sql
        # SFLATUALIZARREGRAPRECATORIO DEFAULT 'N' NOT NULL → obrigatório = false
        # Os demais são anuláveis mas precisam estar presentes no grafo XStream
        "<atualizarRegraPrecatorio>false</atualizarRegraPrecatorio>"
        "<esferaPrecatorio>null</esferaPrecatorio>"
        "<tipoPrecatorio>null</tipoPrecatorio>"
        "<dataInicioPeriodoGraca>null</dataInicioPeriodoGraca>"
        "<dataFimPeriodoGraca>null</dataFimPeriodoGraca>"
        # ─────────────────────────────────────────────────────────────────────

        f"<calculo><Calculo><internalRef>{calc_id}</internalRef></Calculo></calculo>"
        "<listaDeExcecaoDeJurosDaAtualizacao><Set></Set></listaDeExcecaoDeJurosDaAtualizacao>"
        "<listaDeCombinacaoDeIndices><Set>"
        f"<CombinacaoDeIndice><id>{str(int(calc_id)-4)}</id><versao>0</versao>"
        "<outroIndiceTrabalhista>SEM_CORRECAO</outroIndiceTrabalhista>"
        f"<apartirDeOutroIndice>{epoch_ajuiz}</apartirDeOutroIndice>"
        f"<parametrosDeAtualizacao><ParametrosDeAtualizacao>"
        f"<internalRef>{param_id}</internalRef>"
        f"</ParametrosDeAtualizacao></parametrosDeAtualizacao>"
        "</CombinacaoDeIndice>"
        "</Set></listaDeCombinacaoDeIndices>"
        "<listaDeCombinacaoDeJuros><Set>"
        f"<CombinacaoDeJuros><id>{comb_id}</id><versao>0</versao>"
        "<outroJuros>SELIC</outroJuros>"
        f"<apartirDeOutroJuros>{epoch_ajuiz}</apartirDeOutroJuros>"
        f"<parametrosDeAtualizacao><ParametrosDeAtualizacao>"
        f"<internalRef>{param_id}</internalRef>"
        f"</ParametrosDeAtualizacao></parametrosDeAtualizacao>"
        "</CombinacaoDeJuros>"
        "</Set></listaDeCombinacaoDeJuros>"
        "</ParametrosDeAtualizacao></parametrosDeAtualizacao>"

        # ── multas / honorarios ───────────────────────────────────────────────
        "<multas><Set></Set></multas>"
        "<honorarios><Set></Set></honorarios>"

        # ── irpf ──────────────────────────────────────────────────────────────
        "<irpf><Irpf>"
        "<id>0</id><versao>0</versao>"
        "<apurarImpostoRenda>true</apurarImpostoRenda>"
        "<incidirSobreJurosDeMora>false</incidirSobreJurosDeMora>"
        "<cobrarDoReclamado>false</cobrarDoReclamado>"
        "<considerarTributacaoExclusiva>false</considerarTributacaoExclusiva>"
        "<considerarTributacaoEmSeparado>false</considerarTributacaoEmSeparado>"
        "<regimeDeCaixa>false</regimeDeCaixa>"
        "<deduzirContribuicaoSocialDevidaPeloReclamante>true</deduzirContribuicaoSocialDevidaPeloReclamante>"
        "<deduzirPrevidenciaPrivada>true</deduzirPrevidenciaPrivada>"
        "<deduzirPensaoAlimenticia>true</deduzirPensaoAlimenticia>"
        "<deduzirHonorariosDevidosPeloReclamante>true</deduzirHonorariosDevidosPeloReclamante>"
        "<aposentadoMaiorQue65Anos>false</aposentadoMaiorQue65Anos>"
        "<possuiDependentes>false</possuiDependentes>"
        "<quantidadeDependentes>0</quantidadeDependentes>"
        f"<dataInicioAnosAnteriores>{epoch_admissao}</dataInicioAnosAnteriores>"
        f"<dataFimAnosAnteriores>{epoch_demissao}</dataFimAnosAnteriores>"
        f"<dataInicioAnoRecebimento>{epoch_hoje}</dataInicioAnoRecebimento>"
        "<dataFimAnoRecebimento>null</dataFimAnoRecebimento>"
        "<qtdMesesRendimentoTributaveis>null</qtdMesesRendimentoTributaveis>"
        f"<calculo><Calculo><internalRef>{calc_id}</internalRef></Calculo></calculo>"
        "<ocorrencias><Set></Set></ocorrencias>"
        "<ocorrenciasAtualizacao><Set></Set></ocorrenciasAtualizacao>"
        "<ocorrenciasPagamento><Set></Set></ocorrenciasPagamento>"
        "</Irpf></irpf>"

        # ── custasJudiciais ───────────────────────────────────────────────────
        "<custasJudiciais><CustasJudiciais>"
        f"<id>{calc_id}</id><versao>0</versao>"
        "<baseParaCustasCalculadas>BRUTO_DEVIDO_AO_RECLAMANTE_MAIS_DEBITOS_RECLAMADO</baseParaCustasCalculadas>"
        "<tipoDeCustasDeConhecimentoDoReclamante>NAO_SE_APLICA</tipoDeCustasDeConhecimentoDoReclamante>"
        "<dataVencimentoConhecimentoDoReclamante>null</dataVencimentoConhecimentoDoReclamante>"
        "<valorDeConhecimentoDoReclamante>null</valorDeConhecimentoDoReclamante>"
        "<tipoDeCustasDeConhecimentoDoReclamado>NAO_SE_APLICA</tipoDeCustasDeConhecimentoDoReclamado>"
        "<dataVencimentoConhecimentoDoReclamado>null</dataVencimentoConhecimentoDoReclamado>"
        "<valorConhecimentoDoReclamado>null</valorConhecimentoDoReclamado>"
        "<tipoDeCustasDeLiquidacao>NAO_SE_APLICA</tipoDeCustasDeLiquidacao>"
        "<dataVencimentoCustasDeLiquidacao>null</dataVencimentoCustasDeLiquidacao>"
        "<valorCustasDeLiquidacao>null</valorCustasDeLiquidacao>"
        "<dataVencimentoCustasFixas>null</dataVencimentoCustasFixas>"
        "<qtdeAtosUrbanos>null</qtdeAtosUrbanos>"
        "<qtdeAtosRurais>null</qtdeAtosRurais>"
        "<qtdeAgravosDeInstrumento>null</qtdeAgravosDeInstrumento>"
        "<qtdeAgravosDePeticao>null</qtdeAgravosDePeticao>"
        "<qtdeImpugnacaoSentenca>null</qtdeImpugnacaoSentenca>"
        "<qtdeEmbargosArrematacao>null</qtdeEmbargosArrematacao>"
        "<qtdeEmbargosExecucao>null</qtdeEmbargosExecucao>"
        "<qtdeEmbargosTerceiros>null</qtdeEmbargosTerceiros>"
        "<qtdeRecursoRevista>null</qtdeRecursoRevista>"
        "<valorBaseCustasCalculadas>null</valorBaseCustasCalculadas>"
        "<indiceCorrecaoCustasConhecimentoReclamante>null</indiceCorrecaoCustasConhecimentoReclamante>"
        "<taxaJurosCustasConhecimentoReclamante>null</taxaJurosCustasConhecimentoReclamante>"
        "<indiceCorrecaoCustasConhecimentoReclamado>null</indiceCorrecaoCustasConhecimentoReclamado>"
        "<taxaJurosCustasConhecimentoReclamado>null</taxaJurosCustasConhecimentoReclamado>"
        "<indiceCorrecaoCustasLiquidacao>null</indiceCorrecaoCustasLiquidacao>"
        "<taxaJurosCustasLiquidacao>null</taxaJurosCustasLiquidacao>"
        "<indiceCorrecaoCustasFixas>null</indiceCorrecaoCustasFixas>"
        "<taxaJurosCustasFixas>null</taxaJurosCustasFixas>"
        "<pisoCustasConhecimentoReclamante>null</pisoCustasConhecimentoReclamante>"
        "<pisoCustasConhecimentoReclamado>null</pisoCustasConhecimentoReclamado>"
        "<tetoCustasConhecimentoReclamante>null</tetoCustasConhecimentoReclamante>"
        "<tetoCustasConhecimentoReclamado>null</tetoCustasConhecimentoReclamado>"
        "<tetoCustasLiquidacao>null</tetoCustasLiquidacao>"
        "<valorAtosUrbanos>null</valorAtosUrbanos>"
        "<valorAtosRurais>null</valorAtosRurais>"
        "<valorAgravoInstrumento>null</valorAgravoInstrumento>"
        "<valorAgravoPeticao>null</valorAgravoPeticao>"
        "<valorImpuganacaoSentenca>null</valorImpuganacaoSentenca>"
        "<valorEmbargosArrematacao>null</valorEmbargosArrematacao>"
        "<valorEmbargosExecucao>null</valorEmbargosExecucao>"
        "<valorEmbargosTerceiros>null</valorEmbargosTerceiros>"
        "<valorRecursoRevista>null</valorRecursoRevista>"
        "<folhaDoEvento>null</folhaDoEvento>"
        "<tipoCobrancaReclamante>DESCONTAR_CREDITO</tipoCobrancaReclamante>"
        "<aplicarTetoCustasConhecimentoCalcExterno>false</aplicarTetoCustasConhecimentoCalcExterno>"
        f"<calculo><Calculo><internalRef>{calc_id}</internalRef></Calculo></calculo>"
        "<autosJudiciais><Set></Set></autosJudiciais>"
        "<custasFixasAtualizacao><Set></Set></custasFixasAtualizacao>"
        "<armazenamentos><Set></Set></armazenamentos>"
        "<custasPagasDoReclamado><Set></Set></custasPagasDoReclamado>"
        "<custasPagasDoReclamante><Set></Set></custasPagasDoReclamante>"
        "</CustasJudiciais></custasJudiciais>"

        # ── seguroDesemprego ──────────────────────────────────────────────────
        "<seguroDesemprego><SeguroDesemprego>"
        "<id>0</id><versao>0</versao>"
        "<apurarSeguroDesemprego>false</apurarSeguroDesemprego>"
        "<empregadoDomestico>false</empregadoDomestico>"
        "<tipoValorDoSeguroDesemprego>CALCULADO</tipoValorDoSeguroDesemprego>"
        "<tipoSolicitacao>null</tipoSolicitacao>"
        "<numeroDeParcelas>0</numeroDeParcelas>"
        "<tipoSalarioPago>HISTORICO_SALARIAL</tipoSalarioPago>"
        "<remuneracaoMensal>0</remuneracaoMensal>"
        "<limiteFaixa1>0</limiteFaixa1>"
        "<valorPercentualFaixa1>0</valorPercentualFaixa1>"
        "<valorPercentualFaixa2>0</valorPercentualFaixa2>"
        "<somaFaixa2>0</somaFaixa2>"
        "<valorPiso>0</valorPiso>"
        "<valorTeto>0</valorTeto>"
        "<valorSeguroDesemprego>0</valorSeguroDesemprego>"
        "<indiceDeCorrecao>0</indiceDeCorrecao>"
        "<taxaDeJuros>0</taxaDeJuros>"
        "<comporPrincipal>SIM</comporPrincipal>"
        f"<calculo><Calculo><internalRef>{calc_id}</internalRef></Calculo></calculo>"
        "<itensHistoricoSalarialDeSegudoDesemprego><Set></Set></itensHistoricoSalarialDeSegudoDesemprego>"
        "<itensSalarioDevidoDeSeguroDesemprego><Set></Set></itensSalarioDevidoDeSeguroDesemprego>"
        "</SeguroDesemprego></seguroDesemprego>"

        # ── salarioFamilia ────────────────────────────────────────────────────
        "<salarioFamilia><SalarioFamilia>"
        "<id>0</id><versao>0</versao>"
        "<apurarSalarioFamilia>false</apurarSalarioFamilia>"
        "<quantFilhosMenores14Anos>null</quantFilhosMenores14Anos>"
        "<dataInicial>null</dataInicial>"
        "<dataFinal>null</dataFinal>"
        "<tipoSalarioPago>HISTORICO_SALARIAL</tipoSalarioPago>"
        "<comporPrincipal>SIM</comporPrincipal>"
        f"<calculo><Calculo><internalRef>{calc_id}</internalRef></Calculo></calculo>"
        "<variacaoQuantidadesFilhos><List></List></variacaoQuantidadesFilhos>"
        "<itensHistoricoSalarial><Set></Set></itensHistoricoSalarial>"
        "<itensSalarioDevido><Set></Set></itensSalarioDevido>"
        "<ocorrencias><Set></Set></ocorrencias>"
        "</SalarioFamilia></salarioFamilia>"

        "<pontosFacultativos><Set></Set></pontosFacultativos>"
        "<historicosValidacao><Set></Set></historicosValidacao>"
        "<historicosValidacaoAtualizacao><Set></Set></historicosValidacaoAtualizacao>"
        "<cartoesDePonto><Set></Set></cartoesDePonto>"
        "<pagamentos><Set></Set></pagamentos>"
        "<apuracoesCartaoDePonto><Set></Set></apuracoesCartaoDePonto>"
        "<apuracoesDiariasCartaoDePonto><Set></Set></apuracoesDiariasCartaoDePonto>"
        "<excecoesDoFechamentoDeCartaoDePonto><Set></Set></excecoesDoFechamentoDeCartaoDePonto>"
        "</Calculo>"
    )

    return xml.encode("iso-8859-1", errors="xmlcharrefreplace")


# ── API pública ───────────────────────────────────────────────────────────────

def exportar_pjc(dados: dict) -> bytes:
    """
    Recebe o dict de campos extraídos pelo pipeline.
    Retorna bytes do .pjc como XML puro ISO-8859-1 (SEM ZIP).
    """
    numero = dados.get("numero_processo", "N/A")
    print(f"[PJC] Exportação v5.9 | Processo: {numero}")

    pjc_bytes = _build_xml(dados)

    print(f"[PJC] ✓ XML gerado | {len(pjc_bytes):,} bytes | encoding: ISO-8859-1")
    return pjc_bytes


def gerar_nome_arquivo(dados: dict) -> str:
    """Gera nome do arquivo .pjc no padrão do PJeCalc."""
    numero = re.sub(r"[^0-9]", "", dados.get("numero_processo") or "PROCESSO")
    hoje   = datetime.now().strftime("%d%m%Y")
    return f"PROCESSO_{numero}_SMART_EXTRACTOR_{hoje}.pjc"