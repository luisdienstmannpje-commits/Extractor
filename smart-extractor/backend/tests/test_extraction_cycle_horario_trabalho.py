"""
Ciclo TDD: horario_trabalho (pre_extractor MEDIUM).

Horario de entrada, saida e intervalo reconhecido pelo juiz.
Formatos esperados normalizados:
  "07h as 17h com 1h de intervalo"
  "08h as 18h com 1h de intervalo"
  "07h as 17h sem intervalo"
  "07h30 as 17h30 com 1h de intervalo"
"""
from services.pre_extractor import pre_extract


# ── Horario com intervalo ─────────────────────────────────────────────────────

def test_horario_das_07_as_17_1h_intervalo():
    texto = "Reconheco a jornada das 07h as 17h, com 1 hora de intervalo intrajornada."
    result = pre_extract(texto)
    val = result["medium"].get("horario_trabalho", "")
    assert "07h" in val and "17h" in val and "1h" in val


def test_horario_das_08_as_18():
    texto = "O reclamante laborava das 08:00 as 18:00 horas, com 1h de almoco."
    result = pre_extract(texto)
    val = result["medium"].get("horario_trabalho", "")
    assert "08h" in val and "18h" in val


def test_horario_das_07_as_17h30():
    texto = "Fixo a jornada das 07h30 as 17h30 com intervalo de 1 hora."
    result = pre_extract(texto)
    val = result["medium"].get("horario_trabalho", "")
    assert "07h30" in val and "17h30" in val


def test_horario_entrada_saida_intervalo_texto():
    texto = "Entrada as 6h, saida as 14h, intervalo de 30 minutos."
    result = pre_extract(texto)
    val = result["medium"].get("horario_trabalho", "")
    assert "6h" in val or "06h" in val
    assert "14h" in val


# ── Horario sem intervalo ─────────────────────────────────────────────────────

def test_horario_sem_intervalo():
    texto = "Jornada das 08h as 14h, sem intervalo, conforme escala 12x36."
    result = pre_extract(texto)
    val = result["medium"].get("horario_trabalho", "")
    assert "08h" in val and "14h" in val


# ── Normalizacao: dois-pontos vira h ─────────────────────────────────────────

def test_horario_formato_colon_normalizado():
    texto = "O obreiro trabalhava de 09:00 as 18:00 com 1h de intervalo."
    result = pre_extract(texto)
    val = result["medium"].get("horario_trabalho", "")
    assert "09h" in val and "18h" in val


def test_horario_formato_colon_com_minutos():
    texto = "Jornada reconhecida: 07:30 as 17:30, com 1 hora de almoco."
    result = pre_extract(texto)
    val = result["medium"].get("horario_trabalho", "")
    assert "07h30" in val and "17h30" in val


# ── Nao extrai sem mencao ─────────────────────────────────────────────────────

def test_horario_nao_extrai_sem_mencao():
    texto = "Condeno a reclamada ao pagamento de aviso previo e ferias proporcionais."
    result = pre_extract(texto)
    assert "horario_trabalho" not in result["medium"]


# ── Nao confunde com datas ────────────────────────────────────────────────────

def test_horario_nao_confunde_com_data():
    """Datas como 01/03/2022 nao devem preencher horario_trabalho."""
    texto = "O contrato iniciou em 01/03/2022 e encerrou em 15/08/2023."
    result = pre_extract(texto)
    assert "horario_trabalho" not in result["medium"]


# ── anchor section ────────────────────────────────────────────────────────────

def test_horario_anchor_section_renderiza():
    from services.pre_extractor import build_anchor_section
    texto = "Reconheco a jornada das 07h as 17h com 1h de intervalo."
    result = pre_extract(texto)
    anchor = build_anchor_section(result["medium"])
    assert "horario" in anchor.lower() or "07h" in anchor or "jornada" in anchor.lower()
