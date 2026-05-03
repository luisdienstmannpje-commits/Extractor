import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import type { PDFDocumentProxy } from "pdfjs-dist";
import pdfjsWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

export function isPdfFile(file: File | null | undefined): boolean {
  if (!file) return false;
  const name = (file.name || "").toLowerCase();
  return file.type === "application/pdf" || name.endsWith(".pdf");
}

export interface PdfViewerProps {
  file: File | null;
  /** Página 1-based solicitada pelo relatório. */
  jumpToPage?: number;
  /** Incrementa a cada navegação (permite repetir a mesma página). */
  jumpSeq?: number;
  className?: string;
}

/**
 * Visualizador leve (uma página por vez) para alinhar com 🎯 pág. N do relatório.
 */
export function PdfViewer({
  file,
  jumpToPage = 1,
  jumpSeq = 0,
  className = "",
}: PdfViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pdfRef = useRef<PDFDocumentProxy | null>(null);
  const [numPages, setNumPages] = useState(0);
  const [page, setPage] = useState(1);

  useEffect(() => {
    let cancelled = false;

    const prev = pdfRef.current;
    pdfRef.current = null;
    prev?.destroy?.().catch(() => {});
    setNumPages(0);
    setPage(1);

    if (!file || !isPdfFile(file)) {
      return () => {
        cancelled = true;
      };
    }

    (async () => {
      try {
        const data = await file.arrayBuffer();
        const loadingTask = pdfjsLib.getDocument({ data });
        /**
         * Sempre fechar o doc se este efeito já foi cancelado (troca rápida de arquivo),
         * antes de publicar em pdfRef.
         */
        const doc = await loadingTask.promise;
        if (cancelled) {
          await doc.destroy().catch(() => {});
          return;
        }
        pdfRef.current = doc;
        setNumPages(doc.numPages);
      } catch {
        /* arquivo inválido ou corrida com troca de arquivo */
      }
    })();

    return () => {
      cancelled = true;
      const d = pdfRef.current;
      pdfRef.current = null;
      d?.destroy?.().catch(() => {});
    };
  }, [file]);

  useEffect(() => {
    if (jumpSeq === 0 || !numPages) return;
    const target = Math.min(Math.max(1, jumpToPage), numPages);
    setPage(target);
  }, [jumpSeq, jumpToPage, numPages]);

  useEffect(() => {
    const pdf = pdfRef.current;
    const canvas = canvasRef.current;
    if (!pdf || !canvas || page < 1) return;

    let alive = true;

    (async () => {
      try {
        const pdfPage = await pdf.getPage(page);
        if (!alive) return;
        const scale = 1.25;
        const viewport = pdfPage.getViewport({ scale });
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        const task = pdfPage.render({
          canvasContext: ctx,
          viewport,
        });
        await task.promise;
      } catch {
        /* troca rápida de arquivo ou destroy */
      }
    })();

    return () => {
      alive = false;
    };
  }, [page, numPages, file]);

  if (!file || !isPdfFile(file)) return null;

  return (
    <div className={className}>
      <div className="mb-2 flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          className="rounded border border-slate-600 bg-slate-800 px-2 py-1 hover:bg-slate-700 disabled:opacity-40"
        >
          Anterior
        </button>
        <span className="tabular-nums">
          Página {numPages ? page : "…"} / {numPages || "…"}
        </span>
        <button
          type="button"
          disabled={numPages === 0 || page >= numPages}
          onClick={() => setPage((p) => Math.min(numPages, p + 1))}
          className="rounded border border-slate-600 bg-slate-800 px-2 py-1 hover:bg-slate-700 disabled:opacity-40"
        >
          Próxima
        </button>
      </div>
      <div className="max-h-[min(70vh,720px)] overflow-auto rounded border border-slate-700 bg-slate-950/80 p-2">
        <canvas
          ref={canvasRef}
          className="mx-auto block max-w-full bg-white shadow"
        />
      </div>
    </div>
  );
}
