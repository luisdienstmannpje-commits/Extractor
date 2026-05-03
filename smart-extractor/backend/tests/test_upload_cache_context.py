"""Regras de roteamento POST /upload: single PDF vs dossiê vs petição inicial."""

from api.routers.extractor import _should_run_process_lawsuit_pdf_upload


def _collected(*names: str) -> list[tuple[str, bytes]]:
    return [(n, b"x" * 20) for n in names]


def test_auto_single_pdf_usa_process_lawsuit_pdf():
    ok, err = _should_run_process_lawsuit_pdf_upload(
        _collected("sent.pdf"), "auto"
    )
    assert ok is True and err is None


def test_auto_single_docx_usa_dossie():
    ok, err = _should_run_process_lawsuit_pdf_upload(
        _collected("inicial.docx"), "auto"
    )
    assert ok is False and err is None


def test_peticao_single_docx_usa_process_lawsuit_pdf():
    ok, err = _should_run_process_lawsuit_pdf_upload(
        _collected("Peticao_Inicial.docx"), "peticao_inicial"
    )
    assert ok is True and err is None


def test_peticao_multiplo_rejeita():
    ok, err = _should_run_process_lawsuit_pdf_upload(
        _collected("a.pdf", "b.pdf"), "peticao_inicial"
    )
    assert ok is False and err and "exatamente um" in err


def test_peticao_jpg_rejeita():
    ok, err = _should_run_process_lawsuit_pdf_upload(
        _collected("x.jpg"), "peticao_inicial"
    )
    assert ok is False and err and "DOC" in err


def test_contestacao_single_pdf_ok():
    ok, err = _should_run_process_lawsuit_pdf_upload(
        _collected("defesa.pdf"), "contestacao"
    )
    assert ok is True and err is None


def test_contestacao_multiplo_rejeita():
    ok, err = _should_run_process_lawsuit_pdf_upload(
        _collected("a.pdf", "b.pdf"), "contestacao"
    )
    assert ok is False and err and "exatamente um" in err


def test_contestacao_jpg_rejeita():
    ok, err = _should_run_process_lawsuit_pdf_upload(
        _collected("x.jpg"), "contestacao"
    )
    assert ok is False and err and "DOC" in err


def test_dois_arquivos_auto_dossie():
    ok, err = _should_run_process_lawsuit_pdf_upload(
        _collected("a.pdf", "b.pdf"), "auto"
    )
    assert ok is False and err is None
