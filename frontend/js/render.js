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

// ── Renderização principal: dados extraídos do PDF ─────────────────────────
function renderResultado(d, envelope) {
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

  // Número do processo (usado pelo download Excel) — id no span do valor
  const numeroProcesso = d.numero_processo != null ? String(d.numero_processo) : "";

  // Resumo rápido no topo (dados extraídos do PDF)
  const resumoHtml = `
    <div class="resumo-extracao">
      <div class="resumo-item">
        <div class="label">Número do Processo</div>
        <div class="value" id="numero-processo">${escapeHtml(numeroProcesso || "—")}</div>
      </div>
      <div class="resumo-item">
        <div class="label">Reclamante</div>
        <div class="value">${escapeHtml((d.reclamante != null ? d.reclamante : "") || "—")}</div>
      </div>
      <div class="resumo-item">
        <div class="label">Reclamada</div>
        <div class="value">${escapeHtml((d.reclamada != null ? d.reclamada : "") || "—")}</div>
      </div>
      <div class="resumo-item">
        <div class="label">Data da Sentença</div>
        <div class="value">${escapeHtml((d.data_sentenca != null ? d.data_sentenca : "") || "—")}</div>
      </div>
      <div class="resumo-item">
        <div class="label">Salário Base</div>
        <div class="value">${escapeHtml((d.salario_base != null ? d.salario_base : "") || "—")}</div>
      </div>
    </div>`;

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
    <div class="resultado-titulo">
      📄 Dados extraídos do PDF
      <span class="badge">${Object.keys(d).length} campos</span>
    </div>
    ${resumoHtml}
    ${parecerHtml}

    <div class="secao">
      <div class="secao-header">📋 Identificação do Processo</div>
      <div class="campos-grid">
        <div class="campo"><div class="campo-label">Número do Processo</div>${val(d.numero_processo)}</div>
        <div class="campo"><div class="campo-label">Vara do Trabalho</div>${val(d.vara_trabalho)}</div>
        <div class="campo"><div class="campo-label">Reclamante</div>${val(d.reclamante)}</div>
        <div class="campo"><div class="campo-label">Reclamada</div>${val(d.reclamada)}</div>
        <div class="campo"><div class="campo-label">Tipo de Rito</div>${val(d.tipo_rito)}</div>
        <div class="campo"><div class="campo-label">Função do Reclamante</div>${val(d.funcao_reclamante)}</div>
        <div class="campo"><div class="campo-label">Data da Sentença</div>${val(d.data_sentenca, "destaque")}</div>
        <div class="campo"><div class="campo-label">Data de Ajuizamento</div>${val(d.data_ajuizamento)}</div>
        <div class="campo"><div class="campo-label">Justiça Gratuita</div>${val(d.justica_gratuita)}</div>
        <div class="campo"><div class="campo-label">Advogado do Reclamante</div>${val(d.advogado_reclamante)}</div>
        <div class="campo"><div class="campo-label">Juiz Responsável</div>${val(d.juiz_responsavel)}</div>
      </div>
    </div>

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
