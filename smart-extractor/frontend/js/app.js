/**
 * PJe-Calc Smart Extractor — Lógica principal
 * API, upload, polling, status e export (PJC / Excel).
 */

// Usa a mesma origem da página (funciona em qualquer porta: 8000, 8001, etc.)
const API = (typeof window !== "undefined" && window.location && window.location.origin)
  ? window.location.origin
  : "http://localhost:8000";
let pollingInterval = null;
let currentJobId = null;
let _historicoDados = [];
let _pdfObjectUrl = null;
let _selectedFiles = [];  // array of File (multi-upload dossiê)
let _statsCache = null;
let _statsPollingId = null;   // ID do setInterval para o polling de estatísticas

// ── PDF Preview (Estados: upload / viewer) ─────────────────────────────────

function handlePdfFileChange(fileOrFileList) {
  const files = fileOrFileList && (fileOrFileList instanceof FileList ? Array.from(fileOrFileList) : [fileOrFileList]).filter(Boolean);
  if (!files.length) return;

  _selectedFiles = files;

  if (_pdfObjectUrl) {
    URL.revokeObjectURL(_pdfObjectUrl);
    _pdfObjectUrl = null;
  }
  const firstPdf = files.find(function (f) { return (f.name || "").toLowerCase().endsWith(".pdf"); });
  if (firstPdf) {
    _pdfObjectUrl = URL.createObjectURL(firstPdf);
  }

  const viewer       = document.getElementById("pdf-viewer");
  const uploadState  = document.getElementById("upload-state");
  const viewerState  = document.getElementById("viewer-state");
  const placeholder  = document.getElementById("upload-placeholder");
  const fileListEl   = document.getElementById("upload-file-list");

  if (fileListEl) {
    const n = files.length;
    const names = files.map(function (f) { return f.name || "arquivo"; }).join(", ");
    fileListEl.textContent = n + " arquivo" + (n !== 1 ? "s" : "") + " selecionado" + (n !== 1 ? "s" : "") + ": " + names;
    fileListEl.classList.remove("hidden");
  }
  if (placeholder) placeholder.classList.add("hidden");

  if (viewer && _pdfObjectUrl) {
    viewer.setAttribute("data", _pdfObjectUrl);
  }

  if (uploadState && viewerState) {
    uploadState.classList.add("hidden");
    viewerState.classList.remove("hidden");
  }
}

function clearPdfViewer() {
  if (_pdfObjectUrl) {
    URL.revokeObjectURL(_pdfObjectUrl);
    _pdfObjectUrl = null;
  }
  _selectedFiles = [];

  const viewer       = document.getElementById("pdf-viewer");
  const uploadState  = document.getElementById("upload-state");
  const viewerState  = document.getElementById("viewer-state");
  const pdfFile      = document.getElementById("pdf-file");
  const placeholder  = document.getElementById("upload-placeholder");
  const fileListEl   = document.getElementById("upload-file-list");

  if (viewer) viewer.removeAttribute("data");
  if (uploadState && viewerState) {
    viewerState.classList.add("hidden");
    uploadState.classList.remove("hidden");
  }
  if (pdfFile) pdfFile.value = "";
  if (placeholder) placeholder.classList.remove("hidden");
  if (fileListEl) {
    fileListEl.textContent = "";
    fileListEl.classList.add("hidden");
  }
}

// ── KPI Widgets ──────────────────────────────────────────────────────────

function atualizarKPIs(dados) {
  const d = dados || {};

  const verbas = Array.isArray(d.verbas_deferidas) ? d.verbas_deferidas.length : 0;
  const elVerbas = document.getElementById('kpi-verbas');
  if (elVerbas) elVerbas.textContent = verbas > 0 ? verbas : '—';

  const alertas = Array.isArray(d.alertas_juridicos) ? d.alertas_juridicos.length : 0;
  const elAlertas = document.getElementById('kpi-alertas');
  if (elAlertas) {
    elAlertas.textContent  = alertas >= 0 ? alertas : '—';
    elAlertas.style.color  = alertas > 0 ? '#f75f5f' : '';
  }

  const indice = d.indice_correcao || d.criterio_atualizacao || d.indice_monetario || '—';
  const elIndice = document.getElementById('kpi-indice');
  if (elIndice) elIndice.textContent = indice;
}

function resetarKPIs() {
  ['kpi-verbas', 'kpi-alertas', 'kpi-indice'].forEach(function (id) {
    const el = document.getElementById(id);
    if (el) { el.textContent = '—'; el.style.color = ''; }
  });
}

// ── Créditos ─────────────────────────────────────────────────────────────
async function loadCredits() {
  const userId = document.getElementById("user-id").value.trim();
  if (!userId) return;
  try {
    const res = await fetch(`${API}/credits/${userId}`);
    const data = await res.json();
    document.getElementById("credits-display").textContent =
      `${data.credits} crédito${data.credits !== 1 ? "s" : ""}`;
  } catch (e) {
    document.getElementById("credits-display").textContent = "— créditos";
  }
}

function initCredits() {
  const userEl = document.getElementById("user-id");
  if (userEl) {
    userEl.addEventListener("blur", loadCredits);
    loadCredits();
  }
}

// ── Upload (single PDF ou dossiê multi-arquivo) ─────────────────────────────
async function uploadPDF() {
  const userId = document.getElementById("user-id").value.trim();
  const input = document.getElementById("pdf-file");
  const files = _selectedFiles.length ? _selectedFiles : (input && input.files && input.files.length ? Array.from(input.files) : []);
  if (!userId) {
    alert("Informe o ID do usuário");
    return;
  }
  if (!files.length) {
    alert("Selecione um ou mais arquivos do dossiê (PDF, Word, Excel, PJC, XML ou imagens).");
    return;
  }

  const exportBar = document.getElementById("export-bar");
  if (exportBar) exportBar.classList.remove("show");
  const btnPjc = document.getElementById("btn-pjc");
  if (btnPjc) btnPjc.classList.remove("show");
  const btnExcel = document.getElementById("btn-excel");
  if (btnExcel) btnExcel.classList.remove("show");

  resetarKPIs();

  const btn = document.getElementById("btn-upload");
  btn.disabled = true;
  btn.textContent = "Enviando...";

  const formData = new FormData();
  formData.append("user_id", userId);
  // Campo exatamente "files" (plural) para match com backend: files: List[UploadFile] = File(..., alias="files")
  for (let i = 0; i < files.length; i++) {
    formData.append("files", files[i]);
  }

  try {
    const res = await fetch(`${API}/upload`, { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) {
      showErro(data.detail || data.message || "Erro no upload");
      resetBtn();
      return;
    }
    startPolling(data.job_id);
  } catch (e) {
    showErro("Não foi possível conectar ao servidor");
    resetBtn();
  }
}

function resetBtn() {
  const btn = document.getElementById("btn-upload");
  if (btn) {
    btn.disabled = false;
    btn.textContent = "⚡ Extrair Dados";
  }
}

// ── Polling ───────────────────────────────────────────────────────────────
function startPolling(jobId) {
  let attempts = 0;
  const maxAttempts = 300;
  setStatus("processing", "Processando PDF...");

  pollingInterval = setInterval(async () => {
    attempts++;
    if (attempts > maxAttempts) {
      clearInterval(pollingInterval);
      showErro("Tempo esgotado. Tente novamente.");
      resetBtn();
      return;
    }
    if (attempts > 5) {
      setStatus("processing", `Processando PDF... (${attempts * 3}s)`);
    }

    try {
      const res = await fetch(`${API}/status/${jobId}`);
      const data = await res.json();
      if (data.status === "processing" || data.status === "queued") return;

      clearInterval(pollingInterval);
      resetBtn();

      if (data.status === "done" || data.status === "sucesso") {
        currentJobId = jobId;
        mostrarBotaoExport();
        renderMeta(data);
        if (typeof renderResultado === "function") {
          renderResultado(data.data || data.result || data, data);
        }
        atualizarKPIs(data.data || data.result || data);
        loadCredits();
      } else {
        showErro(data.msg || "Erro desconhecido");
      }
    } catch (e) {
      // rede — continua
    }
  }, 3000);
}

// ── Status ─────────────────────────────────────────────────────────────────
function setStatus(tipo, msg, tags) {
  const bar = document.getElementById("status-bar");
  const dot = document.getElementById("status-dot");
  const text = document.getElementById("status-text");
  const meta = document.getElementById("meta-tags");
  if (!bar || !dot || !text) return;

  bar.classList.add("show");
  dot.className = `status-dot dot-${tipo}`;
  text.textContent = msg;
  if (meta) meta.innerHTML = tags ? tags : "";
}

function renderMeta(data) {
  const tipo = data.doc_type || "desconhecido";
  const model = data.model_used || "";
  const fonte = data.source || "ai";
  const pre = data.pre_extract_stats;

  const docLabels = {
    sentenca:   ["📋 Sentença", "doc-sentenca"],
    acordao:    ["⚖️ Acórdão", "doc-acordao"],
    liquidacao: ["🔢 Liquidação", "doc-liquidacao"],
    embargos:   ["📣 Embargos", "doc-embargos"],
    despacho:   ["📌 Despacho", "doc-despacho"],
    completo:   ["📄 Completo", "doc-completo"],
  };
  const [docLabel, docClass] = docLabels[tipo] || ["📄 " + tipo, "doc-completo"];

  let tags = `<span class="meta-tag ${docClass}">${docLabel}</span>`;

  if (fonte === "cache") {
    tags += `<span class="meta-tag cache-tag">⚡ Cache</span>`;
  } else if (model) {
    tags += `<span class="meta-tag model-tag">${model}</span>`;
  }
  if (pre && fonte !== "cache") {
    const total = (pre.high_fields || 0) + (pre.medium_fields || 0);
    if (total > 0) {
      tags += `<span class="meta-tag pre-tag">⚙ Pre-extract: HIGH=${pre.high_fields} MEDIUM=${pre.medium_fields}</span>`;
    }
  }

  setStatus("sucesso", `Concluído — fonte: ${fonte}`, tags);
}

function showErro(msg) {
  setStatus("erro", `❌ ${msg}`);
  const resultado = document.getElementById("resultado");
  if (resultado) resultado.classList.remove("show");
  const exportBar = document.getElementById("export-bar");
  if (exportBar) exportBar.classList.remove("show");
  const btnExcel = document.getElementById("btn-excel");
  if (btnExcel) btnExcel.classList.remove("show");
}

// ── Export PJC ─────────────────────────────────────────────────────────────
function mostrarBotaoExport() {
  const exportBar = document.getElementById("export-bar");
  const btnPjc = document.getElementById("btn-pjc");
  const btnExcel = document.getElementById("btn-excel");
  if (exportBar) exportBar.classList.add("show");
  if (btnPjc) btnPjc.classList.add("show");
  if (btnExcel) btnExcel.classList.add("show");
}

function exportarPJC() {
  if (!currentJobId) {
    alert("Nenhuma extração disponível.");
    return;
  }
  const a = document.createElement("a");
  a.href = `${API}/export-pjc/${currentJobId}`;
  a.click();
}

// ── Download Excel ─────────────────────────────────────────────────────────
function downloadExcel() {
  if (!currentJobId) return;

  const btn = document.getElementById("btn-excel");
  const textoOriginal = btn ? btn.textContent : "⬇ Baixar Excel (.xlsx)";

  if (btn) {
    btn.disabled = true;
    btn.textContent = "⏳ Gerando...";
    btn.style.background = "#166534";
  }

  fetch(`${API}/export-excel/${currentJobId}`)
    .then((response) => {
      if (response.status === 202) {
        throw new Error("Processamento ainda em andamento. Aguarde.");
      }
      if (!response.ok) {
        return response.json().then((err) => {
          throw new Error(err.detail || "Erro ao gerar Excel");
        });
      }
      return response.blob();
    })
    .then((blob) => {
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;

      const numeroEl = document.getElementById("numero-processo");
      const numero = numeroEl ? numeroEl.textContent.trim() : "processo";
      link.download = `extrator_${numero.replace(/\//g, "-").replace(/\./g, "")}.xlsx`;

      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    })
    .catch((err) => {
      alert(`Erro ao baixar Excel:\n${err.message}`);
    })
    .finally(() => {
      if (btn) {
        btn.disabled = false;
        btn.textContent = textoOriginal;
        btn.style.background = "#16A34A";
      }
    });
}

// ── Inicialização ─────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", function () {
  initCredits();
  iniciarPollingEstatisticas();

  const btnUpload = document.getElementById("btn-upload");
  if (btnUpload) btnUpload.addEventListener("click", function (e) { uploadPDF(); e.preventDefault(); });

  const btnPjc = document.getElementById("btn-pjc");
  if (btnPjc) btnPjc.addEventListener("click", function (e) { exportarPJC(); e.preventDefault(); });

  const btnExcel = document.getElementById("btn-excel");
  if (btnExcel) btnExcel.addEventListener("click", function (e) { downloadExcel(); e.preventDefault(); });

  const btnPjcAudit = document.getElementById("btn-pjc-audit");
  if (btnPjcAudit) btnPjcAudit.addEventListener("click", function (e) { uploadPjcAudit(); e.preventDefault(); });

  // PDF / dossiê: render preview and file list when file(s) selected
  const pdfFileInput = document.getElementById("pdf-file");
  if (pdfFileInput) {
    pdfFileInput.addEventListener("change", function () {
      if (this.files && this.files.length) handlePdfFileChange(this.files);
    });
  }

  // Clear PDF viewer (swap file)
  const pdfClearBtn = document.getElementById("pdf-clear-btn");
  if (pdfClearBtn) pdfClearBtn.addEventListener("click", clearPdfViewer);
});

// ── Histórico de Processos ─────────────────────────────────────────────────

async function carregarHistorico() {
  const userId = document.getElementById("user-id")?.value?.trim() || "usuario_teste";
  const lista = document.getElementById("historico-lista");
  if (!lista) return;

  lista.innerHTML = `
    <div class="flex items-center justify-center py-14 gap-3 text-muted text-[13px]">
      <svg class="animate-spin w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path>
      </svg>
      Carregando extrações…
    </div>`;

  try {
    const res = await fetch(`${API}/historico/${encodeURIComponent(userId)}?limit=50`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const body = await res.json();
    _historicoDados = body.extractions || [];

    const busca = document.getElementById("search-historico");
    if (busca) busca.value = "";

    renderizarHistorico(_historicoDados);
  } catch (e) {
    lista.innerHTML = `
      <div class="text-center py-14 text-danger text-[13px]">
        ❌ Não foi possível carregar o histórico.<br>
        <span class="text-muted text-[11px]">${e.message}</span>
      </div>`;
  }
}

function renderizarHistorico(dados) {
  const lista = document.getElementById("historico-lista");
  if (!lista) return;

  if (!dados || !dados.length) {
    lista.innerHTML = `
      <div class="text-center py-16 text-muted text-[13px]">
        <svg class="w-10 h-10 mx-auto mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
        <p>Nenhuma extração encontrada para este filtro.</p>
      </div>`;
    return;
  }

  const docIcons = {
    sentenca:   "📋",
    acordao:    "⚖️",
    liquidacao: "🧮",
    embargos:   "📣",
    despacho:   "📌",
    completo:   "📄",
  };

  const rows = dados.map(function (item) {
    const icon     = docIcons[item.doc_type] || "📄";
    const numero   = item.numero_processo || "—";
    const nome     = item.reclamante      || "—";
    const reclamada= item.reclamada       || "—";
    const modelo   = item.model_used      || "—";
    const jobId    = item.id              || "";

    let dataFmt = "—";
    if (item.created_at) {
      try {
        const d = new Date(item.created_at);
        dataFmt = d.toLocaleDateString("pt-BR") + " " +
                  d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
      } catch (_) {}
    }

    const pjcBtn = jobId
      ? `<a href="${API}/export-pjc/${jobId}" target="_blank"
            class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[11px] font-medium
                   border border-accent/40 text-accent hover:bg-accent/10 transition-colors whitespace-nowrap">
           ⬇ .PJC
         </a>`
      : "";

    const xlsBtn = jobId
      ? `<a href="${API}/export-excel/${jobId}" target="_blank"
            class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md text-[11px] font-medium
                   border border-positive/40 text-positive hover:bg-positive/10 transition-colors whitespace-nowrap">
           ⬇ Excel
         </a>`
      : "";

    return `
      <div class="bg-surface border border-border rounded-xl px-5 py-4 shadow-card hover:border-accent/30 transition-colors">
        <div class="flex flex-wrap items-start gap-x-4 gap-y-2">

          <!-- Icon + tipo -->
          <div class="flex items-center gap-2 shrink-0 w-28">
            <span class="text-lg leading-none">${icon}</span>
            <span class="text-[11px] font-medium text-muted capitalize">${item.doc_type || "doc"}</span>
          </div>

          <!-- Processo + partes -->
          <div class="flex-1 min-w-[180px]">
            <p class="text-[13px] font-semibold font-mono leading-tight truncate" title="${numero}">${numero}</p>
            <p class="text-[11px] text-muted mt-0.5 truncate" title="${nome}">Reclamante: ${nome}</p>
            <p class="text-[11px] text-muted/70 truncate" title="${reclamada}">Reclamada: ${reclamada}</p>
          </div>

          <!-- Data + modelo -->
          <div class="text-right shrink-0 hidden sm:block">
            <p class="text-[12px] text-[#e8eaf0]">${dataFmt}</p>
            <p class="text-[10px] text-muted mt-0.5 font-mono">${modelo}</p>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-2 shrink-0 ml-auto">
            ${pjcBtn}
            ${xlsBtn}
          </div>

        </div>
      </div>`;
  });

  lista.innerHTML = `<div class="flex flex-col gap-2">${rows.join("")}</div>`;
}

function filtrarHistorico() {
  const input = document.getElementById("search-historico");
  const termo = (input ? input.value : "").toLowerCase().trim();

  if (!termo) {
    renderizarHistorico(_historicoDados);
    return;
  }

  const filtrado = _historicoDados.filter(function (item) {
    const numero    = (item.numero_processo || "").toLowerCase();
    const reclamante= (item.reclamante      || "").toLowerCase();
    const reclamada = (item.reclamada       || "").toLowerCase();
    return numero.includes(termo) || reclamante.includes(termo) || reclamada.includes(termo);
  });

  renderizarHistorico(filtrado);
}

// ── Upload de .PJC para auditoria ───────────────────────────────────────────
async function uploadPjcAudit() {
  if (!currentJobId) {
    alert("Nenhuma extração disponível. Primeiro envie o PDF e aguarde o resultado.");
    return;
  }
  const input = document.getElementById("pjc-file");
  if (!input || !input.files || !input.files[0]) {
    alert("Selecione um arquivo .PJC ou .XML gerado pelo PJe-Calc.");
    return;
  }

  const file = input.files[0];
  const formData = new FormData();
  formData.append("file", file);

  const btn = document.getElementById("btn-pjc-audit");
  const originalText = btn ? btn.textContent : "🔍 Auditar .PJC";
  if (btn) {
    btn.disabled = true;
    btn.textContent = "⏳ Auditando...";
  }

  try {
    const res = await fetch(`${API}/upload-pjc/${currentJobId}`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Erro ao auditar .PJC");
    }
    const divergencias = data.divergencias || [];
    if (!divergencias.length) {
      alert("Auditoria concluída: nenhuma divergência relevante encontrada entre a sentença e o .PJC.");
    } else {
      alert(
        "Auditoria de PJe-Calc concluída.\n\nDivergências encontradas:\n- " +
          divergencias.join("\n- ")
      );
    }
  } catch (e) {
    alert(`Erro ao auditar .PJC:\n${e.message}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }
}

// ── Estatísticas (Dashboard de IA) ────────────────────────────────────────────

/**
 * Atualiza um KPI e aplica animação "kpi-updated" se o valor mudou.
 * A animação (brilho verde) é adicionada via classe CSS e removida após 1.8 s.
 */
function _setKpiValue(el, newValue) {
  if (!el) return;
  const prev = el.dataset.kpiPrev;
  const next  = String(newValue);
  el.textContent = next;
  if (prev !== undefined && prev !== next) {
    el.classList.remove("kpi-updated");       // garante reflow para re-trigger
    void el.offsetWidth;
    el.classList.add("kpi-updated");
    setTimeout(() => el.classList.remove("kpi-updated"), 1800);
  }
  el.dataset.kpiPrev = next;
}

async function carregarEstatisticas(silencioso = false) {
  const btn = document.getElementById("btn-estatisticas-refresh");
  const kpiProc   = document.getElementById("stats-kpi-processos");
  const kpiAtivas = document.getElementById("stats-kpi-regras-ativas");
  const kpiShadow = document.getElementById("stats-kpi-regras-shadow");
  const kpiOmisso = document.getElementById("stats-kpi-omissoes");
  const listaRegras = document.getElementById("stats-ultimas-regras");
  const listaVerbas = document.getElementById("stats-top-verbas");

  if (!kpiProc || !kpiAtivas || !kpiShadow || !kpiOmisso || !listaRegras || !listaVerbas) {
    return;
  }

  // No modo silencioso (polling), não bloqueia o botão nem exibe spinner
  if (!silencioso && btn) {
    btn.disabled = true;
    btn.innerHTML = `
      <svg class="w-[13px] h-[13px] animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path>
      </svg>
      Carregando…
    `;
  }

  try {
    const res = await fetch(`${API}/api/stats`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    _statsCache = data;

    const totalProc = data.processos_analisados ?? 0;
    const regrasAt  = data.regras_oficiais_ativas ?? 0;
    const regrasSh  = data.regras_em_teste_shadow ?? 0;
    const omissoes  = data.omissoes_detectadas ?? 0;

    _setKpiValue(kpiProc,   totalProc || "0");
    _setKpiValue(kpiAtivas, regrasAt  || "0");
    _setKpiValue(kpiShadow, regrasSh  || "0");
    _setKpiValue(kpiOmisso, omissoes  || "0");

    // Últimas regras aprendidas
    const regras = Array.isArray(data.ultimas_regras) ? data.ultimas_regras : [];
    if (!regras.length) {
      listaRegras.innerHTML = `<p class="text-[11px] text-muted py-4 text-center">Ainda não há regras dinâmicas registradas no Knowledge Base.</p>`;
    } else {
      const items = regras.map(function (r) {
        const status = (r.status || "shadow").toLowerCase();
        const badgeClass =
          status === "active"
            ? "bg-positive/10 text-positive border border-positive/40"
            : status === "deleted"
            ? "bg-danger/10 text-danger border border-danger/40"
            : "bg-accent2/10 text-accent2 border border-accent2/40";

        let dt = r.updated_at || r.created_at || "";
        try {
          if (dt) {
            const d = new Date(dt);
            dt = d.toLocaleDateString("pt-BR") + " " +
                 d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
          }
        } catch (_) {}

        return `
          <div class="flex items-start justify-between gap-3 border border-border/60 rounded-lg px-3 py-2.5 bg-bg/40">
            <div class="min-w-0">
              <p class="text-[12px] font-medium text-[#e8eaf0] truncate" title="${r.descricao || ""}">
                ${r.descricao || r.rule_id || "Regra dinâmica"}
              </p>
              <p class="text-[10px] text-muted mt-0.5 truncate">
                ID: ${r.rule_id || "—"}
              </p>
              <p class="text-[10px] text-muted/70 mt-0.5 truncate">
                Atualizada em: ${dt || "—"}
              </p>
            </div>
            <div class="flex flex-col items-end gap-1 shrink-0">
              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide ${badgeClass}">
                ${status === "active" ? "Ativa" : status === "deleted" ? "Removida" : "Shadow"}
              </span>
              <span class="text-[10px] text-muted font-mono">
                score: ${r.confidence_score ?? 0}
              </span>
            </div>
          </div>
        `;
      });
      listaRegras.innerHTML = `<div class="space-y-2">${items.join("")}</div>`;
    }

    // Top verbas com divergências
    const verbas = Array.isArray(data.top_verbas_divergencias)
      ? data.top_verbas_divergencias
      : [];
    if (!verbas.length) {
      listaVerbas.innerHTML = `<p class="text-[11px] text-muted py-4 text-center">Nenhuma estatística de verbas disponível ainda.</p>`;
    } else {
      const rows = verbas.map(function (v) {
        const nome = v.verba || "—";
        const qtd  = v.contagem ?? 0;
        const pct  = v.percentual ?? 0;
        const pctVal = typeof pct === "number" ? pct : 0;
        const width = Math.max(8, Math.min(100, Math.round(pctVal)));
        return `
          <div class="space-y-1">
            <div class="flex items-center justify-between text-[11px]">
              <span class="truncate">${nome}</span>
              <span class="text-muted font-mono">${qtd} · ${pctVal.toFixed(1)}%</span>
            </div>
            <div class="w-full h-1.5 rounded-full bg-bg/70 overflow-hidden">
              <div class="h-full rounded-full bg-accent2" style="width:${width}%;"></div>
            </div>
          </div>
        `;
      });
      listaVerbas.innerHTML = `<div class="space-y-2">${rows.join("")}</div>`;
    }
  } catch (e) {
    // No modo silencioso, erros de rede são ignorados silenciosamente
    if (!silencioso) {
      kpiProc.textContent   = "—";
      kpiAtivas.textContent = "—";
      kpiShadow.textContent = "—";
      kpiOmisso.textContent = "—";
      listaRegras.innerHTML = `
        <p class="text-[11px] text-danger py-4 text-center">
          ❌ Não foi possível carregar as estatísticas.<br>
          <span class="text-muted text-[10px]">${e.message}</span>
        </p>`;
      listaVerbas.innerHTML = "";
    }
  } finally {
    if (!silencioso && btn) {
      btn.disabled = false;
      btn.innerHTML = `
        <svg class="w-[13px] h-[13px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
        Atualizar Dados
      `;
    }
  }
}

/**
 * Inicia o polling reativo de estatísticas (intervalo de 5 s).
 * Chama carregarEstatisticas em modo silencioso APENAS quando
 * a aba Estatísticas está visível, para não sobrecarregar o servidor.
 */
function iniciarPollingEstatisticas() {
  if (_statsPollingId) return; // evita duplicar
  _statsPollingId = setInterval(function () {
    const view = document.getElementById("view-estatisticas");
    if (!view) return;
    const visivel = view.style.display !== "none" && view.style.display !== "";
    if (visivel) {
      carregarEstatisticas(true); // modo silencioso
    }
  }, 5000);
}

function pararPollingEstatisticas() {
  if (_statsPollingId) {
    clearInterval(_statsPollingId);
    _statsPollingId = null;
  }
}

/**
 * Zera o histórico de extrações (processos analisados).
 * Exige confirmação dupla. Não apaga regras, cache, créditos ou learning_log.
 */
async function zerarContagem() {
  const ok = window.confirm(
    "⚠️ Zerar contagem de processos analisados?\n\n" +
    "Isso remove o histórico de extrações e volta o contador para 0.\n" +
    "Regras aprendidas, cache de PDF, créditos e learning_log NÃO são apagados.\n\n" +
    "Confirmar?"
  );
  if (!ok) return;

  const kpiEl = document.getElementById("stats-kpi-processos");
  if (kpiEl) kpiEl.textContent = "…";

  try {
    const res = await fetch(`${API}/api/admin/reset-contagem`, { method: "DELETE" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (kpiEl) {
      kpiEl.textContent = "0";
      kpiEl.classList.add("kpi-updated");
      setTimeout(() => kpiEl.classList.remove("kpi-updated"), 1800);
    }
    console.info("[STATS] Contagem zerada:", data.mensagem);
    // Recarrega todos os KPIs para sincronizar
    setTimeout(() => carregarEstatisticas(true), 600);
  } catch (e) {
    console.error("[STATS] Erro ao zerar contagem:", e);
    if (kpiEl) kpiEl.textContent = "Erro";
  }
}
