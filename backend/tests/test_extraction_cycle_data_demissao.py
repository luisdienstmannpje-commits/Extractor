"""
Ciclo TDD — data_demissao
Gaps identificados no probe:
  GAP 1: "demissão: DD/MM/AAAA" — label com dois-pontos (sem "em")
  GAP 2: "dispensada da empresa em" — frase entre trigger e "em"
  GAP 3: "Em DD/MM/AAAA, foi dispensado" — data invertida no início
  GAP 4: "encerrou o vínculo em" — trigger ausente
"""
import pytest
from services.pre_extractor import PreExtractor


def _run(text: str) -> str | None:
    result = PreExtractor(text).run()
    return result["high"].get("data_demissao") or result["medium"].get("data_demissao")


# ── Casos já cobertos (regressão) ───────────────────────────────────────────

class TestDataDemissaoRegressao:
    def test_dispensado_em(self):
        assert _run("foi dispensado em 10/05/2023 sem justa causa") == "10/05/2023"

    def test_demitido_em(self):
        assert _run("o reclamante foi demitido em 22/11/2022") == "22/11/2022"

    def test_rescisao_contratual_em(self):
        assert _run("ocorreu a rescisão contratual em 01/03/2021") == "01/03/2021"

    def test_data_de_demissao_label(self):
        assert _run("data de demissão: 15/07/2024") == "15/07/2024"

    def test_data_da_rescisao_label(self):
        assert _run("data da rescisão: 28/02/2023") == "28/02/2023"

    def test_desligado_em(self):
        assert _run("foi desligado em 05/09/2023 da empresa") == "05/09/2023"

    def test_termino_contrato_em(self):
        assert _run("término do contrato em 31/12/2023") == "31/12/2023"

    def test_extenso_dispensado(self):
        # _data_extenso_para_slash converte para DD/MM/AAAA
        assert _run("foi dispensado em 10 de março de 2022") == "10/03/2022"

    def test_extenso_demitido(self):
        assert _run("foi demitido em 05 de junho de 2021") == "05/06/2021"


# ── GAP 1: label com dois-pontos ────────────────────────────────────────────

class TestDataDemissaoGap1LabelColon:
    def test_demissao_colon_data(self):
        """demissão: DD/MM/AAAA — sem a palavra 'em'"""
        assert _run("demissão: 30/06/2023") == "30/06/2023"

    def test_demissao_hifen_data(self):
        """demissão - DD/MM/AAAA — com hífen"""
        assert _run("demissão - 30/06/2023") == "30/06/2023"

    def test_rescisao_colon_data(self):
        """rescisão: DD/MM/AAAA"""
        assert _run("rescisão: 15/08/2022") == "15/08/2022"

    def test_desligamento_colon_data(self):
        """desligamento: DD/MM/AAAA"""
        assert _run("desligamento: 01/01/2024") == "01/01/2024"


# ── GAP 2: frase entre trigger e "em" ───────────────────────────────────────

class TestDataDemissaoGap2FraseTrigger:
    def test_dispensada_da_empresa_em(self):
        """dispensada da empresa em DD/MM/AAAA"""
        assert _run("foi dispensada da empresa em 15/01/2025") == "15/01/2025"

    def test_dispensado_do_emprego_em(self):
        """dispensado do emprego em DD/MM/AAAA"""
        assert _run("foi dispensado do emprego em 20/04/2023") == "20/04/2023"

    def test_demitido_da_empresa_em(self):
        """demitido da empresa em DD/MM/AAAA"""
        assert _run("foi demitido da empresa em 07/07/2022") == "07/07/2022"

    def test_desligado_da_reclamada_em(self):
        """desligado da reclamada em DD/MM/AAAA"""
        assert _run("foi desligado da reclamada em 10/10/2023") == "10/10/2023"


# ── GAP 3: data invertida no início ─────────────────────────────────────────

class TestDataDemissaoGap3DataInvertida:
    def test_em_data_foi_dispensado(self):
        """Em DD/MM/AAAA, foi dispensado sem justa causa"""
        assert _run("Em 15/01/2025, foi dispensado sem justa causa") == "15/01/2025"

    def test_em_data_foi_demitido(self):
        """Em DD/MM/AAAA, o reclamante foi demitido"""
        assert _run("Em 22/03/2023, o reclamante foi demitido") == "22/03/2023"

    def test_em_data_rescisao(self):
        """Em DD/MM/AAAA ocorreu a rescisão"""
        assert _run("Em 01/06/2022 ocorreu a rescisão do contrato") == "01/06/2022"


# ── GAP 4: trigger ausente / novo trigger ───────────────────────────────────

class TestDataDemissaoGap4NovoTrigger:
    def test_encerrou_vinculo_em(self):
        """encerrou o vínculo em DD/MM/AAAA"""
        assert _run("encerrou o vínculo em 10/03/2022") == "10/03/2022"

    def test_rompeu_vinculo_em(self):
        """rompeu o vínculo empregatício em DD/MM/AAAA"""
        assert _run("rompeu o vínculo empregatício em 05/05/2023") == "05/05/2023"

    def test_extincao_contrato_em(self):
        """extinção do contrato em DD/MM/AAAA"""
        assert _run("extinção do contrato em 20/12/2023") == "20/12/2023"

    def test_dispensado_sem_justa_causa_em(self):
        """dispensado sem justa causa em DD/MM/AAAA"""
        assert _run("foi dispensado sem justa causa em 30/09/2024") == "30/09/2024"


# ── GAP 5: término do vínculo / data de saída ───────────────────────────────

class TestDataDemissaoGap5NovosTriggers:
    def test_termino_vinculo_em(self):
        """'término do vínculo em' — não coberto (só 'término do contrato em')."""
        assert _run("término do vínculo em 15/03/2023") == "15/03/2023"

    def test_termino_vinculo_empregatorio_em(self):
        assert _run("término do vínculo empregatício em 30/06/2023") == "30/06/2023"

    def test_data_saida_label(self):
        """'data de saída: DD/MM/AAAA' — label de saída."""
        assert _run("data de saída: 30/06/2023") == "30/06/2023"

    def test_data_saida_sem_acento(self):
        assert _run("data de saida: 01/07/2022") == "01/07/2022"
