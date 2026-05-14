# GEMINI_CALLS_INVENTORY.md — Inventário de Chamadas ao Gemini

> Gerado em: 2026-05-13

---

## Resumo

| # | Arquivo | Linha | Propósito | Substituível por Python? |
|---|---------|-------|-----------|--------------------------|
| 1 | `ai_client.py` | 286 | Extração principal de todos os campos | **Parcial** — 14 campos já têm regex no pre_extractor (desconectado) |
| 2 | `ai_client.py` | 459 | Geração do texto "I. PARCELAS APURADAS" do parecer | Não — geração de texto jurídico contextual |
| 3 | `ai_writer.py` | 114 | Geração da Manifestação aos Cálculos (Word) | Não — redação jurídica com estilo mapeado |
| 4 | `learning_engine.py` | 833 | Núcleo — usado por 8 funções do Laboratório (ver abaixo) | Parcial por função |

---

## Detalhamento

### 1. `backend/services/ai_client.py` — Extração principal

**Função:** `_call_model()` → chamada por `extract_data_with_gemini()`  
**Linha:** 286 (`client.models.generate_content(...)`)  
**Modelos:** `gemini-2.5-flash` → `models/gemini-2.5-pro` (cascata em caso de falha)  
**O que pede:** Extração de TODOS os ~40 campos do processo em um único prompt (~4000–15000 chars)  
**Frequência:** 1× por PDF processado (extrator principal)

**Substituível?** PARCIAL.

- **14 campos já têm regex funcional** em `pre_extractor.py` mas estão desconectados do pipeline (ver `EXTRACAO_STATUS.md`).
- Reconectar o pre_extractor elimina chamadas redundantes para: `numero_processo`, `data_sentenca`, `justica_gratuita`, `tipo_rito`, `data_ajuizamento`, `data_admissao`, `data_demissao`, `salario_base`, `indice_correcao`, `juros_mora`, `motivo_rescisao`, `tipo_contrato`, `divisor_horas`, `aviso_previo_dias`.
- Os ~20 campos restantes (nomes das partes, verbas, valores) **necessitam de IA** — não são extraíveis de forma confiável com regex.

---

### 2. `backend/services/ai_client.py` — Parecer técnico

**Função:** `gerar_parcelas_parecer()`  
**Linha:** 459 (`client.models.generate_content(...)`)  
**Modelo:** `gemini-2.5-flash`  
**O que pede:** Texto da seção "I. PARCELAS APURADAS" no estilo pericial formal — uma linha por verba (`a) HORAS EXTRAS: Apuração...`)  
**Frequência:** 1× por extração bem-sucedida (gerado no pipeline principal)

**Substituível?** NÃO.

- A geração é criativa e contextual: depende do nome da verba, reflexos e percentual de cada item.
- Existe um template fixo em `explanation_engine.py` que gera textos similares sem IA — seria possível usar como fallback, mas a qualidade seria inferior ao padrão pericial.
- **Otimização possível:** usar `gemini-2.5-flash-lite` (mais barato) pois a tarefa não exige raciocínio complexo — apenas formatação de texto estruturado.

---

### 3. `backend/services/ai_writer.py` — Manifestação Word

**Função:** `gerar_texto_manifestacao()`  
**Linha:** 114 (`_client.models.generate_content(...)`)  
**Modelo:** `gemini-2.5-flash`  
**O que pede:** Texto completo da Manifestação aos Cálculos — introdução + seções por discrepância + tabela comparativa. Contexto: até 25.000 chars de estilo mapeado + lista de discrepâncias.  
**Frequência:** 1× por acionamento do endpoint `/lab/gerar-docx` (não é automático — usuário solicita)

**Substituível?** NÃO.

- Geração criativa de texto jurídico com tom específico da perita.
- O prompt injeta o arquivo `manifestacao_style.md` inteiro (até 25.000 chars).
- Ponto de atenção: prompt muito longo pode degradar qualidade. Considerar resumir o estilo em <5.000 chars.

---

### 4. `backend/services/learning_engine.py` — Laboratório (8 funções)

Todas as chamadas do Laboratório passam pela função interna `_chamar_gemini_para_codify()` na linha 816.  
Cascata: `models/gemini-2.5-pro` → `gemini-2.0-flash` (nota: `gemini-2.0-flash` está **depreciado**).

#### 4a. `_codify_regra_python()` — linha 924
**O que pede:** Gera código Python completo de uma nova `LegalRule` a partir de uma discrepância detectada pelo laboratório. Usa `gemini-2.5-pro` (modelo de raciocínio).  
**Substituível?** PARCIAL — o template de rascunho já existe em `preview_aprendizado()` (`learning_engine.py:540`). A parte substituível é o esqueleto; a lógica de condicionamento (`if/else`) precisa de IA.

#### 4b. `_codify_playbook_exemplo()` — linha 983
**O que pede:** Gera um bloco Markdown de exemplo few-shot para adicionar ao skill.  
**Substituível?** PARCIAL — poderia ser um template estático com os campos preenchidos, sem IA.

#### 4c. `_extrair_metadados_amostragem()` — linha 2060
**O que pede:** Analisa um "documento de amostragem" (proof document) e extrai: tipo, descrição, relevância jurídica, sugestão de argumento.  
**Substituível?** PARCIAL — tipo e relevância poderiam ser detectados via regex (Súmulas, OJs, CLT). Sugestão de argumento precisa de IA.

#### 4d. `_extrair_estilo_impugnacao()` — linha 2112
**O que pede:** Lê uma manifestação/impugnação DOCX e extrai: tom retórico, expressões-chave, padrões de ataque/defesa.  
**Substituível?** NÃO — análise semântica de estilo.

#### 4e. `_extrair_metadados_peticao()` — linha 2169
**O que pede:** Da petição inicial (PDF/DOCX): verbas pedidas, período reivindicado, valor da causa.  
**Substituível?** PARCIAL — verbas pedidas (regex de lista de verbas), valor da causa (regex monetário). Período precisa de IA.

#### 4f. `_extrair_metadados_contestacao()` — linha 2224
**O que pede:** Da contestação: argumentos de exclusão de verbas, teses defensivas.  
**Substituível?** PARCIAL — nomes de verbas contestadas via regex; argumentação precisa de IA.

#### 4g. `_gerar_logica_discrepancia_com_ia()` — linha 2594
**O que pede:** Gera a lógica Python (`if` + `self._alerta()`) para identificar uma discrepância automaticamente em futuras sentenças. Entrada: lista de discrepâncias filtradas.  
**Substituível?** NÃO — geração de código inteligente contextual.

#### 4h. `_extrair_metadados_impugnacao()` — linha 2816
**O que pede:** Da impugnação da empresa: calculos contestados, teses técnicas, valores divergentes.  
**Substituível?** PARCIAL — valores monetários e referências jurídicas via regex; argumentação precisa de IA.

---

### 5. `backend/services/learning_engine.py` — Extração de sentença no Lab

**Funções:** `_extrair_sentenca()` linha 103, `_extrair_documento_generico()` linha 1374, `_extrair_titulo_executivo()` linha 1744  
**O que pede:** Reutiliza `extract_data_with_gemini()` (mesma função do pipeline principal) para extrair campos de PDFs no contexto do Laboratório.  
**Frequência:** Múltiplas vezes durante `processar_sete_arquivos()` — até 3 chamadas por sessão de laboratório.

**Substituível?** PARCIAL.  
**Risco adicional:** Estas chamadas **não verificam cache** e **não debitam créditos**, podendo causar uso de API não contabilizado. Também chamam `extract_data_with_gemini()` para documentos DOCX convertidos para texto, onde a qualidade da extração é inferior (sem pdfplumber).

---

## Chamadas Obsoletas

- `learning_engine.py:828`: cascata inclui `gemini-2.0-flash` que está **depreciado**. Substituir por `gemini-2.5-flash`.

---

## Custo Estimado por Operação

| Operação | Chamadas Gemini | Modelo | Custo est. (USD) |
|----------|----------------|--------|-----------------|
| Extração de PDF (pipeline principal) | 1–2 (Flash + Pro fallback) | 2.5-flash / 2.5-pro | ~$0.01–0.05 |
| Extração + parecer completo | 2–3 | 2.5-flash | ~$0.02–0.08 |
| Laboratório completo (7 arquivos) | 5–10 | 2.5-pro (maioria) | ~$0.50–2.00 |
| Gerar manifestação Word | 1 | 2.5-flash | ~$0.03–0.10 |

*Estimativas baseadas em volumes típicos de texto jurídico (~5.000–15.000 tokens por chamada.*
