from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import os
import time
import traceback


router = APIRouter(prefix="/api/export", tags=["Exportação"])


@router.post("/pjc")
async def export_pjc(body: dict):
    """
    Gera um arquivo .pjc (XML PJe-Calc) a partir do objeto ProcessoTrabalhista.

    Espera receber no body o JSON equivalente ao ProcessoTrabalhista (dados finais
    da extração ou do Laboratório). O frontend envia exatamente o objeto "processo"
    que está sendo exibido no relatório.
    """
    if not body or not isinstance(body, dict):
        raise HTTPException(400, "Corpo inválido: envie o objeto ProcessoTrabalhista em JSON.")

    try:
        from services.pjc_exporter import exportar_pjc, gerar_nome_arquivo

        pjc_bytes = exportar_pjc(body)
        filename = gerar_nome_arquivo(body) or "calculo.pjc"
    except Exception as exc:
        print(f"[EXPORT] Erro ao gerar PJC: {exc}", flush=True)
        raise HTTPException(500, f"Erro ao gerar PJC: {type(exc).__name__}: {exc}")

    return Response(
        content=pjc_bytes,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-PJC-Version": "5.4",
        },
    )


@router.post("/excel")
async def export_excel(body: dict):
    """
    Gera um arquivo .xlsx de auditoria a partir do objeto ProcessoTrabalhista.

    O body é o mesmo JSON de ProcessoTrabalhista. O nome do arquivo segue o
    padrão Auditoria_Calculo_[CNJ].xlsx (ASCII para header HTTP estável).
    """
    if not body or not isinstance(body, dict):
        raise HTTPException(400, "Corpo inválido: envie o objeto ProcessoTrabalhista em JSON.")

    try:
        from services.excel_exporter import exportar_excel
    except Exception as exc:
        print(f"[EXPORT] Falha ao importar excel_exporter: {exc}", flush=True)
        traceback.print_exc()
        raise HTTPException(500, f"Erro ao gerar Excel: {type(exc).__name__}: {exc}")

    # Diretório de exportação (caso o exporter venha a usá-lo futuramente)
    try:
        os.makedirs("exports", exist_ok=True)
    except Exception as exc:
        print(f"[EXPORT] Aviso: não foi possível garantir pasta 'exports': {exc}", flush=True)

    try:
        # Limpa o body removendo campos claramente não necessários / muito grandes
        campos_ignorados = {
            "raw",
            "_raw",
            "memorial_bruto",
            "explicacoes",
            "logs_pipeline",
            "shadow_logs",
        }
        # memorial_juridico: manter em petição inicial / contestação (aba Resumo); omitir no resto
        meta_dt = (body.get("_meta_doc_type") or "").strip().lower()
        is_peticao = meta_dt == "peticao_inicial"
        is_contestacao = meta_dt == "contestacao"
        if not is_peticao and not is_contestacao:
            campos_ignorados = {*campos_ignorados, "memorial_juridico"}

        dados_limpos = {
            k: v for k, v in body.items()
            if k not in campos_ignorados
        }

        # Reaproveita a mesma API do exporter, usando um job_id sintético
        numero_proc = (dados_limpos.get("numero_processo") or "").strip()
        job_id = numero_proc or f"ts_{int(time.time())}"

        caminho_xlsx = exportar_excel(dados_limpos, str(job_id))

        numero = numero_proc or f"{int(time.time())}"
        numero_sanitizado = numero.replace("/", "-").replace(".", "") or "processo"
        if is_peticao:
            nome_download = f"Pedidos_Inicial_{numero_sanitizado}.xlsx"
        elif is_contestacao:
            nome_download = f"Contestacao_{numero_sanitizado}.xlsx"
        else:
            nome_download = f"Auditoria_Calculo_{numero_sanitizado}.xlsx"
    except Exception as exc:
        print(f"[EXPORT] Erro ao gerar Excel: {exc}", flush=True)
        traceback.print_exc()
        raise HTTPException(500, f"Erro ao gerar Excel: {type(exc).__name__}: {exc}")

    from fastapi.responses import FileResponse

    return FileResponse(
        path=caminho_xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=nome_download,
        headers={
            "Content-Disposition": f'attachment; filename="{nome_download}"',
        },
    )

