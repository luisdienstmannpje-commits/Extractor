"""
Ciclo pós-integração: merge de pre_fields['high'] sobre dados_limpos após _validate_result.

Contrato (este ciclo):
  - Só chaves em whitelist alinhadas ao PreExtractor HIGH entram no merge.
  - Sobrescrita: valor HIGH definido substitui o que vier da IA para a mesma chave.
  - None ou string só espaços no HIGH → não aplica (mantém o valor já em dados_limpos).
  - justica_gratuita: bool preservado (True e False).
  - Chaves HIGH não presentes em pre_fields não alteram dados_limpos.
"""

from workers.processor import _aplicar_pre_high


def test_numero_processo_high_substitui_valor_ia():
    dados = {"numero_processo": "0000000-00.0000.0.00.0000", "reclamante": "Fulano"}
    pre_high = {"numero_processo": "1234567-89.2023.5.03.0068"}

    out = _aplicar_pre_high(dados, pre_high)

    assert out["numero_processo"] == "1234567-89.2023.5.03.0068"
    assert out["reclamante"] == "Fulano"


def test_chave_high_ausente_preserva_ia():
    dados = {"numero_processo": "X", "reclamante": "IA nome"}
    pre_high = {"vara_trabalho": "3ª Vara do Trabalho de São Paulo"}

    out = _aplicar_pre_high(dados, pre_high)

    assert out["numero_processo"] == "X"
    assert out["reclamante"] == "IA nome"
    assert out["vara_trabalho"] == "3ª Vara do Trabalho de São Paulo"


def test_justica_gratuita_false_substitui_true_ia():
    dados = {"justica_gratuita": True}
    pre_high = {"justica_gratuita": False}

    out = _aplicar_pre_high(dados, pre_high)

    assert out["justica_gratuita"] is False


def test_string_vazia_high_nao_apaga_campo():
    dados = {"numero_processo": "valor IA"}
    pre_high = {"numero_processo": "   "}

    out = _aplicar_pre_high(dados, pre_high)

    assert out["numero_processo"] == "valor IA"


def test_pre_high_none_e_dict_vazio():
    dados = {"numero_processo": "X"}

    assert _aplicar_pre_high(dict(dados), None) == dados
    assert _aplicar_pre_high(dict(dados), {}) == dados


def test_chave_estranha_em_pre_high_ignorada():
    dados = {"numero_processo": "Y"}
    pre_high = {"numero_processo": "Z", "campo_inventado": "hack"}

    out = _aplicar_pre_high(dados, pre_high)

    assert out["numero_processo"] == "Z"
    assert "campo_inventado" not in out
