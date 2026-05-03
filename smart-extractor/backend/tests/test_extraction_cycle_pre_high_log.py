"""
Ciclo observabilidade: log quando _aplicar_pre_high altera valor em relação ao estado anterior.

Contrato:
  - Uma linha stdout se pelo menos um campo whitelist mudar de fato (valor anterior ≠ valor novo).
  - Prefixo fixo [PRE-HIGH]; lista nomes de campos alterados (ordem de iteração do pre_high).
  - Sem linha [PRE-HIGH] se pre_high ausente/vazio, ou se nenhum campo aplicável muda o valor.
"""

from workers.processor import _aplicar_pre_high


def test_emite_log_quando_numero_processo_muda(capsys):
    dados = {"numero_processo": "0000000-00.0000.0.00.0000"}
    pre_high = {"numero_processo": "1234567-89.2023.5.03.0068"}

    _aplicar_pre_high(dados, pre_high)

    out = capsys.readouterr().out
    assert "[PRE-HIGH]" in out
    assert "numero_processo" in out


def test_nao_emite_log_quando_valor_final_igual(capsys):
    dados = {"numero_processo": "MESMO-CNJ"}
    pre_high = {"numero_processo": "MESMO-CNJ"}

    _aplicar_pre_high(dados, pre_high)

    assert "[PRE-HIGH]" not in capsys.readouterr().out


def test_nao_emite_log_sem_pre_high(capsys):
    dados = {"numero_processo": "X"}

    _aplicar_pre_high(dados, None)

    assert "[PRE-HIGH]" not in capsys.readouterr().out


def test_emite_um_log_para_varios_campos_alterados(capsys):
    dados = {
        "numero_processo": "A",
        "reclamante": "IA",
    }
    pre_high = {
        "numero_processo": "1234567-89.2023.5.03.0068",
        "reclamante": "Regex Nome",
    }

    _aplicar_pre_high(dados, pre_high)

    out = capsys.readouterr().out
    assert out.count("[PRE-HIGH]") == 1
    assert "numero_processo" in out
    assert "reclamante" in out
