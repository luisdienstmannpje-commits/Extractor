# EXTRACAO_STATUS.md — Mapeamento de Extração de Campos

> Atualizado em: 2026-05-13 | Pipeline: `processor.py` v2.4.0 (FASE 2+3 aplicadas)

## ✅ Pre-extractor conectado (FASE 2 — 2026-05-13)

O bug foi corrigido. `processor.py` agora chama `pre_extract(texto)` antes da IA e:
- Passa `pre_fields` para `extract_data_with_gemini()` (MEDIUM → âncoras no prompt)
- Aplica HIGH fields sobre o resultado da IA após validação (`dados_limpos[campo] = valor`)

O prompt da IA recebe agora uma seção "CAMPOS CONFIRMADOS" (HIGH) e "VALORES PRÉ-EXTRAÍDOS" (MEDIUM) via `build_prompt_context()` em `pre_extractor.py`.

---

## Tabela de Status por Campo

| Campo | Arquivo:linha | Método | Confiança estimada | Status atual |
|-------|--------------|--------|-------------------|--------------|
| `numero_processo` | `pre_extractor.py:258` | Regex HIGH (padrão CNJ) | ~99% | **Conectado** — sobrescreve IA |
| `data_sentenca` | `pre_extractor.py:270` | Regex HIGH (assinatura PJe) | ~98% | **Conectado** — sobrescreve IA |
| `justica_gratuita` | `pre_extractor.py:295` | Regex HIGH (booleano) | ~95% | **Conectado** — sobrescreve IA |
| `tipo_rito` | `pre_extractor.py:305` | Regex HIGH (sumaríssimo/ordinário) | ~90% | **Conectado** — sobrescreve IA |
| `data_ajuizamento` | `pre_extractor.py:314` | Regex MEDIUM | ~80% | **Conectado** — âncora no prompt |
| `data_admissao` | `pre_extractor.py:321` | Regex MEDIUM | ~80% | **Conectado** — âncora no prompt |
| `data_demissao` | `pre_extractor.py:328` | Regex MEDIUM | ~80% | **Conectado** — âncora no prompt. Falha em "dispensado sem justa causa em DD/MM" (não adjacente) |
| `salario_base` | `pre_extractor.py:335` | Regex MEDIUM + heurística de moda | ~75% | **Conectado** — âncora no prompt |
| `indice_correcao` | `pre_extractor.py:363` | Regex MEDIUM (IPCA-E/SELIC/TR/ADC 58) | ~85% | **Conectado** — âncora no prompt |
| `juros_mora` | `pre_extractor.py:382` | Regex MEDIUM | ~80% | **Conectado** — âncora no prompt |
| `motivo_rescisao` | `pre_extractor.py:390` | Regex MEDIUM | ~85% | **Conectado** — âncora no prompt |
| `tipo_contrato` | `pre_extractor.py:402` | Regex MEDIUM | ~75% | **Conectado** — âncora no prompt |
| `divisor_horas` | `pre_extractor.py:410` + `processor.py:279` | Regex MEDIUM + derivação pós-IA | ~80% | **Conectado** — âncora no prompt + derivação pós-IA |
| `aviso_previo_dias` | `pre_extractor.py:425` | Regex MEDIUM (20–90 dias) | ~80% | **Conectado** — âncora no prompt |
| `prescricao_quinquenal` | `processor.py:267` | Calculado: `data_ajuizamento - 5 anos` | ~95% | Depende de `data_ajuizamento` — se esse falhar, este também falha. |
| `jornada_contratual` | `processor.py:236` | Derivação de `horario_trabalho` (regex pós-IA) | ~70% | Regex para derivação `HH às HH com X horas` só funciona em padrão específico. Alternativa: campo direto pela IA. |
| `fgts_periodo_completo` | `processor.py:259` + Gemini | Derivação pós-IA + IA | ~85% | Quando genérico ("todo o contrato"), completa com datas reais. Funciona. |
| `evolucao_salarial` | `processor.py:311` | Valor padrão se salário extraído | ~60% | Apenas preenche `"Salário fixo reconhecido: R$ X"` — não captura evolução real. |
| `reclamante` | `ai_client.py:126` (prompt Gemini) | IA (Flash → Pro) | ~85% | Confunde autor/reclamante em acórdãos com múltiplos recorrentes. |
| `reclamada` | `ai_client.py:126` | IA | ~80% | Múltiplas reclamadas (litisconsórcio) frequentemente omitem uma das partes. |
| `vara_trabalho` | `ai_client.py:126` | IA | ~85% | Geralmente bem extraído; falha em acórdãos sem cabeçalho. |
| `funcao_reclamante` | `ai_client.py:126` | IA | ~65% | Alta taxa de null — função não mencionada explicitamente na sentença. |
| `horario_trabalho` | `ai_client.py:126` | IA | ~75% | Texto livre varia muito; nem sempre inclui intervalo. |
| `advogado_reclamante` | `ai_client.py:126` | IA | ~70% | **FASE M**: instrução de desambiguação adicionada (FASE J+M). Confusão com advogado da reclamada reduzida. |
| `advogado_reclamada` | `ai_client.py` | IA | novo | **FASE J**: campo adicionado ao schema (v2.6), prompt e playbooks. Instrução de desambiguação em FASE M. |
| `juiz_responsavel` | `ai_client.py:126` | IA | ~80% | Bom em sentenças; falha em acórdãos (múltiplos desembargadores). |
| `verbas_deferidas[]` | `ai_client.py:126` | IA (lista de objetos) | ~80% | **Principal fonte de inconsistência.** Omissão de verbas, duplicação, `status_final` null. |
| `verbas[].valor_fixado` | `ai_client.py:126` | IA | ~65% | Alta taxa de null. Valor raramente aparece por verba na sentença (aparece apenas no total). |
| `verbas[].base_calculo` | `ai_client.py:126` | IA | ~60% | Baixa precisão — IA frequentemente inventa a base de cálculo. |
| `verbas[].reflexos` | `ai_client.py:126` | IA | ~70% | IA às vezes lista reflexos não deferidos explicitamente. |
| `dano_moral` | `ai_client.py:126` | IA | ~85% | Razoável. Valor numérico pode vir sem `R$`. |
| `dano_material` | `ai_client.py:126` | IA | ~80% | |
| `multa_art_467` | `ai_client.py:126` | IA | ~80% | |
| `multa_art_477` | `ai_client.py:126` | IA | ~80% | |
| `honorarios_sucumbenciais` | `ai_client.py:126` | IA | ~75% | Percentual às vezes omitido. |
| `contribuicao_previdenciaria` | `ai_client.py:126` | IA | ~70% | Texto descritivo variado. |
| `ir_retido_fonte` | `ai_client.py:126` | IA | ~65% | Alta taxa de null ou texto genérico. |
| `fgts_sobre_aviso_previo` | `ai_client.py:126` | IA | ~70% | Instrução específica no prompt; frequentemente null quando não explícito. |
| `fgts_multa_40_aviso_previo` | `ai_client.py:126` | IA | ~70% | Idem. |
| `fgts_sobre_ferias_indenizadas` | `ai_client.py:126` | IA | ~70% | Idem. |

---

## Resumo Executivo

| Camada | Campos cobertos | Status |
|--------|----------------|--------|
| **Regex HIGH** (pre_extractor) | 4 campos | Implementado mas **desconectado** |
| **Regex MEDIUM** (pre_extractor) | 10 campos | Implementado mas **desconectado** |
| **Derivação pós-IA** (processor.py) | 5 campos | Funcionando |
| **Gemini** (ai_client.py) | ~20 campos | Funcionando mas cobre campos que poderiam ser regex |

**Ação prioritária:** reconectar `pre_extractor` ao `processor.py` — correção de 2 linhas que elimina chamadas de IA redundantes para 14 campos.
