# Ciclo de Extracao Incremental com IA Agents

Este documento e o ponto de coordenacao entre Codex, Cursor Agent e o usuario.
Antes de codificar melhorias de extracao, leia este arquivo e siga o ciclo abaixo.

## Regra principal

Trabalhar em apenas **um dado-alvo por ciclo**.

Nao misturar correcao de `numero_processo`, `reclamante`, datas, salario e verbas no mesmo patch.
Cada ciclo deve terminar com teste focado passando e uma indicacao clara do proximo campo.

## Protocolo de conversa com Cursor

Quando o Cursor Agent assumir uma tarefa, ele deve:

1. Ler este arquivo.
2. Ler o teste do ciclo atual.
3. Confirmar se concorda com o dado-alvo e o criterio de aceite.
4. Fazer a menor alteracao possivel.
5. Rodar o teste focado.
6. Registrar, no fim da resposta, uma destas decisoes:
   - `APROVADO`: teste passou e podemos seguir para o proximo dado.
   - `BLOQUEADO`: explicar o motivo e qual contexto falta.
   - `DISCORDO`: explicar uma alternativa tecnicamente melhor antes de codificar.

## Ciclo de trabalho

1. Escolher dado-alvo.
2. Criar fixture pequena, preferencialmente texto com marcadores de pagina.
3. Criar teste automatizado com expectativa objetiva.
4. Rodar apenas o teste do ciclo.
5. Corrigir regex, parser, normalizador ou prompt no menor escopo possivel.
6. Rodar teste focado.
7. Rodar uma suite curta de regressao.
8. Registrar proximo dado-alvo.

## Ordem sugerida dos dados

1. `numero_processo`
2. `reclamante`
3. `reclamada`
4. `vara_trabalho`
5. `data_ajuizamento`
6. `data_sentenca`
7. `data_admissao`
8. `data_demissao`
9. `salario_base`
10. `verbas_deferidas[].nome`
11. `verbas_deferidas[].periodo`
12. `verbas_deferidas[].reflexos`
13. `indice_correcao`
14. `juros_mora`
15. `divisor_horas`
16. `aviso_previo_dias` (pos-ordem sugerida — MEDIUM remanescente)
17. `motivo_rescisao`
18. `tipo_contrato`
19. `justica_gratuita` (HIGH remanescente)
20. `tipo_rito` (HIGH remanescente)
21. Integração `pre_extract` → `extract_data_with_gemini` / `processor`
22. Merge pós-IA `pre_fields["high"]` → `dados_limpos`

## Ciclo atual

- Status: `APROVADO` (Claude Code).
- Dado-alvo concluido: **horario_trabalho** (MEDIUM).
- Diagnostico: dois padroes — A "das/de/jornada: HH as HH" e B "Entrada as HH, saida as HH". Fix chave: `_HORA` usa `(?:(?:h|:)(\d{2})|h)?` para consumir 'h' solto sem minutos (antes ficava travado). Intervalo capturado no fragmento restante (h ou min). Normalizacao: "07:30" → "07h30".
- Camada: `backend/services/pre_extractor.py`.
- Teste focado:
  - `python -m pytest -q tests/test_extraction_cycle_horario_trabalho.py` -> `10 passed`.
- Regressao:
  - `tests/test_extraction_cycle_*.py` -> `482 passed`.
- Diagnostico: tres branches por prioridade — (1) sem incidencia (natureza indenizatoria, "nao ha incidencia", isencao) — maxima prioridade; (2) tabela progressiva ("conforme tabela progressiva", "tabela IRRF vigente"); (3) reclamada desconta (3 sub-padroes: A reclamada+descontar/reter/recolher+IR, B condeno+reclamada+reter+IR, C desconto do IR na fonte generico).
- Camada: `backend/services/pre_extractor.py`.
- Teste focado:
  - `python -m pytest -q tests/test_extraction_cycle_ir_retido_fonte.py` -> `11 passed`.
- Regressao:
  - `tests/test_extraction_cycle_*.py` -> `427 passed`.

## Proximo ciclo sugerido

- Dado-alvo: **`banco_horas_valido`** — banco de horas reconhecido como valido/invalido (bool MEDIUM).
- Alternativa: **`cargo_confianca`** — cargo de confianca reconhecido (bool MEDIUM).

## Ciclos anteriores (referencia)

- **horario_trabalho** — 2 padroes (das/de vs Entrada/saida); fix `_HORA` consome 'h' solto; intervalo em h ou min; normalizacao 07:30→07h30; 10 testes focados; suite `tests/test_extraction_cycle_*.py` `482 passed`.
- **advogado_reclamante + advogado_reclamada** — `_NOME_ADV` reutilizavel; prefixos Advogado/Adv./Patrono; Dr(a). opcional; unico metodo para ambos; 11 testes focados; suite `tests/test_extraction_cycle_*.py` `472 passed`.
- **prescricao_quinquenal** — prioridade Parcial > Afastada > Acolhida; "acolho parcialmente" nao vira "Acolhida"; cobre quinquenal e bienal; 12 testes focados; suite `tests/test_extraction_cycle_*.py` `461 passed`.
- **valor_causa** — 3 padroes (cabecalho, "Atribuo/Fixo/Dou a causa", "em R$"); normalizado via `_formatar_moeda_br`; nao confunde com valores de condenacao; 11 testes focados; suite `tests/test_extraction_cycle_*.py` `449 passed`.
- **jornada_contratual** — regex A: `\bjornada\b.{0,60}?` tolera palavras intermediarias; fix `(?:[xX]|por)` vs classe de caracteres; 12x36 tem prioridade; 11 testes focados; suite `tests/test_extraction_cycle_*.py` `438 passed`.
- **ir_retido_fonte** — prioridade: sem incidencia > tabela progressiva > reclamada desconta; 3 sub-padroes reclamada; cobre IRRF, IR e "imposto de renda"; 11 testes focados; suite `tests/test_extraction_cycle_*.py` `427 passed`.
- **contribuicao_previdenciaria** — prioridade: sem incidencia > ambas as partes > reclamada; 4 sub-padroes reclamada; fix plural `contribuicoes previdenciarias` (`s?`); 11 testes focados; suite `tests/test_extraction_cycle_*.py` `416 passed`.
- **custas_processuais** — 3 sub-padroes reclamada (nominal/explicito/implicito); prioridade isencao > reclamante > reclamada; valor base "sobre R$" e "no valor de"; `pel[ao]` handle "pelo reu"; 9 testes focados; suite `tests/test_extraction_cycle_*.py` `405 passed`.
- **multa_art_467** — regex espelhada da 477 com numero de artigo trocado; guard por diferenca de digitos; 8 testes focados (inclui independencia 467+477); suite `tests/test_extraction_cycle_*.py` `396 passed`.
- **dano_moral + dano_material** — Pattern A: conector "a titulo de" (sem verbo); Pattern B: verbo + rotulo + conector; licao `[^.]*?` vs pontos de milhar; 12 testes focados; suite `tests/test_extraction_cycle_*.py` `388 passed`.
- **obrigacoes_fazer PPP** — regex com guard de verbo judicial; agente nocivo opcional na descricao; contrato 5-campo (tipo/descricao/prazo_dias/multa_diaria/multa_limite); 7 testes focados; suite `tests/test_extraction_cycle_*.py` `376 passed`.
- **prazo_dias em seguro_desemprego** — paridade com CTPS: uma linha por branch (CD/SD e alvara) para chamar `_prazo_obrigacao_dias_no_fragmento`; guard 1-120 dias; 5 testes focados; suite `tests/test_extraction_cycle_*.py` `369 passed`.
- **multa_diaria/multa_limite em seguro_desemprego** — hookup de astreintes para itens seguro CD/SD e alvara; captura fragment via walrus operator no match; 5 testes focados; suite `tests/test_extraction_cycle_*.py` `364 passed`.
- **obrigacoes_fazer[].multa_limite** — teto de astreintes no mesmo fragmento, somente quando `multa_diaria` ja existe; regex `_RE_MULTA_LIMITE_OBRIGACAO` com 4 formas (limitada a / ate o limite de / nao podendo exceder / com teto de); guard impede extracao sem multa_diaria; teste focado `6 passed`; suite `tests/test_extraction_cycle_*.py` `359 passed`.
- **obrigacoes_fazer[].multa_diaria** - astreintes vinculadas a CTPS/guias quando aparecem no mesmo fragmento; teste focado 5 passed; suite tests/test_extraction_cycle_*.py 353 passed.
- **obrigacoes_fazer[].prazo_dias CTPS** - prazo em dias vinculado ao item CTPS quando estiver na mesma frase da obrigacao; anchor renderiza prazo; teste focado 4 passed; suite tests/test_extraction_cycle_*.py 348 passed.
- **frontend fixture DEV obrigacoes_fazer** - URL /extractor?fixture=obrigacoes carrega CTPS, guias rescisorias e seguro-desemprego no modo audit; npm run lint e npm run build passed; inspecao visual Browser Use bloqueada por Node v22.15.0 (< v22.22.0).
- **frontend obrigacoes_fazer no AnalysisReport** - lista CTPS/guias visivel no modo audit e padrao; npm run lint e npm run build passed.
- **obrigacoes_fazer guias rescisorias** — lista estruturada MEDIUM com item TRCT/codigo SJ2/chave/alvara FGTS, agregando com CTPS; teste focado `6 passed`; suite `tests/test_extraction_cycle_*.py` `339 passed`.
- **obrigacoes_fazer CTPS** — lista estruturada MEDIUM com item CTPS derivado de anotacao/retificacao/baixa da CTPS; teste focado `6 passed`; suite `tests/test_extraction_cycle_*.py` `333 passed`.
- **guias_rescisorias** — novo campo top-level no schema `2.20`, extraido como MEDIUM para TRCT/codigo SJ2/chave/alvara FGTS em contexto de entrega; teste focado `7 passed`; suite `tests/test_extraction_cycle_*.py` `327 passed`.
- **funcao_reclamante** — campo ja existente, agora extraido como MEDIUM em contexto claro de funcao/cargo do reclamante; teste focado `7 passed`; suite `tests/test_extraction_cycle_*.py` `320 passed`.
- **prazo_calculos_dias** — novo campo top-level no schema `2.19`, extraido como MEDIUM quando prazo de dias esta ligado a calculos/liquidacao; teste focado `8 passed`; suite `tests/test_extraction_cycle_*.py` `313 passed`.
- **data_intimacao_calculos** — novo campo top-level no schema `2.18`, extraido como MEDIUM quando ha intimacao expressa para calculos/liquidacao; teste focado `7 passed`; suite `tests/test_extraction_cycle_*.py` `305 passed`.
- **data_transito_julgado** — novo campo top-level no schema `2.17`, extraido como MEDIUM quando ha transito em julgado expresso; teste focado `7 passed`; suite `tests/test_extraction_cycle_*.py` `298 passed`.
- **verbas_deferidas_itens[].detalhe** — enriquece itens de verbas com detalhe de 13o, ferias, saldo e aviso quando a propria linha traz subtipo/avos/dias; teste focado `8 passed`; suite `tests/test_extraction_cycle_*.py` `285 passed`.
- **FGTS periodo completo / multa de 40%** — extrai como MEDIUM periodo completo do FGTS, multa 40% em observacoes e incidencia sobre aviso apenas quando expressa; teste focado `7 passed`; suite `tests/test_extraction_cycle_*.py` `277 passed`.
- **multa_art_477** — extrai como MEDIUM `Deferida`/`Indeferida` para decisao clara da multa do art. 477, sem confundir com art. 467; teste focado `6 passed`; suite `tests/test_extraction_cycle_*.py` `270 passed`.
- **seguro_desemprego / guias** — extrai como MEDIUM entrega de guias CD/SD, guias/alvara, indenizacao substitutiva ou indeferimento; teste focado `7 passed`; suite `tests/test_extraction_cycle_*.py` `264 passed`.
- **anotacao_ctps** — extrai como MEDIUM obrigacao expressa de anotar/retificar/baixar CTPS com resumo curto e detalhes do mesmo fragmento; teste focado `7 passed`; suite `tests/test_extraction_cycle_*.py` `257 passed`.
- **data_saida_ctps** — extrai como MEDIUM a saida projetada expressa em contexto de CTPS/projecao de saida; teste focado `8 passed`; suite `tests/test_extraction_cycle_*.py` `250 passed`.
- **honorarios_sucumbenciais / percentual_honorarios** — extrai como MEDIUM honorarios sucumbenciais/reciprocos com percentual legal entre 5% e 15%; teste focado `7 passed`; suite `tests/test_extraction_cycle_*.py` `242 passed`.
- **UI selecao de texto e marca-texto no PDF** — `PdfViewer` renderiza camada de texto transparente sobre o canvas para permitir copiar trechos; botao `Marcar` cria destaque amarelo local na selecao; `npm run lint` e `npm run build` passed.
- **UI layout em largura total** — `MainLayout` removeu `mx-auto max-w-6xl`; conteudo principal agora usa `w-full min-w-0`, ocupando toda a area util entre sidebar e lateral direita; `npm run lint` e `npm run build` passed.
- **UI PDF contínuo e âncoras com página visível** — `PdfViewer` renderiza páginas contínuas em coluna, com rolagem vertical independente e página ajustada à largura no zoom 100%; correntes do modo audit exibem `pág. N` ou `sem pág.`; `npm run lint` e `npm run build` passed.
- **UI split-screen pericial da aba Extrator** — painel esquerdo PDF, painel direito relatório auditável com tema escuro, correntes e badges HIGH/MEDIUM; `npm run lint` e `npm run build` passed.
- **Aba Extrator erro terminal por log Unicode no processor** — `Mescla Regex -> ...`; suite completa backend `1107 passed`.
- **M1 memoria de calculo em stdout cp1252** — logs M1 passaram a usar ASCII para nao registrar falsa falha apos salvar JSON UTF-8; suite completa backend `1106 passed`.
- **PDF real ATSum 0010691 `partial_update` real no WebSocket** — processor real emite parcial de IA com `_meta_doc_type=embargos` e CNJ HIGH antes do terminal; suite completa backend `1105 passed`.
- **PDF real ATSum 0010691 via `/upload` + `/ws/{job_id}`** — WebSocket terminal `done` com worker real e Gemini mockado; suite completa backend `1104 passed`.
- **Consolidacao HTTP/WS PDF real ATSum 0010691** — helpers locais `_setup_real_pdf_processor_mocks`, `_post_real_pdf_upload` e `_assert_real_pdf_anchor_contract`; suite completa backend `1104 passed`.
- **PDF real ATSum 0010691 via `/upload` + `/status`** — worker real com Gemini mockado termina `done` e valida texto/ancoras no caminho da UI; suite completa backend `1103 passed`.
- **PDF real ATSum 0010691 — verbas do dispositivo** — reconhece `saldo de salários`, `13º proporcional/integral` e corta recorte antes de nova intimação PJe; suite completa backend `1102 passed`.
- **PDF real ATSum 0010691 — texto vazio / campos estruturais** — corrigiu log Unicode `≤` no `sentence_finder`, `RÉU:` para reclamada, data de dispensa em frase invertida e vara em cabeçalho judicial profundo; suite completa backend `1100 passed`.
- **Revisao documental pos-ciclos** — alinhou README/regras/docs aos contratos `pre_extract`, upload/status/WS, `cache_context` e export; suite completa backend `1095 passed`.
- **`/export-excel/{job_id}` com falha do exporter** — `test_export_excel_job_falha_exporter_retorna_500_estavel`.
- **`/export-excel/{job_id}` com resultado invalido** — `test_export_excel_job_resultado_invalido_retorna_400_sem_exporter`; corrigiu fallback `job["result"]`.
- **`/export-excel/{job_id}` com job em erro** — `test_export_excel_job_error_retorna_400_sem_exporter`.
- **`/export-excel/{job_id}` com job em processamento** — `test_export_excel_job_processing_retorna_202_sem_exporter`.
- **`/export-excel/{job_id}` com job ausente** — `test_export_excel_job_ausente_retorna_404_sem_exporter`.
- **Exportacao Excel por job_id (happy path)** — `test_export_excel_job_pronto_retorna_xlsx`.
- **Exportacao PJC com falha do exporter** — `test_export_pjc_falha_exporter_retorna_500_estavel`.
- **Exportacao PJC com corpo vazio/invalido** — `test_export_pjc_corpo_vazio_retorna_400_sem_exporter`.
- **Exportacao PJC via API (happy path)** — `test_export_pjc_happy_path_retorna_xml_com_headers`.
- **Exportacao Excel com falha do exporter** — `test_export_excel_falha_exporter_retorna_500_estavel`.
- **Exportacao Excel com corpo vazio/invalido** — `test_export_excel_corpo_vazio_retorna_400_sem_exporter`.
- **Exportacao Excel de `contestacao` via API** — `test_export_excel_contestacao_preserva_memorial_e_nome_especifico`.
- **Exportacao Excel de `peticao_inicial` via API** — `test_export_excel_peticao_preserva_memorial_e_nome_especifico`.
- **Exportacao Excel via API (sentenca/default)** — `test_export_excel_sentenca_limpa_campos_e_retornaxlsx`; corrigiu filename ASCII `Auditoria_Calculo_...xlsx`.
- **Saldo esgotado em dossie** — `test_process_lawsuit_dossie_saldo_esgotado_para_antes_de_cache_texto_ia`.
- **Cache invalido em dossie reprocessa** — `test_process_lawsuit_dossie_cache_invalido_reprocessa`.
- **Cache hit qualificado em dossie** — `test_process_lawsuit_dossie_cache_hit_qualificado`.
- **Falha nao critica da segunda IA de quadro em dossie** — `test_process_lawsuit_dossie_quadro_falha_nao_bloqueia_fluxo`.
- **Dossie com dois arquivos sem segunda IA de quadro** — `test_process_lawsuit_dossie_dois_arquivos_sem_quadro_no_payload_final`.
- **Dossie com tres arquivos e quadro comparativo no payload final** — `test_process_lawsuit_dossie_tres_arquivos_quadro_no_payload_final`.
- **Rejeicao direta de extensao invalida em `contestacao`** — `test_process_lawsuit_pdf_contestacao_extensao_invalida`.
- **Rejeicao direta de extensao invalida em `peticao_inicial`** — `test_process_lawsuit_pdf_peticao_inicial_extensao_invalida`.
- **Cache invalido em `contestacao`** — `test_process_lawsuit_pdf_contestacao_cache_invalido_reprocessa`.
- **Cache invalido em `peticao_inicial`** — `test_process_lawsuit_pdf_peticao_inicial_cache_invalido_reprocessa`.
- **Cache hit qualificado em `contestacao`** — `test_process_lawsuit_pdf_contestacao_cache_hit_qualificado`.
- **Cache hit qualificado em `peticao_inicial`** — `test_process_lawsuit_pdf_peticao_inicial_cache_hit_qualificado`.
- **Fluxo de negocio `contestacao` via `cache_context`** — `test_process_lawsuit_pdf_contestacao_cache_context_mockada`.
- **Fluxo de negocio `peticao_inicial` via `cache_context`** — `test_process_lawsuit_pdf_peticao_inicial_cache_context_mockada`.
- **Upload com extensao nao permitida** — `test_upload_extensao_nao_permitida_retorna_400_sem_processador`.
- **Upload de PDF menor que 10 bytes** — `test_upload_pdf_menor_que_10_bytes_retorna_400_sem_processador`.
- **Timeout do worker em `/upload` + `/ws/{job_id}`** — `test_upload_worker_timeout_websocket_terminal_error`.
- **Timeout do worker em `/upload` + `/status`** — `test_upload_worker_timeout_surfaces_error_on_status`.
- **WebSocket terminal de erro** após `/upload` — `test_upload_worker_exception_websocket_terminal_error`.
- **`/upload` + `/status` com falha do worker** — `test_upload_worker_exception_surfaces_error_on_status`.
- Consolidação leve helpers no mesmo arquivo HTTP/WS (`_post_minimal_upload_queued`, etc.); quatro cenários felizes/borda antes deste erro.
- WebSocket com `partial_update` antes do terminal — `test_upload_minimal_pdf_websocket_partial_then_terminal` (fake + `threading.Event` visível no teste).
- WebSocket terminal só (sem parcial) — `test_upload_minimal_pdf_websocket_terminal_happy_path`.
- HTTP borda `/upload` **`400`** — `peticao_inicial` com dois PDFs — `test_upload_peticao_inicial_dois_arquivos_retorna_400_sem_processador`.
- HTTP feliz `/upload` + `/status/{job_id}` — `test_upload_minimal_pdf_then_status_happy_path` no mesmo arquivo.
- Consolidação helpers em `tests/test_extraction_cycle_processor_e2e_mock_ia.py` (infra/payload IA); `13 passed` naquele arquivo.
- Testes existentes de roteamento **unitário** do upload (sem HTTP): `tests/test_upload_cache_context.py` — `_should_run_process_lawsuit_pdf_upload`.
- E2e mockado `doc_type == "despacho"` — `test_process_lawsuit_pdf_despacho_caminho_feliz_ia_mockada`.
- E2e mockado `doc_type == "embargos"` — `test_process_lawsuit_pdf_embargos_caminho_feliz_ia_mockada`.
- E2e **`liquidacao`** — merge HIGH **dois campos** (`numero_processo` + `reclamante`) numa linha `[PRE-HIGH]` — `test_liquidacao_e2e_pre_high_merge_numero_e_reclamante_uma_linha`.
- E2e mockado `doc_type == "acordao"` — `test_process_lawsuit_pdf_acordao_caminho_feliz_ia_mockada`.
- E2e merge HIGH `tipo_rito` + `[PRE-HIGH]` — `test_liquidacao_e2e_pre_high_sobrescreve_tipo_rito_e_log`.
- E2e merge HIGH `justica_gratuita` + `[PRE-HIGH]` — `test_liquidacao_e2e_pre_high_sobrescreve_justica_gratuita_e_log`.
- E2e merge HIGH `vara_trabalho` + `[PRE-HIGH]` — `test_liquidacao_e2e_pre_high_sobrescreve_vara_trabalho_e_log`.
- E2e merge HIGH `reclamada` + `[PRE-HIGH]` — `test_liquidacao_e2e_pre_high_sobrescreve_reclamada_e_log`.
- E2e merge HIGH `reclamante` + `[PRE-HIGH]` — `test_liquidacao_e2e_pre_high_sobrescreve_reclamante_e_log`.
- E2e merge HIGH `data_sentenca` + `[PRE-HIGH]` — `test_liquidacao_e2e_pre_high_sobrescreve_data_sentenca_e_log`.
- E2e merge HIGH `numero_processo` + `[PRE-HIGH]` — `test_liquidacao_e2e_pre_high_sobrescreve_numero_e_log`.
- E2e mockado `doc_type == "sentenca"` — `test_process_lawsuit_pdf_sentenca_caminho_feliz_ia_mockada` no mesmo arquivo.
- Asserts estruturais no e2e `liquidacao` — mesmo arquivo `tests/test_extraction_cycle_processor_e2e_mock_ia.py`.
- E2e enxuto `process_lawsuit_pdf` + IA mockada (sem asserts estruturais extras) — evolução incremental no mesmo arquivo.
- Observabilidade merge HIGH (`[PRE-HIGH]`) — teste: `tests/test_extraction_cycle_pre_high_log.py` (`4 passed`).
- Merge pós-IA `pre_fields["high"]` — teste: `tests/test_extraction_cycle_merge_pre_high.py` (`6 passed`).
- Integração `pre_extract` → IA — teste: `tests/test_extraction_cycle_pre_ia_integration.py` (`1 passed`).
- `tipo_rito` — teste: `tests/test_extraction_cycle_tipo_rito.py` (`8 passed`).
- `justica_gratuita` — teste: `tests/test_extraction_cycle_justica_gratuita.py` (`11 passed`).
- `tipo_contrato` — teste: `tests/test_extraction_cycle_tipo_contrato.py` (`10 passed`).
- `motivo_rescisao` — teste: `tests/test_extraction_cycle_motivo_rescisao.py` (`11 passed`).
- `aviso_previo_dias` — teste: `tests/test_extraction_cycle_aviso_previo_dias.py` (`11 passed`).
- `divisor_horas` — teste: `tests/test_extraction_cycle_divisor_horas.py` (`11 passed`).
- `juros_mora` — teste: `tests/test_extraction_cycle_juros_mora.py` (`9 passed`).
- `indice_correcao` — teste: `tests/test_extraction_cycle_indice_correcao.py` (`9 passed`).
- `verbas_deferidas[].reflexos` (fase 3) — teste: `tests/test_extraction_cycle_verbas_reflexos.py` (`7 passed`).
- `verbas_deferidas[].periodo` (fase 2) — teste: `tests/test_extraction_cycle_verbas_periodo.py` (`8 passed`).
- `verbas_deferidas[].nome` (fase 1) — teste: `tests/test_extraction_cycle_verbas_nomes.py` (`6 passed`).
- `salario_base` — teste: `tests/test_extraction_cycle_salario_base.py` (`8 passed`).
- `data_demissao` — teste: `tests/test_extraction_cycle_data_demissao.py` (`8 passed`).
- `data_admissao` — teste: `tests/test_extraction_cycle_data_admissao.py` (`8 passed`).
- `data_sentenca` — teste: `tests/test_extraction_cycle_data_sentenca.py` (`9 passed`).
- `data_ajuizamento` — teste: `tests/test_extraction_cycle_data_ajuizamento.py` (`7 passed`).
- `vara_trabalho` — teste: `tests/test_extraction_cycle_vara_trabalho.py` (`6 passed`).
- `reclamada` — teste: `tests/test_extraction_cycle_reclamada.py` (`6 passed`).
- `reclamante` — teste: `tests/test_extraction_cycle_reclamante.py` (`5 passed`).
- `numero_processo` — `APROVADO` em 2026-05-01 por Codex; teste: `tests/test_extraction_cycle_numero_processo.py` (`3 passed`).

## Proximo ciclo proposto

- Dado-alvo sugerido: **`obrigacoes_fazer` para PPP** — o schema `ObrigacaoFazer` ja lista `"PPP"` como tipo valido mas nao ha extrator dedicado. Fragmentos com "entregar PPP", "fornecer PPP", "PPP com agente nocivo" devem gerar um item `tipo="PPP"`. Relevante para aposentadoria especial.
- Escopo: extrator `_extract_obrigacoes_fazer_ppp` em `pre_extractor.py`; MEDIUM; mesmo padrao dos extratores CTPS/guias/seguro com suporte a prazo_dias, multa_diaria e multa_limite.
- Manter TDD/validacao pequena por ciclo.

## Mensagem recomendada para o Cursor

Cursor, revise `backend/docs/AI_AGENT_EXTRACTION_CYCLE.md`, `backend/services/pre_extractor.py` e `backend/tests/test_extraction_cycle_obrigacoes_fazer_multa_diaria.py`.

O ciclo `obrigacoes_fazer[].multa_diaria` esta aprovado: CTPS e guias rescisorias recebem astreintes quando `multa diaria de R$ ...`, `multa de R$ ... por dia` ou `astreintes de R$ ... por dia` aparece no mesmo fragmento da obrigacao. O teste negativo preserva multa art. 477 como campo proprio, sem virar astreinte. Focado `5 passed`; CTPS+guias+seguro+prazo+multa diaria `26 passed`; regressao dos ciclos `353 passed`.

Discuta o proximo ciclo proposto: `obrigacoes_fazer[].multa_limite`, somente se houver teto expresso no mesmo fragmento e preferencialmente apenas quando `multa_diaria` ja existir.

Ao final, diga `APROVADO`, `BLOQUEADO` ou `DISCORDO`.
