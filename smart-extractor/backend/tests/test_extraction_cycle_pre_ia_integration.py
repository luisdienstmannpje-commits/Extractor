"""
Ciclo de integração mínima: saída de pre_extract → âncoras MEDIUM em extract_data_with_gemini.

Contrato (este ciclo):
  - pre_fields = pre_extract(texto) com forma {"high": dict, "medium": dict}.
  - extract_data_with_gemini(..., pre_fields=pre_fields) monta anchor_section via
    build_anchor_section(pre_fields["medium"]) e repassa a _call_model.
  - processor (PDF único e dossiê) chama pre_extract antes da IA e repassa pre_fields.
"""

from __future__ import annotations

import services.ai_client as ai_client
from services.pre_extractor import pre_extract


def _stub_ia_payload() -> dict:
    """Resposta mínima para não acionar API real; não passa por _validate_result aqui."""
    return {"numero_processo": None, "reclamante": None, "reclamada": None}


def test_medium_do_pre_extract_aparece_em_anchor_do_gemini(monkeypatch):
    texto_pre = "O reclamante percebia salário de R$ 2.345,67 mensais."
    pre_fields = pre_extract(texto_pre)
    assert pre_fields.get("medium", {}).get("salario_base")

    captured: dict[str, str] = {}

    def stub_call_model(
        model_name: str,
        text: str,
        playbook: str = "",
        anchor_section: str = "",
        retries: int = 2,
        pipeline_debug_meta=None,
    ):
        captured["anchor_section"] = anchor_section
        return _stub_ia_payload()

    monkeypatch.setattr(ai_client, "_call_model", stub_call_model)

    out = ai_client.extract_data_with_gemini(
        text="corpo mínimo para truncagem",
        playbook="",
        pre_fields=pre_fields,
    )

    assert out["error"] is None
    assert out["data"] == _stub_ia_payload()
    anchor = captured.get("anchor_section", "")
    assert "Salário base" in anchor
    assert "R$ 2.345,67" in anchor
