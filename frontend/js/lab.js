/**
 * lab.js — Laboratório de Aprendizado da Perita
 *
 * 8 campos de upload — Marcha processual (Fase de Conhecimento + Liquidação):
 *   1. peticao        (PDF/DOCX)  — opcional · Petição Inicial (verbas pedidas, causa de pedir)
 *   2. contestacao    (PDF/DOCX)  — opcional · Contestação (argumentos de exclusão)
 *   3. processo       (PDF/DOC/DOCX) — obrigatório · Título Executivo (sentença + acórdãos)
 *   4. liquidacao     (PDF/DOC/DOCX) — recomendado · cálculo da empresa
 *   5. parecer        (PDF/DOC/DOCX) — obrigatório · parecer da perita
 *   6. impugnacao     (PDF/DOC/DOCX) — opcional · impugnação da empresa
 *   7. calculo-pjc    (PDF/.PJC/.XML) — opcional · parâmetros PJe-Calc
 *   8. manifestacao   (PDF/DOC/DOCX) — opcional · manifestação da perita
 */

// Usa a mesma origem da página (funciona em qualquer porta: 8000, 8001, etc.)
const LAB_API = (typeof window !== "undefined" && window.location && window.location.origin)
  ? window.location.origin
  : "http://localhost:8000";

// Estado local do laboratório
let _relatorio = null;

// Acumulador de arquivos para o Card 3 (Título Executivo Complexo)
let _processoFiles = [];

// ── Toggle da seção ──────────────────────────────────────────────────────────

function initLabToggle() {
  const btn = document.getElementById("btn-toggle-lab");
  const sec = document.getElementById("lab-section");
  if (!btn || !sec) return;

  btn.addEventListener("click", () => {
    const open = sec.classList.toggle("open");
    btn.classList.toggle("active", open);
    btn.textContent = open
      ? "✖ Fechar Laboratório"
      : "🧪 Laboratório de Aprendizado da Perita";
    if (open) sec.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

// Definição dos 8 campos — marcha processual
const LAB_CAMPOS = [
  // Fase de Conhecimento (opcional)
  { inputId: "lab-peticao",       nameId: "lab-peticao-name",       cardId: "card-peticao",       obrigatorio: false, formKey: "peticao" },
  { inputId: "lab-contestacao",   nameId: "lab-contestacao-name",   cardId: "card-contestacao",   obrigatorio: false, formKey: "contestacao" },
  // Obrigatórios mínimos (sentença + parecer)
  { inputId: "lab-processo",       nameId: "lab-processo-name",     cardId: "card-processo",       obrigatorio: true },
  { inputId: "lab-liquidacao",   nameId: "lab-liquidacao-name",   cardId: "card-liquidacao",     obrigatorio: false },
  { inputId: "lab-parecer",      nameId: "lab-parecer-name",      cardId: "card-parecer",         obrigatorio: true },
  // Opcionais de enriquecimento
  { inputId: "lab-impugnacao",    nameId: "lab-impugnacao-name",   cardId: "card-impugnacao",     obrigatorio: false },
  { inputId: "lab-calculo-pjc",  nameId: "lab-calculo-pjc-name",  cardId: "card-calculo-pjc",    obrigatorio: false },
  { inputId: "lab-manifestacao",  nameId: "lab-manifestacao-name", cardId: "card-manifestacao",  obrigatorio: false, formKey: "manifestacao" },
];

// Pesos de cada card para o score de eficiência (total 100)
const _EFICIENCIA_PESOS = {
  processo:    30,  // Card 3 — Título Executivo (obrigatório)
  parecer:     20,  // Card 5 — Laudo Pericial
  liquidacao:  15,  // Card 4 — Cálculos da empresa
  calculo_pjc: 10,  // Card 7 — Parâmetros PJC
  manifestacao: 10, // Card 8 — Retórica de combate
  contestacao:  7,  // Card 2 — Argumentos de exclusão
  impugnacao:   5,  // Card 6 — Style Transfer defesa
  peticao:      3,  // Card 1 — Contexto dos pedidos
};

// ── Validação: bloquear .doc (Word antigo) ────────────────────────────────────

/**
 * Retorna true se o ficheiro for .doc (formato antigo do Word), não suportado pelo backend.
 */
function _isDocAntigo(file) {
  if (!file || !file.name) return false;
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  const mime = (file.type || "").toLowerCase();
  return ext === "doc" || mime === "application/msword";
}

/**
 * Mostra toast de aviso quando o utilizador tenta anexar um .doc.
 */
function _showLabToastDocNaoSuportado() {
  const id = "lab-toast-doc-nao-suportado";
  const existing = document.getElementById(id);
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.id = id;
  toast.setAttribute("role", "alert");
  toast.innerHTML = `
    <span style="font-size:18px;line-height:1">⚠️</span>
    <div style="flex:1;min-width:0">
      <p style="margin:0;font-size:12px;font-weight:600;color:#e8eaf0">Formato não suportado</p>
      <p style="margin:4px 0 0;font-size:11px;color:#8b92a9;line-height:1.4">O ficheiro selecionado é um .doc (versão antiga do Word). Por favor, abra o ficheiro no Word, clique em "Salvar Como" e escolha a opção "Documento do Word (*.docx)" antes de o anexar.</p>
    </div>
    <button type="button" aria-label="Fechar" style="background:none;border:none;cursor:pointer;color:#8b92a9;font-size:16px;line-height:1;padding:0 2px">×</button>
  `;
  Object.assign(toast.style, {
    position: "fixed",
    bottom: "24px",
    right: "24px",
    maxWidth: "380px",
    display: "flex",
    alignItems: "flex-start",
    gap: "12px",
    padding: "14px 16px",
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: "10px",
    boxShadow: "0 8px 24px rgba(0,0,0,0.25)",
    zIndex: "10000",
    fontFamily: "var(--sans)",
  });
  toast.querySelector("button").addEventListener("click", () => toast?.remove());
  document.body.appendChild(toast);
  setTimeout(() => toast?.remove(), 12000);
}

// ── Card 3: Título Executivo Complexo — acumulação de múltiplos documentos ───

/**
 * Renderiza a lista de arquivos acumulados no Card 3 e atualiza o label/badge.
 */
function _renderProcessoFiles() {
  const nameEl  = document.getElementById("lab-processo-name");
  const listaEl = document.getElementById("lab-processo-lista");
  const card    = document.getElementById("card-processo");
  const count   = _processoFiles.length;

  if (!count) {
    if (nameEl)  nameEl.textContent = "Escolher arquivo(s)";
    if (listaEl) listaEl.style.display = "none";
    card?.classList.remove("filled");
    return;
  }

  // Badge no label
  if (nameEl) {
    nameEl.innerHTML =
      `<span style="color:var(--purple);font-weight:600">${count} doc${count > 1 ? "s" : ""} anexado${count > 1 ? "s" : ""}</span>`;
  }
  card?.classList.add("filled");
  card?.classList.remove("error");

  // Lista removível
  if (listaEl) {
    listaEl.style.display = "block";
    listaEl.innerHTML = _processoFiles.map((f, i) => {
      const tier = _classifyDecisaoTier(f.name);
      return `<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;font-size:11px;color:var(--muted)">
        <span style="color:${tier.cor};flex-shrink:0">${tier.badge}</span>
        <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${_esc(f.name)}">${_esc(f.name)}</span>
        <button type="button" data-idx="${i}" title="Remover"
          style="background:none;border:none;cursor:pointer;color:var(--red);font-size:13px;line-height:1;padding:0 2px;flex-shrink:0">×</button>
      </div>`;
    }).join("");
    listaEl.querySelectorAll("button[data-idx]").forEach(btn => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.dataset.idx, 10);
        _processoFiles.splice(idx, 1);
        _renderProcessoFiles();
        _atualizarBotaoAnalisar();
        _atualizarBarraEficiencia();
      });
    });
  }
}

/**
 * Classifica o nível hierárquico de um documento decisório pelo nome do arquivo.
 * Retorna badge emoji + cor visual.
 */
function _classifyDecisaoTier(filename) {
  const n = (filename || "").toLowerCase();
  if (n.includes("tst") || n.includes("rr") || n.includes("recurso_de_revista") || n.includes("recurso de revista")) {
    return { badge: "🏛️ TST/RR", cor: "var(--purple)" };
  }
  if (n.includes("trt") || n.includes("ro") || n.includes("acordao") || n.includes("acórdão") || n.includes("recurso_ordinario") || n.includes("recurso ordinário")) {
    return { badge: "⚖️ TRT/RO", cor: "var(--accent2, #60a5fa)" };
  }
  return { badge: "📄 1º Grau", cor: "var(--text)" };
}

// ── Controle dos campos de upload ────────────────────────────────────────────

function initLabUploads() {
  LAB_CAMPOS.forEach(({ inputId, nameId, cardId }) => {
    const input  = document.getElementById(inputId);
    const nameEl = document.getElementById(nameId);
    const card   = document.getElementById(cardId);
    if (!input) return;

    // Card 3 (processo): acumulação de múltiplos documentos decisórios
    if (inputId === "lab-processo") {
      input.addEventListener("change", () => {
        const novos = Array.from(input.files || []);
        input.value = ""; // libera o input para nova seleção
        const docAntigos = novos.filter(_isDocAntigo);
        if (docAntigos.length) {
          _showLabToastDocNaoSuportado();
        }
        const validos = novos.filter(f => !_isDocAntigo(f));
        // Acumula evitando duplicatas pelo nome
        const nomesExistentes = new Set(_processoFiles.map(f => f.name));
        validos.forEach(f => {
          if (!nomesExistentes.has(f.name)) {
            _processoFiles.push(f);
            nomesExistentes.add(f.name);
          }
        });
        _renderProcessoFiles();
        _atualizarBotaoAnalisar();
        _atualizarBarraEficiencia();
      });
      return;
    }

    input.addEventListener("change", () => {
      const file = input.files[0];
      if (file && _isDocAntigo(file)) {
        input.value = "";
        if (nameEl) nameEl.textContent = "Escolher arquivo";
        if (card) card.classList.remove("filled", "error");
        _showLabToastDocNaoSuportado();
        _atualizarBotaoAnalisar();
        _atualizarBarraEficiencia();
        return;
      }
      if (file) {
        nameEl.textContent = file.name;
        card.classList.add("filled");
        card.classList.remove("error");
      } else {
        nameEl.textContent = "Escolher arquivo";
        card.classList.remove("filled", "error");
      }
      _atualizarBotaoAnalisar();
      _atualizarBarraEficiencia();
    });
  });
}

function _calcularEficiencia() {
  let score = 0;
  const keyToInput = {};
  LAB_CAMPOS.forEach(c => {
    const key = c.formKey || c.inputId.replace("lab-", "").replace(/-/g, "_");
    keyToInput[key] = c.inputId;
  });
  if (_EFICIENCIA_PESOS.processo && _processoFiles.length > 0) score += _EFICIENCIA_PESOS.processo;
  ["parecer", "liquidacao", "calculo_pjc", "manifestacao", "contestacao", "impugnacao", "peticao"].forEach(key => {
    const id = keyToInput[key] || "lab-" + key.replace(/_/g, "-");
    const el = document.getElementById(id);
    if (el && el.files && el.files.length > 0) score += (_EFICIENCIA_PESOS[key] || 0);
  });
  return Math.min(100, score);
}

function _atualizarBarraEficiencia() {
  const score = _calcularEficiencia();
  const bar = document.getElementById("lab-eficiencia-bar");
  const pct = document.getElementById("lab-eficiencia-pct");
  const nivel = document.getElementById("lab-eficiencia-nivel");
  const detalhe = document.getElementById("lab-eficiencia-detalhe");

  if (!bar) return;

  bar.style.width = score + "%";
  if (pct) pct.textContent = score + "%";

  const baseClass = "h-3 rounded-full transition-all duration-500 ease-out ";
  if (score === 0) {
    bar.className = baseClass + "bg-gray-600";
    if (nivel) nivel.textContent = "Aguardando arquivos...";
    if (detalhe) detalhe.textContent = "Adicione arquivos para ver a previsão atualizar em tempo real.";
  } else if (score < 25) {
    bar.className = baseClass + "bg-gray-500";
    if (nivel) nivel.textContent = "Contexto inicial — aprendizado limitado";
    if (detalhe) detalhe.textContent = "Adicione o Título Executivo (Card 3) para iniciar o aprendizado.";
  } else if (score < 45) {
    bar.className = baseClass + "bg-blue-500";
    if (nivel) nivel.textContent = "⚡ Nível 1 — Rápido: fundamentos jurídicos e estilo da perita";
    if (detalhe) detalhe.textContent = "Adicione Liquidação ou Parecer para subir para Nível 2.";
  } else if (score < 65) {
    bar.className = baseClass + "bg-yellow-500";
    if (nivel) nivel.textContent = "🔍 Nível 2 — Auditoria: detecção de discrepâncias ativa";
    if (detalhe) detalhe.textContent = "Adicione o Cálculo PJC para ativar a detecção de omissões.";
  } else if (score < 85) {
    bar.className = baseClass + "bg-orange-500";
    if (nivel) nivel.textContent = "📊 Nível 3 — Tríade: detecção automática de omissões de parâmetros";
    if (detalhe) detalhe.textContent = "Adicione Manifestação para atingir o máximo aprendizado preditivo.";
  } else {
    bar.className = baseClass + "bg-green-500";
    if (nivel) nivel.textContent = "🏆 Nível 4 — Tríade de Ouro: máximo aprendizado preditivo ativo";
    if (detalhe) detalhe.textContent = "Todos os insumos essenciais presentes. Aprendizado completo.";
  }
}

function _atualizarBotaoAnalisar() {
  const btn = document.getElementById("btn-lab-analisar");
  if (!btn) return;
  // A partir da Tríade da Liquidação, o laboratório aceita qualquer combinação
  // de arquivos (incluindo apenas Processo + Amostragem + .PJC). O backend
  // continua validando combinações inválidas, mas o botão fica sempre disponível.
  btn.disabled = false;
}

// ── Upload e análise ─────────────────────────────────────────────────────────

async function labAnalisar() {
  const btn   = document.getElementById("btn-lab-analisar");
  const steps = document.getElementById("lab-steps");

  // Nenhum campo é obrigatório: o backend aceita qualquer combinação.
  // Ainda assim, avisamos o usuário se ele for analisar totalmente vazio.
  const outrosSelecionados = LAB_CAMPOS.filter(c => {
    if (c.inputId === "lab-processo") return false; // tratado via _processoFiles
    const el = document.getElementById(c.inputId);
    return el && el.files && el.files.length > 0;
  }).length;
  const totalSelecionados = outrosSelecionados + _processoFiles.length;
  if (!totalSelecionados) {
    _labStatus(
      "Nenhum arquivo selecionado. Você pode analisar assim mesmo, mas o relatório ficará praticamente vazio.",
      "err"
    );
    // Não damos return: deixamos o usuário decidir.
  }

  btn.disabled    = true;
  btn.textContent = "⏳ Analisando...";
  steps.classList.remove("open");

  const totalArquivos = outrosSelecionados + _processoFiles.length;
  _labStatus(`Enviando ${totalArquivos} arquivo(s) e processando... (pode levar até 2 min)`, "spin");

  const form = new FormData();

  // Inclui user_id para rastrear processos únicos no dashboard
  const userId = document.getElementById("user-id")?.value?.trim() || "anonimo";
  form.append("user_id", userId);

  // Card 3: todos os documentos decisórios acumulados (mesma chave "processo")
  _processoFiles.forEach(f => form.append("processo", f));

  LAB_CAMPOS.forEach(c => {
    if (c.inputId === "lab-processo") return; // já tratado acima
    const el = document.getElementById(c.inputId);
    if (el && el.files && el.files.length > 0) {
      const key = c.formKey || c.inputId.replace("lab-", "").replace("-", "_");
      form.append(key, el.files[0]);
    }
  });

  try {
    const res = await fetch(`${LAB_API}/lab/analisar`, {
      method: "POST",
      body: form,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    _relatorio = await res.json();
    _labStatus(
      `Análise concluída — ${_relatorio.discrepancias?.length ?? 0} discrepância(s) encontrada(s).`,
      "ok"
    );
    _renderPassos(_relatorio);
    steps.classList.add("open");

  } catch (e) {
    _labStatus(`Erro: ${e.message}`, "err");
  } finally {
    btn.disabled    = false;
    btn.textContent = "🔬 Analisar e Gerar Relatório de Discrepância";
    // Limpa o acumulador do Card 3 após análise
    _processoFiles = [];
    _renderProcessoFiles();
  }
}

// ── Renderização dos passos ───────────────────────────────────────────────────

function _renderPassos(r) {
  _renderPasso1(r);
  _renderPasso2(r);
  _renderPasso3(r);
  _renderPasso4(r);
}

// Resultado 1 — Linha do Tempo: Prova → Direito → Cálculo
function _renderPasso1(r) {
  const el = document.getElementById("lab-step-1-body");
  if (!el) return;

  let html = "";

  // ── Arquivos analisados ──────────────────────────────────────────────────────
  const arqs = r.arquivos_analisados;
  if (arqs) {
    const arqsHtml = Object.entries(arqs)
      .filter(([, v]) => v)
      .map(([k, v]) => `<span class="lab-fund-tag" style="border-color:var(--muted);color:var(--muted)">${_esc(k)}: ${_esc(v)}</span>`)
      .join("");
    if (arqsHtml) {
      html += `<div class="lab-fund-list" style="margin-bottom:16px">${arqsHtml}</div>`;
    }
  }

  // ── FASE 1: Amostragem PDF (tese vencedora) ──────────────────────────────────
  const amos = r.amostragem_pdf;
  if (amos) {
    html += `<div style="margin-bottom:18px">
      <p style="font-size:11px;color:var(--green);text-transform:uppercase;letter-spacing:0.7px;margin-bottom:8px">
        🔬 Fase 1 — Tese Vencedora (Amostragem PDF)
      </p>`;

    if (amos.resumo) {
      html += `<p style="font-size:12px;color:var(--text);margin-bottom:10px;line-height:1.5">${_esc(amos.resumo)}</p>`;
    }
    if ((amos.teses_provadas || []).length) {
      html += `<p style="font-size:10px;color:var(--muted);text-transform:uppercase;margin-bottom:6px">Teses provadas</p><div class="lab-verbas-list">`;
      amos.teses_provadas.forEach(t => {
        html += `<span class="lab-verba-tag" style="border-color:var(--green);color:var(--green)">${_esc(t)}</span>`;
      });
      html += `</div>`;
    }
    if ((amos.irregularidades || []).length) {
      html += `<div class="lab-fields-grid" style="margin-top:10px">`;
      amos.irregularidades.forEach(ir => {
        html += `<div class="lab-field-item">
          <span class="lab-field-key">${_esc(ir.verba || "—")}</span>
          <span class="lab-field-val" style="color:var(--red)">${_esc(ir.irregularidade || "—")}</span>
        </div>`;
      });
      html += `</div>`;
    }
    if (amos.model_used) {
      html += `<p style="font-size:10px;color:var(--muted);margin-top:6px;font-family:var(--mono)">modelo: ${_esc(amos.model_used)}</p>`;
    }
    html += `</div>`;
  }

  // ── Petição Inicial (Card 1) ───────────────────────────────────────────────────
  const peticao = r.peticao_inicial;
  if (peticao) {
    html += `<div style="margin-bottom:18px">
      <p style="font-size:11px;color:var(--accent);text-transform:uppercase;letter-spacing:0.7px;margin-bottom:8px">⚖️ Petição Inicial</p>`;
    if ((peticao.verbas_pedidas || []).length) {
      html += `<p style="font-size:10px;color:var(--muted);margin-bottom:4px">Verbas pedidas</p><div class="lab-verbas-list">`;
      (peticao.verbas_pedidas || []).forEach(v => { html += `<span class="lab-verba-tag" style="border-color:var(--accent);color:var(--accent)">${_esc(v)}</span>`; });
      html += `</div>`;
    }
    if (peticao.causa_pedir) html += `<p style="font-size:12px;color:var(--text);margin-top:8px;line-height:1.4">${_esc(peticao.causa_pedir)}</p>`;
    if (peticao.periodo_reivindicado) html += `<p style="font-size:11px;color:var(--muted);margin-top:4px">Período: ${_esc(peticao.periodo_reivindicado)}</p>`;
    html += `</div>`;
  }

  // ── Contestação (Card 2) ───────────────────────────────────────────────────────
  const contestacao = r.contestacao;
  if (contestacao) {
    html += `<div style="margin-bottom:18px">
      <p style="font-size:11px;color:var(--purple);text-transform:uppercase;letter-spacing:0.7px;margin-bottom:8px">🛡️ Contestação</p>`;
    if ((contestacao.teses_empresa || []).length) {
      html += `<p style="font-size:10px;color:var(--muted);margin-bottom:4px">Teses da empresa</p><div class="lab-verbas-list">`;
      (contestacao.teses_empresa || []).forEach(t => { html += `<span class="lab-verba-tag" style="border-color:var(--purple);color:var(--purple)">${_esc(t)}</span>`; });
      html += `</div>`;
    }
    if ((contestacao.argumentos_exclusao || []).length) {
      html += `<div class="lab-fields-grid" style="margin-top:8px">`;
      (contestacao.argumentos_exclusao || []).slice(0, 5).forEach(ar => {
        html += `<div class="lab-field-item"><span class="lab-field-key">${_esc(ar.verba || "—")}</span><span class="lab-field-val">${_esc(ar.argumento || "—")}</span></div>`;
      });
      html += `</div>`;
    }
    html += `</div>`;
  }

  // ── FASE 2: Amostragem Word (style transfer) ──────────────────────────────────
  const amosW = r.amostragem_word;
  if (amosW) {
    const estilo = amosW.estilo || {};
    html += `<div style="margin-bottom:18px">
      <p style="font-size:11px;color:var(--purple);text-transform:uppercase;letter-spacing:0.7px;margin-bottom:8px">
        📝 Fase 2 — Style Transfer (Amostragem Word)
        ${amosW.style_atualizado ? '<span style="color:var(--green);font-size:10px;margin-left:8px">✓ skills/amostragem_style.md atualizado</span>' : ""}
      </p>`;

    if (estilo.resumo_estilo) {
      html += `<p style="font-size:12px;color:var(--text);margin-bottom:10px;line-height:1.5">${_esc(estilo.resumo_estilo)}</p>`;
    }
    const campos2 = [
      ["Tom", estilo.tom],
      ["Estrutura", estilo.estrutura_argumentativa],
      ["Tabelas comparativas", estilo.tabelas_comparativas ? "Sim" : "Não"],
    ].filter(([, v]) => v);
    if (campos2.length) {
      html += `<div class="lab-fields-grid">`;
      campos2.forEach(([k, v]) => {
        html += `<div class="lab-field-item">
          <span class="lab-field-key">${_esc(k)}</span>
          <span class="lab-field-val" style="color:var(--purple)">${_esc(String(v))}</span>
        </div>`;
      });
      html += `</div>`;
    }
    if ((estilo.expressoes_caracteristicas || []).length) {
      html += `<p style="font-size:10px;color:var(--muted);text-transform:uppercase;margin:10px 0 6px">Expressões características</p><div class="lab-verbas-list">`;
      estilo.expressoes_caracteristicas.slice(0, 5).forEach(e => {
        html += `<span class="lab-verba-tag" style="border-color:var(--purple);color:var(--purple)">${_esc(e)}</span>`;
      });
      html += `</div>`;
    }
    html += `</div>`;
  }

  // ── FASE 3: Sentença (o que o juiz deferiu) ──────────────────────────────────
  const sec    = r.sentenca || r.processo || {};
  const campos = sec.campos_chave || {};
  const verbas = sec.verbas || [];
  const erro   = sec.erro;

  html += `<div>
    <p style="font-size:11px;color:var(--accent);text-transform:uppercase;letter-spacing:0.7px;margin-bottom:8px">
      ⚖️ Fase 3 — Sentença (o que o juiz deferiu)
    </p>`;

  if (erro) {
    html += `<p class="lab-status err">Erro ao processar processo: ${_esc(erro)}</p>`;
  }
  if (sec.model_used) {
    html += `<p style="font-size:10px;color:var(--muted);margin-bottom:10px;font-family:var(--mono)">
      modelo: ${_esc(sec.model_used)} · tipo: ${_esc(sec.doc_type || "—")}
    </p>`;
  }

  const camposKeys = Object.keys(campos);
  if (camposKeys.length) {
    html += `<div class="lab-fields-grid">`;
    camposKeys.forEach(k => {
      html += `<div class="lab-field-item">
        <span class="lab-field-key">${_esc(k.replace(/_/g, " "))}</span>
        <span class="lab-field-val">${_esc(campos[k] || "—")}</span>
      </div>`;
    });
    html += `</div>`;
  }
  if (verbas.length) {
    html += `<p style="font-size:10px;color:var(--muted);text-transform:uppercase;margin:10px 0 6px">Verbas deferidas</p><div class="lab-verbas-list">`;
    verbas.forEach(v => { html += `<span class="lab-verba-tag">${_esc(v)}</span>`; });
    html += `</div>`;
  }
  if (!camposKeys.length && !verbas.length && !erro) {
    html += `<p style="color:var(--muted);font-size:12px">Nenhum campo extraído da sentença.</p>`;
  }

  // ── Conclusão da Tríade de Ouro Expandida ─────────────────────────────────
  const triade       = r.triade_pericial || {};
  const triAmostragem = triade.amostragem_presente;
  const triSentenca   = triade.sentenca_presente;
  const triPjc        = triade.pjc_presente;
  const triAviso      = triade.aviso;
  const triManifestacao = triade.manifestacao || null;
  const argVencedor   = triManifestacao ? triManifestacao.argumento_vencedor : null;
  const padroesCount  = triManifestacao ? (triManifestacao.padroes_count || 0) : 0;

  html += `</div>`;

  html += `<div style="margin-top:18px;padding-top:14px;border-top:1px dashed var(--border);">
    <p style="font-size:11px;color:var(--cyan);text-transform:uppercase;letter-spacing:0.7px;margin-bottom:8px">
      ⚔️ Conclusão da Tríade de Ouro Expandida
    </p>
    <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;font-size:11px;">
      <div style="padding:10px 12px;border:1px solid var(--border);border-radius:10px;background:rgba(15,17,23,0.7);">
        <p style="font-weight:600;color:var(--text);margin:0 0 4px;">① Amostragem (Provas)</p>
        <p style="margin:0;color:${triAmostragem ? "var(--green)" : "var(--muted)"};">
          ${triAmostragem ? "✔ Tese identificada na amostragem pericial." : "○ Sem amostragem PDF enviada para este caso."}
        </p>
      </div>
      <div style="padding:10px 12px;border:1px solid var(--border);border-radius:10px;background:rgba(15,17,23,0.7);">
        <p style="font-weight:600;color:var(--text);margin:0 0 4px;">② Processo (Decisão Judicial)</p>
        <p style="margin:0;color:${triSentenca ? "var(--green)" : "var(--muted)"};">
          ${triSentenca ? "✔ Sentença processada com campos-chave extraídos." : "○ Sentença não pôde ser processada."}
        </p>
      </div>
      <div style="padding:10px 12px;border:1px solid var(--border);border-radius:10px;background:rgba(15,17,23,0.7);">
        <p style="font-weight:600;color:var(--text);margin:0 0 4px;">③ Cálculo .PJC (Execução)</p>
        <p style="margin:0;color:${triPjc ? "var(--green)" : "var(--orange)"};">
          ${triPjc ? "✔ Parâmetros do PJe-Calc disponíveis para auditoria." : "⚠ .PJC não fornecido — parametrização matemática não validada."}
        </p>
      </div>
      <div style="padding:10px 12px;border:1px solid var(--border);border-radius:10px;background:rgba(15,17,23,0.7);">
        <p style="font-weight:600;color:var(--text);margin:0 0 4px;">④ Manifestação (Combate)</p>
        ${triManifestacao
          ? `<p style="margin:0 0 4px;color:var(--green);">✔ ${padroesCount} padrão(ões) Ataque/Defesa codificado(s).</p>
             ${argVencedor ? `<p style="margin:0;color:var(--muted);font-style:italic;">"${_esc(argVencedor)}"</p>` : ""}`
          : `<p style="margin:0;color:var(--muted);">○ Manifestação não enviada — retórica de combate não aprendida.</p>`
        }
      </div>
    </div>
    ${triAviso ? `<p style="margin-top:8px;font-size:11px;color:var(--muted);">${_esc(triAviso)}</p>` : ""}
  </div>`;

  el.innerHTML = html;
}

// Passo 2 — Onde a liquidação divergiu
function _renderPasso2(r) {
  const el = document.getElementById("lab-step-2-body");
  if (!el) return;

  const discs = r.discrepancias || [];
  if (!discs.length) {
    el.innerHTML = `<p class="lab-no-disc">Nenhuma divergência crítica identificada automaticamente.</p>`;
    return;
  }

  let html = `<div class="lab-disc-list">`;
  discs.forEach(d => {
    const cls = d.nivel === "ERRO" ? "" : "aviso";
    html += `<div class="lab-disc-item ${cls}">
      <div class="lab-disc-linha">
        <span class="lab-disc-key">Juiz disse</span>
        <span class="lab-disc-val">${_esc(d.juiz_disse || "—")}</span>
      </div>
      <div class="lab-disc-linha">
        <span class="lab-disc-key">Empresa calc.</span>
        <span class="lab-disc-val">${_esc(d.empresa_calculou || "—")}</span>
      </div>
      <div class="lab-disc-linha">
        <span class="lab-disc-key">Correção</span>
        <span class="lab-disc-val">${_esc(d.juliana_corrigiu || "—")}</span>
      </div>
      ${d.fundamento ? `<span class="lab-disc-fundamento">⚖ ${_esc(d.fundamento)}</span>` : ""}
    </div>`;
  });
  html += `</div>`;

  // Comparação rápida de verbas da liquidação
  const verbas_liq = r.liquidacao?.verbas_calculadas || [];
  if (verbas_liq.length) {
    html += `<div style="margin-top:14px">
      <p style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.7px;margin-bottom:8px">
        Verbas encontradas na liquidação
      </p>
      <div class="lab-verbas-list">`;
    verbas_liq.forEach(v => {
      html += `<span class="lab-verba-tag" style="border-color:var(--orange);color:var(--orange)">${_esc(v)}</span>`;
    });
    html += `</div></div>`;
  }

  el.innerHTML = html;
}

// Resultado 3 — Regras Preditivas + Fundamentos da Perita
function _renderPasso3(r) {
  const el = document.getElementById("lab-step-3-body");
  if (!el) return;

  let html = "";

  // ── Regras Preditivas (geradas por cross-reference Amostragem × Sentença) ────
  const aprendizados = r.aprendizados || [];
  const regrasPreditivas = aprendizados.filter(a => a.origem === "amostragem_cross_reference");
  const tesesPreditivas  = aprendizados.filter(a => a.origem === "amostragem_tese");

  if (regrasPreditivas.length || tesesPreditivas.length) {
    html += `<p style="font-size:11px;color:var(--green);text-transform:uppercase;letter-spacing:0.7px;margin-bottom:8px">
      🎯 Regras Preditivas — Cross-Reference Amostragem × Sentença
    </p>`;

    if (regrasPreditivas.length) {
      html += `<div class="lab-disc-list">`;
      regrasPreditivas.forEach(ap => {
        html += `<div class="lab-disc-item">
          <div class="lab-disc-linha">
            <span class="lab-disc-key">Regra</span>
            <span class="lab-disc-val" style="color:var(--green)">${_esc(ap.titulo)}</span>
          </div>
          <div class="lab-disc-linha">
            <span class="lab-disc-key">Auditoria</span>
            <span class="lab-disc-val">${_esc(ap.correcao || ap.descricao || "—")}</span>
          </div>
          ${ap.base_legal ? `<span class="lab-disc-fundamento">⚖ ${_esc(ap.base_legal)}</span>` : ""}
        </div>`;
      });
      html += `</div>`;
    }

    if (tesesPreditivas.length) {
      html += `<p style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:0.7px;margin:12px 0 6px">
        Teses vencedoras identificadas (para playbook)
      </p><div class="lab-fund-list">`;
      tesesPreditivas.forEach(ap => {
        html += `<span class="lab-fund-tag" style="border-color:var(--green);color:var(--green)">${_esc(ap.titulo)}</span>`;
      });
      html += `</div>`;
    }
  }

  // Suporta chave "parecer" (nova) ou "manifestacao" (legado)
  const parecerSec = r.parecer || r.manifestacao || {};
  const fund = parecerSec.fundamentos_juridicos || [];
  const disc = parecerSec.discrepancias_levantadas || [];
  const erro = parecerSec.erro;

  if (erro) {
    html += `<p class="lab-status err">Erro ao processar parecer: ${_esc(erro)}</p>`;
  }

  if (fund.length) {
    html += `<p style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.7px;margin:14px 0 8px">
      Fundamentos jurídicos — Parecer da perita
    </p>
    <div class="lab-fund-list">`;
    fund.forEach(f => { html += `<span class="lab-fund-tag">${_esc(f)}</span>`; });
    html += `</div>`;
  }

  // Impugnação (opcional)
  const impSec = r.impugnacao;
  if (impSec) {
    const fundImp = impSec.fundamentos_juridicos || [];
    const argsImp = impSec.argumentos_da_parte || [];
    if (fundImp.length) {
      html += `<p style="font-size:11px;color:var(--orange);text-transform:uppercase;letter-spacing:0.7px;margin:14px 0 8px">
        Fundamentos da impugnação da parte adversa
      </p>
      <div class="lab-fund-list">`;
      fundImp.forEach(f => {
        html += `<span class="lab-fund-tag" style="border-color:var(--orange);color:var(--orange)">${_esc(f)}</span>`;
      });
      html += `</div>`;
    }
    if (argsImp.length) {
      html += `<p style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.7px;margin:12px 0 6px">
        Argumentos da impugnação (trechos)
      </p>
      <div class="lab-disc-raw">`;
      argsImp.forEach(a => { html += `<div class="lab-disc-raw-item">${_esc(a)}</div>`; });
      html += `</div>`;
    }
  }

  // Pontos de conflito (fundamentos impugnação não cobertos no parecer)
  const conflitos = r.pontos_de_conflito || [];
  if (conflitos.length) {
    html += `<p style="font-size:11px;color:var(--red);text-transform:uppercase;letter-spacing:0.7px;margin:14px 0 8px">
      Pontos em conflito — argumentados pela parte, não rebatidos no parecer
    </p>
    <div class="lab-fund-list">`;
    conflitos.forEach(c => {
      html += `<span class="lab-fund-tag" style="border-color:var(--red);color:var(--red)">${_esc(c)}</span>`;
    });
    html += `</div>`;
  }

  // Parâmetros do cálculo PJC (opcional)
  const pjcSec = r.calculo_pjc;
  if (pjcSec && !pjcSec.erro) {
    html += `<p style="font-size:11px;color:var(--cyan);text-transform:uppercase;letter-spacing:0.7px;margin:14px 0 8px">
      Parâmetros do cálculo PJe-Calc
    </p>
    <div class="lab-fields-grid">`;
    const pjcCampos = [
      ["Índice correção", pjcSec.indice_correcao],
      ["Juros de mora",   pjcSec.juros_mora],
      ["Divisor horas",   pjcSec.divisor_horas],
    ].filter(([, v]) => v);
    pjcCampos.forEach(([k, v]) => {
      html += `<div class="lab-field-item">
        <span class="lab-field-key">${_esc(k)}</span>
        <span class="lab-field-val" style="color:var(--cyan)">${_esc(v)}</span>
      </div>`;
    });
    html += `</div>`;
    const verbPjc = pjcSec.verbas_calculadas || [];
    if (verbPjc.length) {
      html += `<div class="lab-verbas-list" style="margin-top:8px">`;
      verbPjc.forEach(v => {
        html += `<span class="lab-verba-tag" style="border-color:var(--cyan);color:var(--cyan)">${_esc(v)}</span>`;
      });
      html += `</div>`;
    }
  }

  if (disc.length) {
    html += `<p style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.7px;margin:14px 0 8px">
      Correções identificadas no parecer (trechos)
    </p>
    <div class="lab-disc-raw">`;
    disc.forEach(d => { html += `<div class="lab-disc-raw-item">${_esc(d)}</div>`; });
    html += `</div>`;
  }

  if (!fund.length && !disc.length && !impSec && !pjcSec && !erro) {
    html = `<p style="color:var(--muted);font-size:12px">Nenhum fundamento jurídico identificado automaticamente.</p>`;
  }

  el.innerHTML = html;
}

// Passo 4 — Selecionar aprendizados e abrir pré-visualização
function _renderPasso4(r) {
  const lista = document.getElementById("lab-aprendizados-lista");
  const acoes = document.getElementById("lab-save-actions");
  if (!lista || !acoes) return;

  const aprendizados = r.aprendizados || [];
  if (!aprendizados.length) {
    lista.innerHTML = `<p style="color:var(--muted);font-size:12px">Nenhum aprendizado automático identificado. Você pode alimentar o sistema manualmente.</p>`;
    acoes.innerHTML = "";
    return;
  }

  let html = "";
  aprendizados.forEach((ap, idx) => {
    const tipoClass = ap.tipo === "regra" ? "regra" : "playbook";
    const tipoLabel = ap.tipo === "regra" ? "Nova Regra" : "Exemplo Playbook";
    const destHint  = ap.tipo === "regra"
      ? "→ <em>legal_engine/rules/lab_xxx.py</em>"
      : "→ <em>skills/sentenca_ordinaria.md</em>";
    html += `<div class="lab-aprendizado-item" id="ap-item-${idx}">
      <input type="checkbox" id="ap-check-${idx}" data-idx="${idx}">
      <div class="lab-aprend-info">
        <span class="lab-aprend-tipo ${tipoClass}">${_esc(tipoLabel)}</span>
        <span class="lab-aprend-titulo">${_esc(ap.titulo || "")}</span>
        <span class="lab-aprend-desc">${_esc(ap.descricao || "")}</span>
        ${ap.base_legal ? `<span class="lab-aprend-legal">⚖ ${_esc(ap.base_legal)}</span>` : ""}
        <span style="font-size:10px;color:var(--muted);font-family:var(--mono);margin-top:2px">${destHint}</span>
      </div>
    </div>`;
  });
  lista.innerHTML = html;

  // Marcar item ao clicar
  lista.querySelectorAll("input[type='checkbox']").forEach(cb => {
    cb.addEventListener("change", () => {
      const item = document.getElementById(`ap-item-${cb.dataset.idx}`);
      item.classList.toggle("selected", cb.checked);
    });
  });

  // Botão abre pré-visualização (não salva diretamente)
  acoes.innerHTML = `
    <button class="btn-lab-save" id="btn-lab-preview-sel" style="background:linear-gradient(135deg,var(--purple),var(--accent2))">
      👁 Pré-visualizar antes de Salvar
    </button>`;
  document.getElementById("btn-lab-preview-sel").addEventListener("click", labAbrirPreview);
}

// ── Coletar selecionados ──────────────────────────────────────────────────────

function _coletarSelecionados() {
  const aprendizados = _relatorio?.aprendizados || [];
  const selecionados = [];
  document.querySelectorAll("[id^='ap-check-']").forEach(cb => {
    if (cb.checked) {
      const idx = parseInt(cb.dataset.idx, 10);
      if (aprendizados[idx]) selecionados.push({ idx, ap: aprendizados[idx] });
    }
  });
  return selecionados;
}

// ── Abrir pré-visualização: chama /lab/preview e monta modal ─────────────────

async function labAbrirPreview() {
  const btn = document.getElementById("btn-lab-preview-sel");
  const selecionados = _coletarSelecionados();

  if (!selecionados.length) {
    _mostrarFeedbackSalvar("Selecione pelo menos um aprendizado.", false);
    return;
  }

  btn.disabled    = true;
  btn.textContent = "Carregando pré-visualização...";

  try {
    const res = await fetch(`${LAB_API}/lab/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ aprendizados: selecionados.map(s => s.ap) }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    _abrirModal(data.previews, selecionados);
  } catch (e) {
    _mostrarFeedbackSalvar(`Erro ao carregar pré-visualização: ${e.message}`, false);
  } finally {
    btn.disabled    = false;
    btn.textContent = "👁 Pré-visualizar antes de Salvar";
  }
}

// ── Modal de pré-visualização ─────────────────────────────────────────────────

let _modalOverlay = null;

function _abrirModal(previews, selecionados) {
  // Remove modal anterior se existir
  _fecharModal();

  const total = previews.length;
  const overlay = document.createElement("div");
  overlay.className = "lab-modal-overlay";
  overlay.id = "lab-modal-overlay";

  // Fecha ao clicar fora
  overlay.addEventListener("click", e => {
    if (e.target === overlay) _fecharModal();
  });

  // Monta cards de preview
  let cardsHtml = "";
  previews.forEach((pv, i) => {
    const tipoClass = pv.tipo === "regra" ? "regra" : "playbook";
    const tipoLabel = pv.tipo === "regra" ? "Nova Regra" : "Exemplo Playbook";
    const lingLabel = pv.tipo === "regra" ? "Python" : "Markdown";
    const titulo    = selecionados[i]?.ap?.titulo || pv.nome_arquivo || "";

    cardsHtml += `
      <div class="lab-preview-card">
        <div class="lab-preview-card-header">
          <div class="lab-preview-card-left">
            <span class="lab-preview-tipo ${tipoClass}">${tipoLabel}</span>
            <span class="lab-preview-titulo">${_esc(titulo)}</span>
          </div>
          <span class="lab-preview-destino" title="${_esc(pv.destino)}">${_esc(pv.destino)}</span>
        </div>
        <div class="lab-preview-edit-label">
          <span>${lingLabel}</span>
          <span class="lab-preview-edit-hint">✏ Edite o conteúdo antes de salvar</span>
        </div>
        <textarea
          class="lab-preview-textarea"
          id="lab-preview-ta-${i}"
          spellcheck="false"
          autocorrect="off"
          autocapitalize="off"
        >${_escAttr(pv.conteudo)}</textarea>
      </div>`;
  });

  overlay.innerHTML = `
    <div class="lab-modal" role="dialog" aria-modal="true" aria-labelledby="lab-modal-title">

      <div class="lab-modal-header">
        <div class="lab-modal-title">
          <div class="lab-modal-title-icon">👁</div>
          <span id="lab-modal-title">Pré-visualização do Aprendizado</span>
        </div>
        <button class="lab-modal-close" id="lab-modal-close" aria-label="Fechar">✕</button>
      </div>

      <p class="lab-modal-subtitle">
        Revise e edite o conteúdo abaixo antes de confirmar o salvamento.
        O que você vê aqui é <strong>exatamente o que será gravado em disco</strong>.
        Campos marcados com borda amarela indicam que foram editados.
      </p>

      <div class="lab-modal-body">
        ${cardsHtml}
      </div>

      <div class="lab-modal-footer">
        <span class="lab-modal-footer-info">
          ${total} item(s) será(ão) salvo(s)
        </span>
        <div class="lab-modal-actions">
          <button class="btn-modal-cancel" id="btn-modal-cancel">Cancelar</button>
          <button class="btn-modal-confirm" id="btn-modal-confirm">
            💾 Confirmar e Salvar
          </button>
        </div>
      </div>

    </div>`;

  document.body.appendChild(overlay);
  _modalOverlay = overlay;
  document.body.style.overflow = "hidden";

  // Fechar pelo botão X
  document.getElementById("lab-modal-close").addEventListener("click", _fecharModal);
  document.getElementById("btn-modal-cancel").addEventListener("click", _fecharModal);

  // Marcar textarea como "modified" ao editar
  previews.forEach((_, i) => {
    const ta = document.getElementById(`lab-preview-ta-${i}`);
    if (!ta) return;
    const original = ta.value;
    ta.addEventListener("input", () => {
      ta.classList.toggle("modified", ta.value !== original);
    });
  });

  // Botão confirmar — coleta conteúdos (editados ou originais) e salva
  document.getElementById("btn-modal-confirm").addEventListener("click", () =>
    labConfirmarSalvar(previews, selecionados)
  );
}

function _fecharModal() {
  if (_modalOverlay) {
    _modalOverlay.remove();
    _modalOverlay = null;
  }
  document.body.style.overflow = "";
}

// ── Confirmar e Salvar (chamado do modal) ─────────────────────────────────────

async function labConfirmarSalvar(previews, selecionados) {
  const btnConfirmar = document.getElementById("btn-modal-confirm");
  if (btnConfirmar) {
    btnConfirmar.disabled    = true;
    btnConfirmar.textContent = "Salvando...";
  }

  const numero_processo = _relatorio?.numero_processo || "";
  const resultados = [];

  for (let i = 0; i < selecionados.length; i++) {
    const ap = selecionados[i].ap;
    const ta = document.getElementById(`lab-preview-ta-${i}`);
    const conteudo_editado = ta ? ta.value : null;

    try {
      const res = await fetch(`${LAB_API}/lab/salvar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ aprendizado: ap, numero_processo, conteudo_editado }),
      });
      const data = await res.json();
      resultados.push(data);
    } catch (e) {
      resultados.push({ salvo: false, msg: e.message });
    }
  }

  const salvos = resultados.filter(r => r.salvo).length;
  const falhas = resultados.length - salvos;

  // Mostrar resultado dentro do modal
  const footer = document.querySelector(".lab-modal-footer");
  if (footer) {
    let fb = footer.querySelector(".lab-modal-feedback");
    if (!fb) {
      fb = document.createElement("div");
      footer.insertBefore(fb, footer.firstChild);
    }
    const ok = salvos > 0;
    fb.className = `lab-modal-feedback ${ok ? "ok" : "err"}`;

    if (ok) {
      // Monta descrição dos modelos utilizados
      const modelos = resultados
        .filter(r => r.salvo)
        .map(r => {
          const parts = [];
          if (r.model_used_rule  && r.model_used_rule  !== "user_edited") parts.push(`regra: ${_modelLabel(r.model_used_rule)}`);
          if (r.model_used_skill && r.model_used_skill !== "user_edited") parts.push(`skill: ${_modelLabel(r.model_used_skill)}`);
          return parts.join(" | ");
        })
        .filter(Boolean)
        .join("; ");

      fb.textContent = "Aprendizado consolidado: Log registrado e Manual de Instruções (Skills) atualizado com sucesso."
        + (modelos ? ` [${modelos}]` : "");
    } else {
      fb.textContent = `Erro ao salvar. ${resultados.map(r => r.msg).join(" | ")}`;
    }
  }

  if (salvos > 0) {
    // Fechar modal após 2.5 s e mostrar feedback consolidado no passo 4
    setTimeout(() => {
      _fecharModal();
      _mostrarFeedbackSalvar(
        "Aprendizado consolidado: Log registrado e Manual de Instruções (Skills) atualizado com sucesso.",
        true
      );
      // Toast que direciona o usuário ao dashboard de Estatísticas
      _labToastEstatisticas();
    }, 2500);
  } else {
    if (btnConfirmar) {
      btnConfirmar.disabled    = false;
      btnConfirmar.textContent = "💾 Confirmar e Salvar";
    }
  }
}

// ── Helper: label legível para o modelo Gemini usado ─────────────────────────

function _modelLabel(modelId) {
  if (!modelId) return "";
  if (modelId === "template_fallback") return "template";
  if (modelId === "user_edited")       return "editado";
  if (modelId.includes("2.5-pro"))     return "Gemini 2.5 Pro";
  if (modelId.includes("2.0-flash"))   return "Gemini 2.0 Flash";
  return modelId;
}

// ── Helper: escape para atributo HTML ────────────────────────────────────────

function _escAttr(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// ── Toast de notificação pós-salvar ───────────────────────────────────────────

/**
 * Exibe um toast flutuante notificando o perito de que o conhecimento foi
 * integrado ao motor e sugerindo a navegação até a aba Estatísticas.
 * Remove-se automaticamente após 6 s ou ao clicar.
 */
function _labToastEstatisticas() {
  // Remove toast existente para evitar acúmulo
  const existing = document.getElementById("lab-toast-stats");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.id = "lab-toast-stats";
  toast.innerHTML = `
    <span style="font-size:18px;line-height:1">🧠</span>
    <div style="flex:1;min-width:0">
      <p style="margin:0;font-size:12px;font-weight:600;color:#e8eaf0">Conhecimento integrado!</p>
      <p style="margin:2px 0 0;font-size:11px;color:#8b92a9">
        Verifique a aba <strong style="color:#4f8ef7;cursor:pointer" onclick="_labNavEstatisticas()">Estatísticas</strong>
        para ver a evolução do motor.
      </p>
    </div>
    <button onclick="document.getElementById('lab-toast-stats')?.remove()"
      style="background:none;border:none;cursor:pointer;color:#8b92a9;font-size:16px;line-height:1;padding:0 2px"
      title="Fechar">×</button>
  `;
  Object.assign(toast.style, {
    position: "fixed",
    bottom: "24px",
    right: "24px",
    zIndex: "9999",
    display: "flex",
    alignItems: "flex-start",
    gap: "10px",
    background: "#1a1e2e",
    border: "1px solid rgba(79,142,247,0.35)",
    borderRadius: "10px",
    padding: "12px 14px",
    boxShadow: "0 4px 24px rgba(0,0,0,0.45)",
    maxWidth: "320px",
    animation: "labToastIn 0.25s ease",
  });

  document.body.appendChild(toast);
  setTimeout(() => toast?.remove(), 6000);
}

function _labNavEstatisticas() {
  // Navega para a view de Estatísticas se a função global showView existir
  if (typeof showView === "function") {
    showView("estatisticas");
  }
  document.getElementById("lab-toast-stats")?.remove();
}

// ── Helpers de UI ─────────────────────────────────────────────────────────────

function _labStatus(msg, type = "") {
  const el = document.getElementById("lab-status");
  if (!el) return;
  el.textContent = msg;
  el.className   = `lab-status ${type}`;
}

function _mostrarFeedbackSalvar(msg, ok) {
  const acoes = document.getElementById("lab-save-actions");
  if (!acoes) return;

  let fb = acoes.querySelector(".lab-save-feedback");
  if (!fb) {
    fb = document.createElement("div");
    acoes.appendChild(fb);
  }
  fb.className   = `lab-save-feedback ${ok ? "ok" : "err"}`;
  fb.textContent = msg;
}

function _esc(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Inicialização ─────────────────────────────────────────────────────────────

function initLab() {
  initLabToggle();
  initLabUploads();
  _atualizarBarraEficiencia();

  const btnAnalisar = document.getElementById("btn-lab-analisar");
  if (btnAnalisar) {
    btnAnalisar.addEventListener("click", labAnalisar);
  }
}

document.addEventListener("DOMContentLoaded", initLab);
