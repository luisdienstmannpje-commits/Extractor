/**
 * PJe-Calc Smart Extractor — Renderização dos dados extraídos do PDF
 * Helpers (val, vv, statusClass, statusLabel) e montagem do HTML (seções, alertas, verbas).
 */

function val(v, cls) {
  if (v === null || v === undefined || v === "") {
    return '<span class="campo-valor null-val">não encontrado</span>';
  }
  if (v === true) return '<span class="campo-valor bool-true">✓ Sim</span>';
  if (v === false) return '<span class="campo-valor bool-false">✗ Não</span>';
  const extra = cls ? ` ${cls}` : "";
  return `<span class="campo-valor${extra}">${escapeHtml(String(v))}</span>`;
}

function vv(v) {
  if (!v && v !== false) return '<span class="verba-val null-verba">—</span>';
  if (v === true) return '<span class="integ-sim">✓ Integra</span>';
  if (v === false) return '<span class="integ-nao">✗ Não integra</span>';
  return `<span class="verba-val">${escapeHtml(String(v))}</span>`;
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

function statusClass(s) {
  if (!s) return "status-deferida";
  const l = String(s).toLowerCase();
  if (l.includes("deferida")) return "status-deferida";
  if (l.includes("mantida")) return "status-mantida";
  if (l.includes("reformada")) return "status-reformada";
  if (l.includes("excluída") || l.includes("excluida")) return "status-excluida";
  if (l.includes("acrescida")) return "status-acrescida";
  if (l.includes("homologada")) return "status-homologada";
  if (l.includes("corrigida")) return "status-corrigida";
  if (l.includes("não informado") || l === "") return "status-deferida";
  return "status-default";
}

function statusLabel(s) {
  if (!s || String(s).toLowerCase() === "não informado" || s === "") return "deferida";
  return s;
}

// ── Raio-X: labels e ordem alinhada ao PJe-Calc ─────────────────────────────
var RAIOX_LABELS = {
  numero_processo: "Número do Processo", reclamante: "Reclamante", reclamada: "Reclamada",
  data_ajuizamento: "Data de Ajuizamento", prescricao_quinquenal: "Data Prescrição Quinquenal (Ajuiz. - 5 anos)",
  data_admissao: "Admissão", data_demissao: "Demissão", salario_base: "Maior Remuneração", divisor_horas: "Divisor de Horas", motivo_rescisao: "Motivo da Rescisão",
  indice_correcao: "Índice de Correção", juros_mora: "Juros de Mora",
  vara_trabalho: "Vara", tipo_rito: "Rito", funcao_reclamante: "Função", data_sentenca: "Data da Sentença",
  advogado_reclamante: "Adv. Reclamante", advogado_reclamada: "Adv. Reclamada", juiz_responsavel: "Juiz Responsável", valor_causa: "Valor da Causa",
  tipo_contrato: "Tipo Contrato", jornada_contratual: "Jornada", horario_trabalho: "Horário",
  aviso_previo_dias: "Aviso Prévio (dias)", data_saida_ctps: "Data Saída CTPS", anotacao_ctps: "Anotação CTPS", seguro_desemprego: "Seguro-desemprego",
  multa_art_467: "Multa Art. 467", multa_art_477: "Multa Art. 477", dano_moral: "Dano Moral", dano_material: "Dano Material",
  fgts_periodo_completo: "FGTS Período", fgts_sobre_aviso_previo: "FGTS sobre Aviso", fgts_sobre_ferias_indenizadas: "FGTS sobre Férias Inden.", fgts_multa_40_aviso_previo: "FGTS Multa 40% Aviso", fgts_observacoes: "FGTS Observações",
  honorarios_sucumbenciais: "Honorários", percentual_honorarios: "% Honorários", justica_gratuita: "Justiça Gratuita", custas_processuais: "Custas",
};
/* Ordem do Bloco 1 (Identificação e Juízo) — alinhada a ESTRUTURAL_KEYS do extraction_engine; numero_processo fica só no sticky */
var BLOCO1_KEYS = ["vara_trabalho", "juiz_responsavel", "data_sentenca", "data_ajuizamento", "valor_causa", "reclamante", "reclamada", "advogado_reclamante", "advogado_reclamada", "tipo_rito", "justica_gratuita", "prescricao_quinquenal"];

/** Normaliza valor para colar no PJe-Calc: datas DD/MM/AAAA sem espaços; CPF/CNPJ sem pontos/traços. */
function normalizeForPjeCalc(val) {
  if (val == null || val === "") return "";
  var s = String(val).trim();
  if (!s) return "";
  var onlyDigits = s.replace(/\D/g, "");
  if (onlyDigits.length === 11 || onlyDigits.length === 14) return onlyDigits;
  var dateMatch = s.match(/(\d{1,2})[\/\-\.\s]+(\d{1,2})[\/\-\.\s]+(\d{4})/);
  if (dateMatch) {
    var d = ("0" + dateMatch[1]).slice(-2), m = ("0" + dateMatch[2]).slice(-2), y = dateMatch[3];
    return d + "/" + m + "/" + y;
  }
  return s.replace(/\s+/g, " ").trim();
}

function raioxCopy(value, btnEl) {
  var raw = value != null && value !== "" ? String(value) : "";
  if (!raw) return;
  var toCopy = normalizeForPjeCalc(raw);
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(toCopy).then(function () {
      showRaioxToast("Copiado!");
      if (btnEl) {
        btnEl.classList.add("raiox-copied");
        var orig = btnEl.innerHTML;
        btnEl.innerHTML = "✓";
        setTimeout(function () {
          btnEl.classList.remove("raiox-copied");
          btnEl.innerHTML = orig;
        }, 1500);
      }
    }).catch(function () {});
  }
}

function showRaioxToast(msg) {
  var t = document.createElement("div");
  t.className = "raiox-toast";
  t.textContent = msg;
  t.style.cssText = "position:fixed;bottom:24px;right:24px;padding:8px 14px;background:var(--surface);border:1px solid var(--border);border-radius:8px;font-size:12px;z-index:9999;box-shadow:0 4px 12px rgba(0,0,0,.3);";
  document.body.appendChild(t);
  setTimeout(function () { t.remove(); }, 1500);
}

function renderRaiox(raiox) {
  var panel = document.getElementById("raiox-panel");
  if (!panel || !raiox || !raiox.categorias) {
    if (panel) panel.innerHTML = "";
    return;
  }
  var cat = raiox.categorias;
  var dicas = raiox.dicas_laboratorio || [];
  var e = cat.estrutural || {};
  var c = cat.contratual || {};
  var con = cat.condenacao || {};
  function v(k, obj) { return (obj && obj[k] != null && obj[k] !== "") ? String(obj[k]).trim() : ""; }
  function row(key, value, label) {
    var lab = label || RAIOX_LABELS[key] || key.replace(/_/g, " ");
    var val = value != null && value !== "" ? String(value) : "—";
    var safe = escapeHtml(val);
    var canCopy = val !== "—";
    var copyVal = canCopy ? escapeHtml(val) : "";
    return (
      '<div class="raiox-row">' +
      '<span class="raiox-label">' + escapeHtml(lab) + '</span>' +
      '<span class="raiox-value">' + safe + '</span>' +
      (canCopy
        ? '<button type="button" class="raiox-copy" aria-label="Copiar" title="Copiar para PJe-Calc" data-copy="' + copyVal + '">📋</button>'
        : '<button type="button" class="raiox-copy raiox-copy-disabled" aria-disabled="true">📋</button>') +
      "</div>"
    );
  }

  var html = '<div class="raiox-wrap">';

  // Sticky: número do processo (destaque) — fixo no topo ao rolar
  var numProcesso = v("numero_processo", e) || "—";
  html += '<div class="raiox-sticky">';
  html += '<div class="raiox-numero-processo">' + escapeHtml(numProcesso) + '</div>';
  html += '</div>';

  // BLOCO 5 (topo do conteúdo): Dicas do Laboratório como alerta fixo se houver
  var dicasCriticas = dicas.filter(function (d) {
    var t = (d.titulo || "").toLowerCase();
    return t.indexOf("swissport") !== -1 || t.indexOf("erro") !== -1 || t.indexOf("recorrente") !== -1 || dicas.length <= 2;
  });
  if (dicas.length > 0) {
    html += '<div class="raiox-dicas-alerta">';
    html += '<div class="raiox-dicas-alerta-title">💡 Dicas do Laboratório</div>';
    (dicasCriticas.length ? dicasCriticas : dicas).slice(0, 3).forEach(function (d) {
      html += '<div class="raiox-dica-item"><strong>' + escapeHtml(d.titulo || "") + '</strong> ' + escapeHtml((d.mensagem || "").slice(0, 120)) + (d.mensagem && d.mensagem.length > 120 ? "…" : "") + "</div>";
    });
    html += "</div>";
  }

  // BLOCO 1: Identificação e Juízo (ordem ESTRUTURAL_KEYS; numero_processo já no sticky)
  html += '<div class="raiox-secao raiox-bloco1"><div class="raiox-secao-header">Identificação e Juízo</div><div class="raiox-rows">';
  BLOCO1_KEYS.forEach(function (key) {
    html += row(key, v(key, e));
  });
  html += "</div></div>";

  // BLOCO 2: Parâmetros Estruturais (contratual; prescricao_quinquenal está no Bloco 1)
  html += '<div class="raiox-secao raiox-bloco2"><div class="raiox-secao-header">Parâmetros Estruturais</div><div class="raiox-rows">';
  html += row("data_admissao", v("data_admissao", c));
  html += row("data_demissao", v("data_demissao", c));
  html += row("salario_base", v("salario_base", c));
  html += row("divisor_horas", v("divisor_horas", c));
  html += row("motivo_rescisao", v("motivo_rescisao", c));
  html += "</div></div>";

  // BLOCO 3: Índices e Correção (mini-card colorido)
  var indice = v("indice_correcao", con);
  var juros = v("juros_mora", con);
  if (indice || juros) {
    html += '<div class="raiox-secao raiox-bloco3"><div class="raiox-secao-header">Índices e Correção</div>';
    html += '<div class="raiox-minicards">';
    html += '<div class="raiox-minicard"><span class="raiox-minicard-label">Índice</span><span class="raiox-minicard-value">' + escapeHtml(indice || "—") + '</span>' +
      (indice ? '<button type="button" class="raiox-copy raiox-minicard-copy" data-copy="' + escapeHtml(indice) + '" title="Copiar">📋</button>' : '') + '</div>';
    html += '<div class="raiox-minicard"><span class="raiox-minicard-label">Juros de Mora</span><span class="raiox-minicard-value">' + escapeHtml(juros || "—") + '</span>' +
      (juros ? '<button type="button" class="raiox-copy raiox-minicard-copy" data-copy="' + escapeHtml(juros) + '" title="Copiar">📋</button>' : '') + '</div>';
    html += "</div></div>";
  }

  // BLOCO 4: Verbas e Adicionais (badges)
  var verbasList = cat.verbas_lista || [];
  var adicList = cat.adicionais || [];
  if (verbasList.length || adicList.length) {
    html += '<div class="raiox-secao raiox-bloco4"><div class="raiox-secao-header">Verbas e Adicionais</div><div class="raiox-badges">';
    verbasList.forEach(function (vb) {
      var nome = (vb.nome || "").trim();
      if (nome) html += '<span class="raiox-badge" title="' + escapeHtml([vb.percentual, vb.reflexos].filter(Boolean).join(" · ") || nome) + '">' + escapeHtml(nome) + '</span>';
    });
    adicList.forEach(function (a) {
      var nome = (a.nome || "").trim();
      if (nome) html += '<span class="raiox-badge raiox-badge-adicional">' + escapeHtml(nome) + '</span>';
    });
    html += "</div></div>";
  }

  html += "</div>";
  panel.innerHTML = html;
  panel.classList.add("show");

  panel.querySelectorAll(".raiox-copy[data-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      raioxCopy(this.getAttribute("data-copy"), this);
    });
  });
}

// ── Renderização principal: dados extraídos do PDF ─────────────────────────
function renderResultado(d, envelope) {
  var raioxPanel = document.getElementById("raiox-panel");
  if (raioxPanel) {
    if (envelope && envelope.raiox) {
      renderRaiox(envelope.raiox);
    } else {
      raioxPanel.innerHTML = "";
      raioxPanel.classList.remove("show");
    }
  }

  const el = document.getElementById("resultado");
  if (!el) return;

  el.classList.add("show");

  if (!d || typeof d !== "object") {
    el.innerHTML = '<div class="secao"><div class="secao-header">Dados</div><p style="padding:18px;color:var(--muted);">Nenhum dado disponível.</p></div>';
    return;
  }

  // Explicações e memorial do engine
  const explicacoesLista =
    (d.explicacoes || (envelope && envelope.explicacoes)) || [];
  const memorialLista =
    (d.memorial_juridico || (envelope && envelope.memorial_juridico)) || [];
  const regrasLista =
    (d.regras_aplicadas || (envelope && envelope.regras_aplicadas)) || [];

  // Número do processo (usado pelo download Excel) — id no span do valor (mantido para export)
  const numeroProcesso = d.numero_processo != null ? String(d.numero_processo) : "";
  // Identificação (número, reclamante, reclamada, datas, salário) exibida apenas no Raio-X (Bloco 1); tabela redundante removida.

  // Seção multas/indenizações (condicional)
  const temMultas = d.multa_art_467 || d.multa_art_477 || d.dano_moral || d.dano_material;
  const secaoMultas = temMultas
    ? `<div class="secao">
        <div class="secao-header">🔴 Valores Fixos e Multas</div>
        <div class="campos-grid">
          <div class="campo"><div class="campo-label">Dano Moral</div>${val(d.dano_moral, "indeniz")}</div>
          <div class="campo"><div class="campo-label">Dano Material</div>${val(d.dano_material, "indeniz")}</div>
          <div class="campo"><div class="campo-label">Multa Art. 467 CLT</div>${val(d.multa_art_467, "destaque")}</div>
          <div class="campo"><div class="campo-label">Multa Art. 477 CLT</div>${val(d.multa_art_477, "destaque")}</div>
        </div>
      </div>`
    : "";

  // Alertas jurídicos
  const alertas = d.alertas_juridicos || [];
  const secaoAlertas = `
    <details class="group bg-surface border border-border rounded-xl mb-4 overflow-hidden">
      <summary class="cursor-pointer font-semibold text-text px-4 py-3 bg-s2 hover:bg-border transition flex items-center justify-between select-none">
        <div class="flex items-center gap-2">
          <span style="color:${alertas.length ? "var(--yellow)" : "var(--green)"}">
            ${alertas.length ? "⚠️" : "✅"}
          </span>
          <span>Alertas Jurídicos</span>
          <span class="count-badge">${alertas.length} alerta${alertas.length !== 1 ? "s" : ""}</span>
        </div>
        <svg class="w-3.5 h-3.5 text-muted group-open:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
        </svg>
      </summary>
      <div class="p-4 border-t border-border">
        ${alertas.length === 0
          ? '<div class="alertas-vazio">✓ Nenhum alerta — dados juridicamente consistentes</div>'
          : `<div class="alertas-list">${alertas.map(function (a) { return renderAlerta(a); }).join("")}</div>`
        }
      </div>
    </details>`;

  // Campos calculados
  const secaoCalculados = `
    <div class="secao">
      <div class="secao-header">🔧 Campos Calculados / Derivados</div>
      <div class="campos-grid calc-grid">
        <div class="campo">
          <div class="campo-label">Divisor de Horas Extras</div>
          ${val(d.divisor_horas, "calc")}
          <div class="campo-hint">Crítico para PjeCalc — 150/180/200/220</div>
        </div>
        <div class="campo">
          <div class="campo-label">Prescrição Quinquenal</div>
          ${val(d.prescricao_quinquenal, "calc")}
          <div class="campo-hint">Ajuizamento − 5 anos</div>
        </div>
        <div class="campo">
          <div class="campo-label">Evolução Salarial</div>
          ${val(d.evolucao_salarial)}
          <div class="campo-hint">Base para cálculo retroativo</div>
        </div>
      </div>
    </div>`;

  // Parecer técnico em formato de documento
  const parecerHtml = renderParecerTecnico(d, explicacoesLista);

  // Fundamentação jurídica / regras aplicadas
  const secaoFundamentacao = `
    <details class="group bg-surface border border-border rounded-xl mb-4 overflow-hidden">
      <summary class="cursor-pointer font-semibold text-text px-4 py-3 bg-s2 hover:bg-border transition flex items-center justify-between select-none">
        <div class="flex items-center gap-2">
          <span>📚 Fundamentação e Regras Aplicadas</span>
          <span class="count-badge">${explicacoesLista.length} fundamento${explicacoesLista.length !== 1 ? "s" : ""}</span>
        </div>
        <svg class="w-3.5 h-3.5 text-muted group-open:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
        </svg>
      </summary>
      <div class="p-4 border-t border-border">
        ${renderFundamentacao(explicacoesLista, regrasLista, memorialLista)}
      </div>
    </details>`;

  const verbas = d.verbas_deferidas || [];
  const verbasCount = verbas.length;

  el.innerHTML = `
    <span id="numero-processo" class="hidden" aria-hidden="true">${escapeHtml(numeroProcesso || "processo")}</span>
    ${parecerHtml}

    <!-- Identificação do processo: apenas no Raio-X lateral (Bloco 1). Corpo central: Parecer, Parâmetros, Verbas. -->

    <details class="group bg-surface border border-border rounded-xl mb-4 overflow-hidden">
      <summary class="cursor-pointer font-semibold text-text px-4 py-3 bg-s2 hover:bg-border transition flex items-center justify-between select-none">
        <div class="flex items-center gap-2">
          <span>👤 Dados do Contrato de Trabalho</span>
        </div>
        <svg class="w-3.5 h-3.5 text-muted group-open:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
        </svg>
      </summary>
      <div class="p-4 border-t border-border">
        <div class="campos-grid">
          <div class="campo"><div class="campo-label">Data de Admissão</div>${val(d.data_admissao)}</div>
          <div class="campo"><div class="campo-label">Data de Demissão</div>${val(d.data_demissao)}</div>
          <div class="campo"><div class="campo-label">Motivo da Rescisão</div>${val(d.motivo_rescisao)}</div>
          <div class="campo"><div class="campo-label">Tipo de Contrato</div>${val(d.tipo_contrato)}</div>
          <div class="campo"><div class="campo-label">Salário Base</div>${val(d.salario_base, "destaque")}</div>
          <div class="campo"><div class="campo-label">Jornada Contratual</div>${val(d.jornada_contratual)}</div>
          <div class="campo"><div class="campo-label">Aviso Prévio (dias)</div>${val(d.aviso_previo_dias, "destaque")}</div>
          <div class="campo"><div class="campo-label">Data Saída CTPS (c/ projeção AP)</div>${val(d.data_saida_ctps, "destaque")}</div>
          <div class="campo"><div class="campo-label">Anotação CTPS Determinada</div>${val(d.anotacao_ctps)}</div>
          <div class="campo"><div class="campo-label">Seguro-Desemprego</div>${val(d.seguro_desemprego)}</div>
          <div class="campo full-width"><div class="campo-label">Horário de Trabalho Reconhecido</div>${val(d.horario_trabalho)}</div>
        </div>
      </div>
    </details>

    <details class="group bg-surface border border-border rounded-xl mb-4 overflow-hidden">
      <summary class="cursor-pointer font-semibold text-text px-4 py-3 bg-s2 hover:bg-border transition flex items-center justify-between select-none">
        <div class="flex items-center gap-2">
          <span>📐 Parâmetros de Cálculo</span>
        </div>
        <svg class="w-3.5 h-3.5 text-muted group-open:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
        </svg>
      </summary>
      <div class="p-4 border-t border-border">
        <div class="campos-grid">
          <div class="campo"><div class="campo-label">Índice de Correção</div>${val(d.indice_correcao)}</div>
          <div class="campo"><div class="campo-label">Juros de Mora</div>${val(d.juros_mora)}</div>
          <div class="campo"><div class="campo-label">Contribuição Previdenciária</div>${val(d.contribuicao_previdenciaria)}</div>
          <div class="campo"><div class="campo-label">IR Retido na Fonte</div>${val(d.ir_retido_fonte)}</div>
          <div class="campo"><div class="campo-label">Honorários Sucumbenciais</div>${val(d.honorarios_sucumbenciais)}</div>
          <div class="campo"><div class="campo-label">Percentual Honorários</div>${val(d.percentual_honorarios)}</div>
          <div class="campo full-width"><div class="campo-label">Custas Processuais</div>${val(d.custas_processuais)}</div>
        </div>
      </div>
    </details>

    <div class="secao">
      <div class="secao-header">🏦 Regras Especiais de FGTS</div>
      <div class="campos-grid">
        <div class="campo"><div class="campo-label">FGTS sobre Aviso Prévio</div>${val(d.fgts_sobre_aviso_previo)}</div>
        <div class="campo"><div class="campo-label">Multa 40% sobre Aviso Prévio</div>${val(d.fgts_multa_40_aviso_previo)}</div>
        <div class="campo"><div class="campo-label">FGTS sobre Férias Indenizadas</div>${val(d.fgts_sobre_ferias_indenizadas)}</div>
        <div class="campo"><div class="campo-label">Base FGTS (período completo)</div>${val(d.fgts_periodo_completo)}</div>
        <div class="campo full-width"><div class="campo-label">Observações FGTS</div>${val(d.fgts_observacoes)}</div>
      </div>
    </div>

    ${secaoCalculados}
    ${secaoMultas}
    ${secaoAlertas}
    ${secaoFundamentacao}

    <div class="secao">
      <div class="secao-header">
        ⚖️ Verbas Deferidas
        <span class="count-badge">${verbasCount} verba${verbasCount !== 1 ? "s" : ""}</span>
      </div>
      ${renderVerbas(verbas)}
    </div>
  `;

  // Bind do botão de copiar parecer, se existir
  const btnCopiar = document.getElementById("btn-copiar-parecer");
  if (btnCopiar) {
    btnCopiar.onclick = copiarParecerTecnico;
  }
}

function renderAlerta(texto) {
  if (typeof texto !== "string") texto = String(texto);
  const m = texto.match(/^\[(\w+)\]\s*(.*)/s);
  if (!m) {
    return '<div class="alerta-item AVISO"><span class="alerta-nivel">AVISO</span>' + escapeHtml(texto) + "</div>";
  }
  const nivel = m[1];
  const msg = m[2];
  return (
    '<div class="alerta-item ' + nivel + '">' +
    '<span class="alerta-nivel">' + escapeHtml(nivel) + "</span>" +
    "<span>" + escapeHtml(msg) + "</span>" +
    "</div>"
  );
}

function renderVerbas(verbas) {
  if (!verbas || verbas.length === 0) {
    return '<div style="padding:20px;color:var(--muted);font-size:13px;text-align:center;">Nenhuma verba encontrada</div>';
  }

  return verbas
    .map(function (v) {
      const temValorFixo = v.valor_fixado != null && v.valor_fixado !== "";
      return (
        '<div class="verba-card">' +
        '<div class="verba-header">' +
        '<span class="verba-nome">' + escapeHtml(v.nome || "—") + "</span>" +
        '<span class="status-badge ' + statusClass(v.status_final) + '">' + escapeHtml(statusLabel(v.status_final)) + "</span>" +
        "</div>" +
        '<div class="verba-grid">' +
        '<div class="verba-campo"><div class="verba-label">Período</div>' + vv(v.periodo) + "</div>" +
        '<div class="verba-campo"><div class="verba-label">Percentual</div>' + vv(v.percentual) + "</div>" +
        '<div class="verba-campo"><div class="verba-label">Qtd. Diária</div>' + vv(v.quantidade_diaria) + "</div>" +
        '<div class="verba-campo ' + (temValorFixo ? "" : "span2") + '"><div class="verba-label">Base de Cálculo</div>' + vv(v.base_calculo) + "</div>" +
        (temValorFixo
          ? '<div class="verba-campo"><div class="verba-label">Valor Fixado</div><span class="verba-val" style="color:var(--orange);font-weight:600">' + escapeHtml(String(v.valor_fixado)) + "</span></div>"
          : "") +
        '<div class="verba-campo"><div class="verba-label">Integração Salarial</div>' +
        (v.integracao_salarial === true
          ? '<span class="integ-sim">✓ Integra</span>'
          : v.integracao_salarial === false
            ? '<span class="integ-nao">✗ Não integra</span>'
            : '<span class="verba-val null-verba">—</span>') +
        "</div>" +
        "</div>" +
        (v.reflexos && v.reflexos.length
          ? '<div class="reflexos-wrap"><div class="verba-label" style="margin-bottom:6px">Reflexos</div>' +
            v.reflexos.map(function (r) { return '<span class="reflexo-tag">' + escapeHtml(r) + "</span>"; }).join("") +
            "</div>"
          : "") +
        (v.observacoes ? '<div class="obs-wrap">💬 ' + escapeHtml(v.observacoes) + "</div>" : "") +
        "</div>"
      );
    })
    .join("");
}

function renderFundamentacao(explicacoes, regras, memorial) {
  explicacoes = Array.isArray(explicacoes) ? explicacoes : [];
  regras = Array.isArray(regras) ? regras : [];
  memorial = Array.isArray(memorial) ? memorial : [];

  if (explicacoes.length === 0 && regras.length === 0) {
    return '<div class="fundamentacao-vazio">Nenhuma fundamentação jurídica registrada para este caso.</div>';
  }

  const memorialById = {};
  memorial.forEach(function (m) {
    if (m && typeof m === "object" && m.id) {
      memorialById[m.id] = m;
    }
  });

  return (
    '<div class="fundamentacao-list">' +
    explicacoes
      .map(function (e) {
        const regraId = e.regra_id || "";
        const titulo = e.titulo || regraId || "Regra aplicada";
        const nivel = e.nivel || "";
        const baseLegal = e.base_legal || "";
        const texto = e.explicacao || "";
        const memorialEntry = regraId && memorialById[regraId] ? memorialById[regraId] : null;
        const descricaoCurta =
          memorialEntry && memorialEntry.descricao
            ? String(memorialEntry.descricao)
            : "";
        return (
          '<article class="explicacao-item">' +
          '<header class="explicacao-header">' +
          (nivel
            ? '<span class="explicacao-nivel-badge">' + escapeHtml(nivel) + "</span>"
            : "") +
          (baseLegal
            ? '<span class="explicacao-base">' + escapeHtml(baseLegal) + "</span>"
            : "") +
          "</header>" +
          '<div class="explicacao-regra">' +
          (regraId
            ? '<span class="explicacao-id-badge">' + escapeHtml(regraId) + "</span>"
            : "") +
          '<span class="explicacao-titulo">' + escapeHtml(titulo) + "</span>" +
          "</div>" +
          (descricaoCurta
            ? '<div class="explicacao-meta">' +
              '<span class="explicacao-meta-label">Afeta:</span>' +
              '<span class="explicacao-meta-valor">' + escapeHtml(descricaoCurta) + "</span>" +
              "</div>"
            : "") +
          '<div class="explicacao-texto">' + escapeHtml(texto) + "</div>" +
          "</article>"
        );
      })
      .join("") +
    "</div>"
  );
}

function renderParecerTecnico(d, explicacoes) {
  const parecerParcelas = Array.isArray(d.parecer_parcelas_apuradas) ? d.parecer_parcelas_apuradas : [];
  const parecerIntro = d.parecer_intro_parcelas || "";
  const verbas = Array.isArray(d.verbas_deferidas) ? d.verbas_deferidas : [];
  const numero = d.numero_processo || "processo";

  if (!parecerParcelas.length && !verbas.length && (!explicacoes || !explicacoes.length)) {
    return "";
  }

  // Seção I — Modelo perita: intro + itens com → alinea) TITULO e parágrafo texto
  let introHtml = "";
  if (parecerIntro) {
    introHtml = '<p class="parecer-intro-parcelas">' + escapeHtml(parecerIntro) + "</p>";
  }

  let linhasParcelas;
  if (parecerParcelas.length > 0) {
    linhasParcelas = parecerParcelas.map(function (item) {
      const letra = (item && item.alinea) || "";
      const titulo = (item && item.titulo) ? String(item.titulo) : "";
      const texto = (item && item.texto) ? String(item.texto) : "";
      const temTitulo = titulo.length > 0;
      return (
        '<li class="parecer-linha parecer-linha-perita">' +
        (temTitulo
          ? '<span class="parecer-alinea">\u2192 ' + escapeHtml(letra) + ')</span> ' +
            '<span class="parecer-titulo-item">' + escapeHtml(titulo) + '</span>' +
            '<p class="parecer-texto">' + escapeHtml(texto) + '</p>'
          : '<span class="parecer-alinea">' + escapeHtml(letra) + ')</span>' +
            '<span class="parecer-texto">' + escapeHtml(texto) + '</span>') +
        "</li>"
      );
    }).join("");
  } else {
    linhasParcelas = verbas.map(function (v, idx) {
      const letra = String.fromCharCode(97 + idx);
      const nome = v && typeof v === "object" ? (v.nome || "Verba") : "Verba";
      const reflexos = v && typeof v === "object" && Array.isArray(v.reflexos) && v.reflexos.length
        ? v.reflexos.join(", ")
        : "sem reflexos adicionais expressamente deferidos";
      const isHoraExtra = /horas?\s*extras?/i.test(nome);
      const divisor = d.divisor_horas || "aplicável";
      const percentual = v && typeof v === "object" && v.percentual ? v.percentual : "50";
      let linha = "Apuração do " + nome + ", com reflexos em " + reflexos + ".";
      if (isHoraExtra) {
        linha += " Nas horas extras, utilizadas as Súmulas 264 e 347 do TST, observado o divisor " + divisor + ", com percentual de " + percentual + "%.";
      }
      return (
        '<li class="parecer-linha">' +
        '<span class="parecer-alinea">' + letra + ')</span>' +
        '<span class="parecer-texto">' + escapeHtml(linha) + '</span>' +
        "</li>"
      );
    }).join("");
  }

  // Seção II — Critérios (modelo perita: correção, contribuições, IR, encerramento)
  function textoPorRegra(id) {
    if (!Array.isArray(explicacoes)) return "";
    const found = explicacoes.find(function (e) { return e && e.regra_id === id; });
    return found && found.explicacao ? String(found.explicacao) : "";
  }
  const textoCorrecao = textoPorRegra("ADC_58_STF") ||
    "Índices de correção monetária IPCA-E na fase pré-judicial e, a partir da citação, a incidência da taxa SELIC (art. 406 do Código Civil). Taxa Selic será \"índice conglobante\" (juros e CM).";
  // Padrão oficial dos peritos (idêntico ao explanation_engine.TEXTOS_PADRAO_CRITERIOS_PARECER)
  const textoContribPrev = (d && d.parecer_criterios_inss) ? String(d.parecer_criterios_inss) : "Contribuições Previdenciárias - Cota parte do Reclamante: Apuração conforme indicado no Decreto 3.048/99 (artigos 198 e 276, § 4º) e item III da Súmula 368 do TST.";
  const textoIR = (d && d.parecer_criterios_irrf) ? String(d.parecer_criterios_irrf) : "Imposto de Renda: calculado pela técnica dos rendimentos acumulados (RRA), conforme previsto na Instrução Normativa 1500/14 da Receita Federal do Brasil, em substituição à IN 1.127/11 que foi revogada.";
  const textoEncerramento = "Esperando haver se desincumbido do munus, a perícia coloca-se à disposição para esclarecimentos adicionais que se fizerem necessários.";

  const criteriosHtml = `
    <li class="parecer-linha"><span class="parecer-texto">${escapeHtml(textoCorrecao)}</span></li>
    <li class="parecer-linha"><span class="parecer-texto">${escapeHtml(textoContribPrev)}</span></li>
    <li class="parecer-linha"><span class="parecer-texto">${escapeHtml(textoIR)}</span></li>
    <li class="parecer-linha"><span class="parecer-texto">${escapeHtml(textoEncerramento)}</span></li>
  `;

  return (
    '<section class="parecer-card" id="parecer-tecnico">' +
    '<header class="parecer-header">' +
    '<h2 class="parecer-titulo">Parecer Técnico</h2>' +
    '<button type="button" class="btn-parecer-copy" id="btn-copiar-parecer">Copiar Parecer</button>' +
    '</header>' +
    '<div class="parecer-corpo">' +
    '<p class="parecer-processo">Referente ao processo nº ' + escapeHtml(String(numero)) + '.</p>' +
    '<p class="parecer-sec-titulo">I. PARCELAS APURADAS:</p>' +
    introHtml +
    '<ol class="parecer-lista">' + linhasParcelas + '</ol>' +
    '<p class="parecer-sec-titulo">II. CRITÉRIOS UTILIZADOS NOS CÁLCULOS:</p>' +
    '<ul class="parecer-lista-criterios">' + criteriosHtml + '</ul>' +
    '</div>' +
    '</section>'
  );
}

function copiarParecerTecnico() {
  const el = document.getElementById("parecer-tecnico");
  if (!el) return;
  const texto = el.innerText.trim();
  if (!texto) return;
  if (navigator && navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(texto).catch(function () {
      // fallback silencioso
    });
  } else {
    const textarea = document.createElement("textarea");
    textarea.value = texto;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand("copy");
    } catch (e) {
      // ignore
    }
    document.body.removeChild(textarea);
  }
}

// ── Biblioteca de Regras (modal #modal-regras) ───────────────────────────────

/**
 * Deriva categoria legível a partir de condicao.tipo (Cálculo vs Texto).
 * @param {Object} condicao - condicao da regra
 * @returns {string} "Cálculo" ou "Texto"
 */
function categoriaRegra(condicao) {
  if (!condicao || !condicao.tipo) return "Texto";
  var t = String(condicao.tipo).toLowerCase();
  if (t.indexOf("verba") !== -1 || t === "campo_diferente" || t === "campo_ausente") return "Cálculo";
  return "Texto";
}

/**
 * Popula o modal Biblioteca de Regras com as regras do Knowledge Base.
 * Regras com status "deleted" vão para a aba "Removidas"; demais para "Ativas / Shadow".
 * @param {Array} rules - array de regras (knowledge_base.rules)
 */
function renderListaRegras(rules) {
  var list = Array.isArray(rules) ? rules : [];
  console.log("Dados do KB recebidos:", list);
  var ativas = list.filter(function (r) { return (r.status || "").toLowerCase() !== "deleted"; });
  var deletadas = list.filter(function (r) { return (r.status || "").toLowerCase() === "deleted"; });

  var tbodyAtivas = document.getElementById("modal-regras-tbody-ativas");
  var tbodyDeletadas = document.getElementById("modal-regras-tbody-deletadas");
  var emptyAtivas = document.getElementById("modal-regras-empty-ativas");
  var emptyDeletadas = document.getElementById("modal-regras-empty-deletadas");

  // Limpar tabelas antes de inserir para evitar duplicações
  if (tbodyAtivas) tbodyAtivas.innerHTML = "";
  if (tbodyDeletadas) tbodyDeletadas.innerHTML = "";

  function badgeStatus(status) {
    var s = (status || "shadow").toLowerCase();
    if (s === "active") return '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-positive/15 text-positive border border-positive/40">Ativa</span>';
    if (s === "deleted") return '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-muted/20 text-muted border border-border">Removida</span>';
    return '<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-warn/15 text-warn border border-warn/40">Shadow</span>';
  }

  function row(r) {
    var id = escapeHtml(r.rule_id || "—");
    var cat = categoriaRegra(r.condicao);
    var badge = badgeStatus(r.status);
    var desc = escapeHtml(r.descricao || "—");
    var score = r.confidence_score != null ? Number(r.confidence_score) : 0;
    return "<tr class=\"border-b border-border/60 hover:bg-white/[0.03]\">" +
      "<td class=\"py-2.5 pr-3 font-mono text-[11px] text-muted\">" + id + "</td>" +
      "<td class=\"py-2.5 pr-3 text-[#e8eaf0]\">" + escapeHtml(cat) + "</td>" +
      "<td class=\"py-2.5 pr-3\">" + badge + "</td>" +
      "<td class=\"py-2.5 pr-3 text-[#e8eaf0] max-w-[280px]\">" + desc + "</td>" +
      "<td class=\"py-2.5 pl-3 text-right font-mono text-muted\">" + score + "</td>" +
      "</tr>";
  }

  if (tbodyAtivas) {
    tbodyAtivas.innerHTML = ativas.map(row).join("");
  }
  if (tbodyDeletadas) {
    tbodyDeletadas.innerHTML = deletadas.map(row).join("");
  }
  if (emptyAtivas) {
    emptyAtivas.classList.toggle("hidden", ativas.length > 0);
    emptyAtivas.textContent = list.length === 0
      ? "Nenhuma regra aprendida ainda. Processe um caso no Laboratório para começar!"
      : "Nenhuma regra ativa ou em shadow.";
  }
  if (emptyDeletadas) {
    emptyDeletadas.classList.toggle("hidden", deletadas.length > 0);
  }
}

/**
 * Abre o modal Biblioteca de Regras e aplica a aba ativa.
 */
function abrirModalRegras() {
  var modal = document.getElementById("modal-regras");
  if (!modal) return;
  modal.classList.remove("hidden");
  modal.classList.add("flex");
  document.getElementById("modal-regras-tab-ativas").focus();
  aplicarTabModalRegras("ativas");
}

/**
 * Fecha o modal Biblioteca de Regras.
 */
function fecharModalRegras() {
  var modal = document.getElementById("modal-regras");
  if (!modal) return;
  modal.classList.add("hidden");
  modal.classList.remove("flex");
}

/**
 * Alterna a aba visível no modal (ativas | deletadas).
 * @param {string} tab - "ativas" ou "deletadas"
 */
function aplicarTabModalRegras(tab) {
  var paneAtivas = document.getElementById("modal-regras-conteudo-ativas");
  var paneDeletadas = document.getElementById("modal-regras-conteudo-deletadas");
  var btnAtivas = document.getElementById("modal-regras-tab-ativas");
  var btnDeletadas = document.getElementById("modal-regras-tab-deletadas");
  if (tab === "deletadas") {
    if (paneAtivas) paneAtivas.classList.add("hidden");
    if (paneDeletadas) paneDeletadas.classList.remove("hidden");
    if (btnAtivas) { btnAtivas.classList.remove("border-accent", "text-accent"); btnAtivas.classList.add("border-transparent", "text-muted"); }
    if (btnDeletadas) { btnDeletadas.classList.add("border-accent", "text-accent"); btnDeletadas.classList.remove("border-transparent", "text-muted"); }
  } else {
    if (paneAtivas) paneAtivas.classList.remove("hidden");
    if (paneDeletadas) paneDeletadas.classList.add("hidden");
    if (btnAtivas) { btnAtivas.classList.add("border-accent", "text-accent"); btnAtivas.classList.remove("border-transparent", "text-muted"); }
    if (btnDeletadas) { btnDeletadas.classList.remove("border-accent", "text-accent"); btnDeletadas.classList.add("border-transparent", "text-muted"); }
  }
}
