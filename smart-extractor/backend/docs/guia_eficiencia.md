# Guia de Eficiência — Motor de IA e Diretrizes de Prompt

> Documento interno de referência para engenharia de prompt e regras de análise jurídica.
> Atualizado em: 2026-03-13

---

## Guia de Eficiência do Aprendizado

Nenhum arquivo é obrigatório. A IA aceita qualquer combinação, mas aprende melhor seguindo a marcha processual real. A cada arquivo adicionado, o sistema recalcula automaticamente a previsão de eficiência.

### Níveis de Aprendizado

| Nível | Combinação | O que o sistema aprende |
|-------|-----------|------------------------|
| ⚡ Nível 1 — Rápido (25%+) | Processo + Parecer | Fundamentos jurídicos e estilo da perita |
| 🔍 Nível 2 — Auditoria (45%+) | Processo + Parecer + Liquidação | Discrepâncias entre sentença e cálculo da empresa |
| 📊 Nível 3 — Tríade (65%+) | Processo + Liquidação + Cálculo PJC | Detecção automática de omissões de parâmetros |
| 🏆 Nível 4 — Tríade de Ouro (85%+) | Todos os anteriores + Contestação + Manifestação | Máximo aprendizado de retórica de combate e regras preditivas |

### Ordem ideal de anexo (marcha processual)

Para que o sistema aprenda como um "cérebro jurídico", os documentos devem seguir a ordem cronológica real do processo — cada etapa responde à anterior:

**Fase de Conhecimento** (quem disse o quê e por quê):
1. **Petição Inicial (Card 1)** — verbas pedidas e causa de pedir
2. **Contestação (Card 2)** — argumentos de exclusão da empresa
3. **Título Executivo (Card 3)** — sentença + acórdãos TRT/TST (a lei do processo)

**Fase de Liquidação** (quanto vale e como calcular):
4. **Liquidação (Card 4)** — quanto a empresa calcula que deve
5. **Parecer Pericial (Card 5)** — quanto a perita diz que realmente deve
6. **Impugnação (Card 6)** — como a empresa ataca os cálculos da perita
7. **Cálculo PJC (Card 7)** — parâmetros reais do motor de cálculo
8. **Manifestação (Card 8)** — como a perita responde os ataques

### Card de Provas como hub único (Parecer + Amostragens + Manifestações)

Em vez de usar os Cards 5 (Parecer), 6 (Impugnação) e 8 (Manifestação) separadamente, o usuário pode anexar **todos** os documentos técnicos no **Card "Amostragens e Provas Adicionais"**. O sistema:

1. **Autoclassifica** cada arquivo por conteúdo: "Parecer Técnico", "Conclui-se", "Vem apresentar" → Parecer (fundamentos e style_transfer); tabelas, R$, meses → Amostragem (conferência centavo a centavo no .PJC); "Manifestação", "petição de resposta" → Manifestação.
2. **Preenche** internamente os slots de Parecer, Amostragem (PDF ou Word) e Manifestação quando os cards explícitos não foram enviados.
3. **Envia ao Gemini** o bloco `<AMOSTRAGENS_DA_PERITA>` com o prompt: *"Você recebeu uma pasta de documentos do Perito Assistente. Identifique qual arquivo é o Parecer e qual é a Amostragem. Use o Parecer para entender a estratégia de combate e a Amostragem para conferir os valores centavo por centavo no arquivo .PJC."*

**Fluxo recomendado:** Processo no Card 3, Cálculo PJC no Card 7, **todo o resto** (Parecer + Amostragem + Manifestação) no Card de Provas. A auditoria completa funciona como antes.

### Ghostwriter — Minuta da Manifestação (.docx)

Após a análise, se houver discrepâncias, o botão **"Gerar Minuta Word"** aparece. Ao clicar, o sistema envia o relatório para `POST /lab/gerar-docx`. O conteúdo de `skills/manifestacao_style.md` é enviado ao Gemini como **Instrução de Tom e Voz**, para que a IA imite o estilo da perita (ex.: "esperando haver se desincumbido do múnus", "vem, respeitosamente" — aprendido nos testes 5 e 6). O documento gerado contém: cabeçalho (Processo, Reclamante, Reclamada), título MANIFESTAÇÃO AOS CÁLCULOS, seções por discrepância (texto limpo, sem Markdown), tabela **Table Grid** (Valor apresentado pela empresa x Valor correto — destaque ao prejuízo financeiro) quando houver dados numéricos, e encerramento padrão "Pede Deferimento. [Cidade], [Data]." com espaço para assinatura do Perito Assistente. **Validação recomendada:** usar o Caso Victor Felipe (Teste 5) ou Caso Gustavo Henrique (Teste 10); conferir discrepância SELIC ou Horas Extras e o cabeçalho do .docx baixado.

### Pesos de cada documento no score de eficiência

| Documento | Peso | Justificativa |
|-----------|------|---------------|
| Título Executivo (Card 3) | 30% | Base obrigatória — a lei do processo |
| Parecer Pericial (Card 5) | 20% | Verdade técnica — maior insumo do KB |
| Liquidação (Card 4) | 15% | Fonte primária das discrepâncias |
| Cálculo PJC (Card 7) | 10% | Parâmetros reais do motor |
| Manifestação (Card 8) | 10% | Retórica de combate da perita |
| Contestação (Card 2) | 7% | Argumentos de exclusão da empresa |
| Impugnação (Card 6) | 5% | Style Transfer de defesa |
| Petição Inicial (Card 1) | 3% | Contexto dos pedidos originais |

---

## 0. PJe Timeline Extractor — Um PDF Integral no Card 3

Quando o usuário anexa **apenas um PDF** do processo completo (1º e 2º grau) no Card 3, o sistema ativa o **Fatiador Cronológico (PJe Timeline Extractor)**:

1. **Sumário PJe**: as primeiras 15 páginas são lidas para localizar o índice ("PARA ACESSAR O SUMÁRIO"); cada linha com nome de peça e número de página gera um mapeamento (petição inicial, contestação, sentença, liquidação, impugnação, parecer).
2. **Fallback âncoras**: se o sumário não for encontrado ou for ilegível, o código usa regex cirúrgico para identificar início (e fim quando aplicável) de cada peça no texto.
3. **Slots automáticos**: as peças encontradas dentro do PDF são usadas para preencher os dados de liquidação, parecer, impugnação, petição e contestação **se o usuário não tiver anexado** esses arquivos nos outros cards. A **Barra de Eficiência** soma os pesos das peças extraídas (ex.: Contestação encontrada = +7 pts).
4. **Log obrigatório**: no terminal, cada peça identificada é registrada, ex.: `[TIMELINE] Petição Inicial encontrada nas pág. 2 a 18. Contestação nas pág. 45 a 65.`

**Regra de ouro:** o pipeline do `processor.py` (extração de sentença única) **não é alterado**. O Timeline atua somente no fluxo `/lab/analisar`, antes da montagem do relatório.

---

## 1. Título Executivo Complexo — Múltiplos Documentos Decisórios

O Card 3 do Laboratório aceita **múltiplos arquivos** (Sentença + Acórdão TRT/RO + Acórdão TST/RR) para compor o **Título Executivo Complexo**. O sistema realiza automaticamente a **Análise de Reforma de Decisão**.

### Classificação automática de instâncias

**Prioridade absoluta ao nome do arquivo** (evita falso positivo pelo cabeçalho PJe "Tribunal Regional do Trabalho"):

| Padrão no nome do arquivo       | Instância detectada |
|---------------------------------|---------------------|
| `1grau`, `ATOrd`, `Sentenca`, `Sentença` | **1º Grau** (obrigatório) |
| `2grau`, `ROT`, `Acordao`, `Acórdão`      | **TRT / 2º grau** (obrigatório) |
| `tst`, `rr`, `recurso_de_revista`         | TST |
| Nome genérico                    | Usa texto após os primeiros 1000 chars (cabeçalho ignorado); só considera "Recurso Ordinário", "Relator:", "Acórdão" — nunca só "Tribunal Regional" do header. |

**Data usada na hierarquia:** a **linha** que contém "Data da Autuação" é removida antes da extração; usa-se a **data do julgamento/assinatura** (final do documento: "Data do Julgamento", "Assinado eletronicamente em", "Belo Horizonte, DD de mês de AAAA").

**Boas práticas de nomenclatura:**
- `sentenca_1grau_processo_12345.pdf`
- `acordao_trt_ro_12345.pdf`
- `acordao_tst_rr_12345.pdf`

---

## 2. Prioridade da Coisa Julgada — Hierarquia Processual

> **Diretriz obrigatória para análise de múltiplos documentos decisórios:**

A IA aplica a seguinte lógica de hierarquia ao analisar o Título Executivo Complexo:

1. **Sentença de 1º Grau** — ponto de partida; define verbas inicialmente deferidas.
2. **Acórdão TRT (Recurso Ordinário)** — reforma parcial ou total da sentença; prevalece sobre o 1º grau.
3. **Acórdão TST (Recurso de Revista)** — última instância ordinária; prevalece sobre TRT e 1º grau.

**Regra de ouro:**
> Verbas deferidas no 1º grau mas **reformadas no TRT/TST devem ser marcadas como `EXCLUÍDAS`** na auditoria do .PJC. O sistema insere essas verbas no campo `verbas_reformadas` do relatório para que o Motor de Auditoria não gere falsos positivos de "verba ausente".

---

## 3. Extração de Súmulas de Instância Superior — Peso Dobrado (RR/TST)

> **Diretriz de aprendizado e playbook:**

O sistema atribui **peso dobrado** às teses extraídas de documentos classificados como **Recurso de Revista (TST/RR)**, pois representam a **jurisprudência consolidada** que guia a uniformização do direito material.

Motivos:
- O RR só é admitido por violação de lei federal ou divergência jurisprudencial (art. 896 CLT).
- Os temas julgados pelo TST via RR geralmente culminam em **Súmulas** ou **Orientações Jurisprudenciais**, que têm efeito vinculante dentro da Justiça do Trabalho.
- Extrair o Style Transfer de um Acórdão TST enriquece o playbook com retórica de **altíssimo nível técnico**, baseada em linguagem de Súmula e precedente qualificado.

**Impacto no motor:**
- Padrões Ataque/Defesa extraídos de Acórdãos TST recebem score inicial `2` no Knowledge Base (dobrado em relação ao padrão `1`).
- Fundamentos jurídicos do TST alimentam diretamente o `manifestacao_style.md` com marcação `[TST/RR]`.

---

## 4. Guardrails de Falsos Positivos — Verba Ausente

Para evitar que o LLM alucine discrepâncias de "verba ausente":

1. **Canonização:** o nome da verba deferida é normalizado (`LegalRule._canonizar_verba`) antes de comparar com verbas da liquidação e do PJC.
2. **Filtro pós-resposta LLM:** discrepâncias e aprendizados com `tipo == "verba_ausente"` são filtrados programaticamente se a verba canonizada existir no cálculo da empresa.
3. **Filtro de hipóteses KB:** as hipóteses geradas para o Knowledge Base também passam pelo mesmo guardrail antes de serem salvas.

Regra de negócio:
> **Uma verba só é considerada "ausente" quando não há correspondência canonizada, por substring ou fuzzy (threshold ≥ 85%) no conjunto de verbas da liquidação + PJC.**

---

## 5. Duplo Style Transfer — Impugnação e Manifestação

O Card 6 (Impugnação) e o Card 8 (Manifestação) alimentam ambos o mesmo playbook de retórica:

- `skills/manifestacao_style.md` — recebe padrões de ataque/defesa dos dois documentos.
- Os resultados são **mesclados** (`_merge_dados_manifestacao`) sem duplicação.

Isso garante que o motor aprenda tanto a linguagem da contestação da empresa quanto a retórica de combate da perita.

---

## 6. Boas Práticas de Upload no Laboratório

| Card | Documento                  | Formatos aceitos       | Observação                                |
|------|----------------------------|------------------------|-------------------------------------------|
| 1    | Petição Inicial            | `.pdf`, `.docx`        | Verbas pedidas e causa de pedir           |
| 2    | Contestação                | `.pdf`, `.docx`        | Argumentos de exclusão da empresa        |
| 3    | **Título Executivo**       | `.pdf`, `.docx`        | **Múltiplos arquivos** — acumula instâncias |
| 4    | Liquidação                 | `.pdf`, `.docx`        | Cálculo da empresa                        |
| 5    | Parecer                    | `.pdf`, `.docx`        | Correção da perita                        |
| 6    | Impugnação                 | `.pdf`, `.docx`        | Contestação — Style Transfer              |
| 7    | Cálculo PJC                | `.pdf`, `.docx`, `.pjc` | Parâmetros PJe-Calc                       |
| 8    | Manifestação               | `.pdf`, `.docx`        | Retórica de combate — Style Transfer      |
| +    | **Amostragens e Provas Adicionais** | `.pdf`, `.doc`, `.docx` | **Múltiplos** — provas/tabelas; injetadas no prompt como `<AMOSTRAGENS_DA_PERITA>` (verdade de referência para confrontar cálculos) |

> **Atenção:** arquivos `.doc` (Word 97–2003) **não são suportados**. Converta para `.docx` antes de fazer upload.

---

## 7. Dicas de Nomenclatura para Classificação Automática

Para que o sistema classifique corretamente a instância, use palavras-chave no nome do arquivo:

- **TST:** inclua `tst`, `rr` ou `recurso_de_revista` no nome.
- **TRT:** inclua `trt`, `ro`, `acordao` ou `recurso_ordinario` no nome.
- **1º Grau:** qualquer outro nome é classificado como 1º grau (padrão).

Se o arquivo não tiver essas palavras-chave, o sistema processará igualmente, mas a badge visual e o log mostrarão "📄 1º Grau".
