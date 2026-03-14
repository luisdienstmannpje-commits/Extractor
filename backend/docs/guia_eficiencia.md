# Guia de Eficiência — Motor de IA e Diretrizes de Prompt

> Documento interno de referência para engenharia de prompt e regras de análise jurídica.
> Atualizado em: 2026-03-13

---

## 1. Título Executivo Complexo — Múltiplos Documentos Decisórios

O Card 3 do Laboratório aceita **múltiplos arquivos** (Sentença + Acórdão TRT/RO + Acórdão TST/RR) para compor o **Título Executivo Complexo**. O sistema realiza automaticamente a **Análise de Reforma de Decisão**.

### Classificação automática de instâncias

O sistema detecta o nível hierárquico pelo nome do arquivo:

| Padrão no nome           | Instância detectada |
|--------------------------|---------------------|
| `tst`, `rr`, `recurso_de_revista` | TST / Recurso de Revista |
| `trt`, `ro`, `acórdão`, `recurso_ordinario` | TRT / Recurso Ordinário |
| Outros                   | 1º Grau             |

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
| 1    | Amostragem PDF             | `.pdf`                 | Holerites / cartões de ponto              |
| 2    | Amostragem Word            | `.docx`                | Style transfer de linguagem                |
| 3    | **Título Executivo**       | `.pdf`, `.docx`        | **Múltiplos arquivos** — acumula instâncias |
| 4    | Liquidação                 | `.pdf`, `.docx`        | Cálculo da empresa                        |
| 5    | Parecer                    | `.pdf`, `.docx`        | Correção da perita                        |
| 6    | Impugnação                 | `.pdf`, `.docx`        | Contestação — Style Transfer              |
| 7    | Cálculo PJC                | `.pdf`, `.docx`, `.pjc` | Parâmetros PJe-Calc                       |
| 8    | Manifestação               | `.pdf`, `.docx`        | Retórica de combate — Style Transfer      |

> **Atenção:** arquivos `.doc` (Word 97–2003) **não são suportados**. Converta para `.docx` antes de fazer upload.

---

## 7. Dicas de Nomenclatura para Classificação Automática

Para que o sistema classifique corretamente a instância, use palavras-chave no nome do arquivo:

- **TST:** inclua `tst`, `rr` ou `recurso_de_revista` no nome.
- **TRT:** inclua `trt`, `ro`, `acordao` ou `recurso_ordinario` no nome.
- **1º Grau:** qualquer outro nome é classificado como 1º grau (padrão).

Se o arquivo não tiver essas palavras-chave, o sistema processará igualmente, mas a badge visual e o log mostrarão "📄 1º Grau".
