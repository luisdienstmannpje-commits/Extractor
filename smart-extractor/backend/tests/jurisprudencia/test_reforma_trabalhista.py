"""
test_reforma_trabalhista.py -- Testes unitarios das regras da Reforma Trabalhista

Cobre:
  - art_58_itinere.py  (Art. 58 par. 2o CLT -- horas in itinere)
  - art_477a.py        (Art. 477-A CLT -- homologacao sindical)
  - art_223g.py        (Art. 223-G CLT -- tarifacao dano extrapatrimonial)

Executar:
    cd backend
    pytest tests/jurisprudencia/test_reforma_trabalhista.py -v
"""

import pytest
from datetime import date


def _make_contexto(**kwargs):
    from services.legal_engine.rule_base import ContextoJuridico, VerbaContexto
    defaults = {
        "numero_processo":  "0099999-99.2025.5.03.0167",
        "reclamante":       "Reclamante Teste",
        "reclamada":        "Reclamada Teste LTDA",
        "data_admissao":    "01/01/2022",
        "data_demissao":    "01/06/2025",
        "data_sentenca":    "01/11/2025",
        "data_ajuizamento": "15/07/2025",
        "salario_base":     "R$ 3.200,00",
        "verbas_deferidas": [],
    }
    defaults.update(kwargs)
    verbas_raw = defaults.pop("verbas_deferidas", [])
    verbas = []
    for v in verbas_raw:
        if isinstance(v, dict):
            verbas.append(VerbaContexto(**v))
        else:
            verbas.append(v)
    defaults["verbas_deferidas"] = verbas
    return ContextoJuridico(**defaults)


def _alertas(contexto):
    return [f"[{a['nivel']}] {a['mensagem']}" for a in contexto.alertas]


def _parse_data(s):
    from datetime import datetime
    if not s:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


# ===========================================================================
# Art. 58 par. 2o CLT -- Horas In Itinere
# ===========================================================================

class TestArt58Itinere:

    @pytest.fixture
    def regra(self):
        from services.jurisprudencia.clt.art_58_itinere import Art58ItinereReforma
        return Art58ItinereReforma()

    def test_is_aplicavel__pre_reforma_nao_aplica(self, regra):
        assert regra.is_aplicavel(_parse_data("01/01/2015")) is False

    def test_is_aplicavel__dia_anterior_nao_aplica(self, regra):
        assert regra.is_aplicavel(_parse_data("10/11/2017")) is False

    def test_is_aplicavel__dia_exato_aplica(self, regra):
        assert regra.is_aplicavel(_parse_data("11/11/2017")) is True

    def test_is_aplicavel__pos_reforma_aplica(self, regra):
        assert regra.is_aplicavel(_parse_data("01/03/2020")) is True

    def test_is_aplicavel__none_aplica(self, regra):
        assert regra.is_aplicavel(None) is True

    def test_sem_verba_itinere__silencio(self, regra):
        ctx = _make_contexto(verbas_deferidas=[
            {"nome": "Horas Extras", "status_final": "deferida", "reflexos": []},
            {"nome": "Aviso Previo", "status_final": "deferida", "reflexos": []},
        ])
        assert regra.aplicar(ctx).alertas == []

    def test_sem_verbas__silencio(self, regra):
        assert regra.aplicar(_make_contexto(verbas_deferidas=[])).alertas == []

    def test_itinere_deferida__erro(self, regra):
        ctx = _make_contexto(verbas_deferidas=[
            {"nome": "Horas in itinere", "status_final": "deferida", "reflexos": []},
        ])
        assert any("[ERRO]" in a for a in _alertas(regra.aplicar(ctx)))

    def test_itinere_deslocamento__erro(self, regra):
        ctx = _make_contexto(verbas_deferidas=[
            {"nome": "Horas de deslocamento", "status_final": "deferida", "reflexos": []},
        ])
        assert any("[ERRO]" in a for a in _alertas(regra.aplicar(ctx)))

    def test_percurso_casa_trabalho__erro(self, regra):
        ctx = _make_contexto(verbas_deferidas=[
            {"nome": "Percurso casa trabalho", "status_final": "deferida", "reflexos": []},
        ])
        assert any("[ERRO]" in a for a in _alertas(regra.aplicar(ctx)))

    def test_itinere_indeferida__silencio(self, regra):
        ctx = _make_contexto(verbas_deferidas=[
            {"nome": "Horas in itinere", "status_final": "indeferida", "reflexos": []},
        ])
        assert regra.aplicar(ctx).alertas == []

    def test_pre_reforma__itinere_sem_alerta(self, regra):
        assert regra.is_aplicavel(_parse_data("01/01/2015")) is False

    def test_regra_registrada_apos_aplicar(self, regra):
        ctx = _make_contexto(verbas_deferidas=[
            {"nome": "Horas in itinere", "status_final": "deferida", "reflexos": []},
        ])
        assert "ART_58_ITINERE_REFORMA" in regra.aplicar(ctx).regras_aplicadas

    def test_data_ref_campo(self, regra):
        assert regra.data_ref_campo == "data_admissao"


# ===========================================================================
# Art. 477-A CLT -- Homologacao Sindical
# ===========================================================================

class TestArt477AHomologacao:

    @pytest.fixture
    def regra(self):
        from services.jurisprudencia.clt.art_477a import Art477AHomologacao
        return Art477AHomologacao()

    def test_is_aplicavel__pre_reforma_nao_aplica(self, regra):
        assert regra.is_aplicavel(_parse_data("01/01/2015")) is False

    def test_is_aplicavel__pos_reforma_aplica(self, regra):
        assert regra.is_aplicavel(_parse_data("01/01/2020")) is True

    def test_is_aplicavel__none_aplica(self, regra):
        assert regra.is_aplicavel(None) is True

    def test_sem_homologacao__silencio(self, regra):
        assert regra.aplicar(_make_contexto(motivo_rescisao="Sem justa causa")).alertas == []

    def test_campos_vazios__silencio(self, regra):
        ctx = _make_contexto(motivo_rescisao=None, fgts_observacoes=None)
        assert regra.aplicar(ctx).alertas == []

    def test_homologacao_obrigatoria__aviso(self, regra):
        ctx = _make_contexto(motivo_rescisao="homologacao sindical e obrigatoria para rescisao")
        assert any("[AVISO]" in a for a in _alertas(regra.aplicar(ctx)))

    def test_homologacao_exigida__aviso(self, regra):
        ctx = _make_contexto(motivo_rescisao="homologacao sindical exigida para validade do ato")
        assert any("[AVISO]" in a for a in _alertas(regra.aplicar(ctx)))

    def test_rescisao_condicionada__aviso(self, regra):
        ctx = _make_contexto(fgts_observacoes="rescisao condicionada a homologacao sindical")
        assert any("[AVISO]" in a for a in _alertas(regra.aplicar(ctx)))

    def test_validade_depende_homologacao__aviso(self, regra):
        ctx = _make_contexto(fgts_observacoes="validade da rescisao depende de homologacao")
        assert any("[AVISO]" in a for a in _alertas(regra.aplicar(ctx)))

    def test_nulidade_falta_homologacao__aviso(self, regra):
        ctx = _make_contexto(motivo_rescisao="nulidade da rescisao por falta de homologacao")
        assert any("[AVISO]" in a for a in _alertas(regra.aplicar(ctx)))

    def test_homologacao_voluntaria__silencio(self, regra):
        ctx = _make_contexto(motivo_rescisao="rescisao homologada perante o sindicato")
        assert regra.aplicar(ctx).alertas == []

    def test_termo_homologado__silencio(self, regra):
        ctx = _make_contexto(fgts_observacoes="termo de rescisao homologado")
        assert regra.aplicar(ctx).alertas == []

    def test_data_ref_campo(self, regra):
        assert regra.data_ref_campo == "data_admissao"

    def test_regra_registrada(self, regra):
        ctx = _make_contexto(motivo_rescisao="homologacao sindical necessaria")
        assert "ART_477A_HOMOLOGACAO" in regra.aplicar(ctx).regras_aplicadas


# ===========================================================================
# Art. 223-G CLT -- Tarifacao de Dano Extrapatrimonial
# ===========================================================================

class TestArt223GDanoExtrapatrimonial:

    @pytest.fixture
    def regra(self):
        from services.jurisprudencia.clt.art_223g import Art223GDanoExtrapatrimonial
        return Art223GDanoExtrapatrimonial()

    def test_is_aplicavel__pre_reforma_nao_aplica(self, regra):
        assert regra.is_aplicavel(_parse_data("01/01/2015")) is False

    def test_is_aplicavel__pos_reforma_aplica(self, regra):
        assert regra.is_aplicavel(_parse_data("01/01/2020")) is True

    def test_sem_dano_moral__silencio(self, regra):
        ctx = _make_contexto(verbas_deferidas=[
            {"nome": "Horas Extras", "status_final": "deferida", "reflexos": []},
        ])
        assert regra.aplicar(ctx).alertas == []

    def test_verbas_vazias__silencio(self, regra):
        assert regra.aplicar(_make_contexto(verbas_deferidas=[])).alertas == []

    def test_dano_moral_sem_valor__info(self, regra):
        ctx = _make_contexto(verbas_deferidas=[
            {"nome": "Dano Moral", "status_final": "deferida",
             "valor_fixado": "valor a definir em liquidacao", "reflexos": []},
        ])
        assert any("[INFO]" in a for a in _alertas(regra.aplicar(ctx)))

    def test_danos_morais__info(self, regra):
        ctx = _make_contexto(verbas_deferidas=[
            {"nome": "Danos Morais", "status_final": "deferida",
             "valor_fixado": None, "reflexos": []},
        ])
        assert any("[INFO]" in a for a in _alertas(regra.aplicar(ctx)))

    def test_dano_extrapatrimonial__info(self, regra):
        ctx = _make_contexto(verbas_deferidas=[
            {"nome": "Dano Extrapatrimonial", "status_final": "deferida",
             "valor_fixado": None, "reflexos": []},
        ])
        assert any("[INFO]" in a for a in _alertas(regra.aplicar(ctx)))

    def test_faixa_leve__info(self, regra):
        ctx = _make_contexto(salario_base="R$ 3.200,00", verbas_deferidas=[
            {"nome": "Dano Moral", "status_final": "deferida",
             "valor_fixado": "R$ 9.600,00", "reflexos": []},
        ])
        alertas = _alertas(regra.aplicar(ctx))
        assert any("[INFO]" in a for a in alertas)
        assert not any("[AVISO]" in a for a in alertas)

    def test_faixa_medio__info(self, regra):
        ctx = _make_contexto(salario_base="R$ 3.200,00", verbas_deferidas=[
            {"nome": "Dano Moral", "status_final": "deferida",
             "valor_fixado": "R$ 16.000,00", "reflexos": []},
        ])
        alertas = _alertas(regra.aplicar(ctx))
        assert any("[INFO]" in a for a in alertas)
        assert not any("[AVISO]" in a for a in alertas)

    def test_faixa_grave__info(self, regra):
        ctx = _make_contexto(salario_base="R$ 3.200,00", verbas_deferidas=[
            {"nome": "Dano Moral", "status_final": "deferida",
             "valor_fixado": "R$ 64.000,00", "reflexos": []},
        ])
        alertas = _alertas(regra.aplicar(ctx))
        assert any("[INFO]" in a for a in alertas)
        assert not any("[AVISO]" in a for a in alertas)

    def test_faixa_gravissimo__info(self, regra):
        ctx = _make_contexto(salario_base="R$ 3.200,00", verbas_deferidas=[
            {"nome": "Dano Moral", "status_final": "deferida",
             "valor_fixado": "R$ 160.000,00", "reflexos": []},
        ])
        alertas = _alertas(regra.aplicar(ctx))
        assert any("[INFO]" in a for a in alertas)
        assert not any("[AVISO]" in a for a in alertas)

    def test_acima_gravissimo__aviso(self, regra):
        ctx = _make_contexto(salario_base="R$ 3.200,00", verbas_deferidas=[
            {"nome": "Dano Moral", "status_final": "deferida",
             "valor_fixado": "R$ 200.000,00", "reflexos": []},
        ])
        assert any("[AVISO]" in a for a in _alertas(regra.aplicar(ctx)))

    def test_dano_moral_indeferido__silencio(self, regra):
        ctx = _make_contexto(verbas_deferidas=[
            {"nome": "Dano Moral", "status_final": "indeferida",
             "valor_fixado": "R$ 200.000,00", "reflexos": []},
        ])
        assert regra.aplicar(ctx).alertas == []

    def test_salario_nao_parseavel__info_sem_multiplo(self, regra):
        ctx = _make_contexto(salario_base="a combinar", verbas_deferidas=[
            {"nome": "Dano Moral", "status_final": "deferida",
             "valor_fixado": "R$ 50.000,00", "reflexos": []},
        ])
        assert any("[INFO]" in a for a in _alertas(regra.aplicar(ctx)))

    def test_data_ref_campo(self, regra):
        assert regra.data_ref_campo == "data_admissao"

    def test_vigencia_inicio(self, regra):
        assert regra.vigencia_inicio == date(2017, 11, 11)

    def test_regra_registrada(self, regra):
        ctx = _make_contexto(verbas_deferidas=[
            {"nome": "Dano Moral", "status_final": "deferida",
             "valor_fixado": None, "reflexos": []},
        ])
        assert "ART_223G_DANO_EXTRAPATRIMONIAL" in regra.aplicar(ctx).regras_aplicadas

    def test_mensagem_contem_nota_stf(self, regra):
        ctx = _make_contexto(verbas_deferidas=[
            {"nome": "Dano Moral", "status_final": "deferida",
             "valor_fixado": "R$ 50.000,00", "reflexos": []},
        ])
        resultado = regra.aplicar(ctx)
        alertas = _alertas(resultado)
        assert alertas
        assert any("ADI" in a or "STF" in a or "parametro" in a.lower() for a in alertas)
