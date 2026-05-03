"""Helpers do endpoint de manifestação no Lab."""

from api.routers.lab import _dados_processo_para_ghostwriter


def test_dados_processo_para_ghostwriter_maps_sentenca_and_alerts():
    rel = {
        "numero_processo": "0001",
        "sentenca": {
            "campos_chave": {
                "reclamante": "A",
                "reclamada": "B",
                "vara_trabalho": "1 VT",
                "indice_correcao": "SELIC",
                "juros_mora": "1%",
            },
            "verbas": ["Horas extras"],
        },
        "alertas_juridicos": ["[AVISO] x"],
        "quadro_comparativo": [{"verba_alvo": "HE"}],
    }
    d = _dados_processo_para_ghostwriter(rel)
    assert d["numero_processo"] == "0001"
    assert d["reclamante"] == "A"
    assert d["reclamada"] == "B"
    assert d["verbas_deferidas"][0]["nome"] == "Horas extras"
    assert d["alertas_juridicos"] == ["[AVISO] x"]
    assert d["quadro_comparativo"][0]["verba_alvo"] == "HE"
