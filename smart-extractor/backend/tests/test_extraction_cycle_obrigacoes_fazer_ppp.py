"""
Ciclo TDD: obrigacoes_fazer tipo PPP.
Perfil Profissiográfico Previdenciário — obrigação de entrega/retificação com suporte
a prazo_dias, multa_diaria e multa_limite (mesmo contrato dos demais tipos).
"""
from services.pre_extractor import pre_extract


def test_ppp_entrega_basica():
    texto = "Determino a entrega do PPP ao reclamante no prazo de 10 dias."
    result = pre_extract(texto)
    obrigacoes = result["medium"]["obrigacoes_fazer"]
    assert any(o["tipo"] == "PPP" for o in obrigacoes)
    item = next(o for o in obrigacoes if o["tipo"] == "PPP")
    assert "PPP" in item["descricao"]
    assert item["prazo_dias"] == "10 dias"


def test_ppp_fornecer():
    texto = "Condeno a reclamada a fornecer o PPP ao reclamante."
    result = pre_extract(texto)
    obrigacoes = result["medium"].get("obrigacoes_fazer", [])
    assert any(o["tipo"] == "PPP" for o in obrigacoes)


def test_ppp_agente_nocivo_na_descricao():
    texto = "Determino a entrega do PPP com agente nocivo ruido ao reclamante."
    result = pre_extract(texto)
    obrigacoes = result["medium"]["obrigacoes_fazer"]
    item = next(o for o in obrigacoes if o["tipo"] == "PPP")
    assert "agente" in item["descricao"].lower() or "nocivo" in item["descricao"].lower() or "ruido" in item["descricao"].lower()


def test_ppp_com_multa_diaria():
    texto = (
        "Determino a entrega do PPP ao reclamante no prazo de 5 dias, "
        "sob pena de multa diaria de R$ 100,00."
    )
    result = pre_extract(texto)
    obrigacoes = result["medium"]["obrigacoes_fazer"]
    item = next(o for o in obrigacoes if o["tipo"] == "PPP")
    assert item["prazo_dias"] == "5 dias"
    assert item["multa_diaria"] == "R$ 100,00"


def test_ppp_com_multa_diaria_e_limite():
    texto = (
        "Condeno a reclamada a fornecer o PPP, "
        "sob pena de astreintes de R$ 200,00 por dia, limitada a R$ 6.000,00."
    )
    result = pre_extract(texto)
    obrigacoes = result["medium"]["obrigacoes_fazer"]
    item = next(o for o in obrigacoes if o["tipo"] == "PPP")
    assert item["multa_diaria"] == "R$ 200,00"
    assert item["multa_limite"] == "R$ 6.000,00"


def test_ppp_retificacao():
    texto = "Determino a retificacao do PPP para incluir o agente nocivo quimico."
    result = pre_extract(texto)
    obrigacoes = result["medium"].get("obrigacoes_fazer", [])
    item = next((o for o in obrigacoes if o["tipo"] == "PPP"), None)
    assert item is not None
    assert "PPP" in item["descricao"]


def test_ppp_nao_extrai_sem_contexto_de_obrigacao():
    """Menção isolada a PPP no relatório não deve gerar obrigação de fazer."""
    texto = "O reclamante alega que o PPP nao foi entregue na rescisao."
    result = pre_extract(texto)
    obrigacoes = result["medium"].get("obrigacoes_fazer", [])
    assert not any(o["tipo"] == "PPP" for o in obrigacoes)
