# Skill: Leitura de Decisão em Cálculos de Liquidação

## Quando usar esta skill
O documento é uma **decisão em fase de liquidação/execução**, que homologa ou impugna
os cálculos apresentados pelas partes. Não é uma sentença de conhecimento nova.
Palavras-chave: "fase de liquidação", "homologação de cálculos", "cálculos apresentados pela contadoria",
"impugnação aos cálculos", "despacho de liquidação", "decisão de liquidação", "título executivo".

## O que este documento É e NÃO É

✅ **É:** decisão que valida, corrige ou rejeita cálculos sobre verbas JÁ deferidas na sentença/acórdão.
❌ **NÃO É:** sentença nova que defere verbas — o que foi deferido está na sentença/acórdão original.

---

## Estratégia de extração

A sentença/acórdão original já definiu as verbas. Esta decisão de liquidação **modifica parâmetros**:
corrige índice de atualização, altera período de apuração, define base de cálculo controversa, fixa valor final homologado.

### Campos prioritários neste documento

- `data_sentenca`: data **desta decisão de liquidação** (não da sentença originária)
- `numero_processo`: mesmo número CNJ do processo originário
- `juiz_responsavel`: juiz desta decisão (pode ser diferente do da sentença)
- `indice_correcao`: índice que foi **confirmado ou alterado** — este é o definitivo para os cálculos
- `juros_mora`: juros confirmados ou corrigidos nesta fase
- `salario_base`: valor **homologado** pelo juiz — pode ter sido corrigido em relação à sentença
- `fgts_periodo_completo`: período **homologado** para apuração do FGTS
- `contribuicao_previdenciaria`: determinação de recolhimento conforme esta decisão

### Verbas na liquidação

As verbas listadas aqui são aquelas cujos **cálculos foram discutidos** nesta fase.
Para cada verba com discussão específica na decisão:

- `status_final`:
  - `"homologada"` → cálculo aceito pelo juiz
  - `"corrigida"` → cálculo foi alterado pelo juiz (valor diferente do apresentado)
  - `"excluída"` → impugnação acolhida, verba removida dos cálculos
  - `"mantida"` → verba não discutida, manter como na sentença originária

- `periodo`: usar o período **homologado**, que pode diferir da sentença originária
- `base_calculo`: registrar a base **fixada pelo juiz** nesta decisão
- `valor_fixado`: se o juiz fixou valor específico nesta decisão de liquidação
- `observacoes`: registrar a divergência e como foi resolvida.
  Ex: "Contadoria calculou R$ 5.200,00; juiz homologou R$ 4.800,00 por discordância na base de cálculo"

### Valor total homologado

Se o juiz fixar ou homologar um valor total, registrar em `observacoes` da **primeira verba**:
- `"Valor total homologado: R$ X.XXX,XX (principal R$ X + juros R$ X + FGTS R$ X)"`

---

## Índice de correção — atenção especial

Esta é frequentemente a principal matéria controvertida nas liquidações trabalhistas.
Buscar explicitamente qual índice foi adotado ou confirmado:

- **IPCA-E + SELIC** (ADC 58/STF): IPCA-E para créditos pré-ajuizamento + SELIC pós-ajuizamento
  - Gatilhos: "ADC 58", "Tema 1.191 do STF", "IPCA-E até o ajuizamento, SELIC a partir de"
  - Registrar: `"IPCA-E (pré-ajuizamento) / SELIC (pós-ajuizamento) — ADC 58/STF"`

- **SELIC** (determinação do STF pós-ADC 58):
  - Gatilhos: "SELIC desde a data do ajuizamento", "índice único SELIC"

- **TR** (contratos anteriores à ADC 58 — verificar data):
  - Gatilhos: "TR", "UFIR", "índice anterior ao STF"

Se houve impugnação ao índice e o juiz decidiu, registrar expressamente qual índice prevaleceu.

---

## FGTS e INSS na liquidação

- `fgts_periodo_completo`: período de apuração **homologado** — pode ter sido reduzido por prescrição
- `contribuicao_previdenciaria`: o juiz pode ter fixado prazo e responsável específico nesta fase
  - Buscar: "recolhimento das contribuições previdenciárias no prazo de X dias"
  - Buscar: "guia GPS", "guia de recolhimento ao FGTS", "DARF"

---

## Perito contábil na liquidação

Se a decisão homologar ou discutir laudo de perito contábil nomeado:
- Registrar em `observacoes` da verba pertinente: `"Conforme laudo pericial de DD/MM/AAAA"`
- Honorários de perito: **não confundir** com honorários advocatícios
  - Honorários de perito → registrar em `custas_processuais` como observação adicional
  - Honorários advocatícios → campo `honorarios_sucumbenciais` / `percentual_honorarios`

---

## Impugnação aos cálculos — como registrar

Identificar quem impugnou (reclamante, reclamada ou ambos) e o resultado:

| Situação | Como registrar |
|---|---|
| Impugnação da reclamada acolhida | `status_final: "corrigida"` + observacoes com o motivo |
| Impugnação da reclamada rejeitada | `status_final: "homologada"` + observacoes "Impugnação rejeitada" |
| Impugnação do reclamante acolhida | `status_final: "corrigida"` com valor aumentado |
| Ambas rejeitadas | `status_final: "homologada"` |
| Cálculo aprovado sem impugnação | `status_final: "homologada"` |

---

## Prescrição intercorrente (art. 11-A CLT)

Se a decisão mencionar prescrição intercorrente (paralisação > 2 anos na execução):
- Verbas atingidas: `status_final: "excluída"`
- `observacoes`: `"Excluída por prescrição intercorrente — art. 11-A CLT — paralisação de X anos"`
- Verificar se a prescrição foi declarada de ofício ou por provocação da parte

---

## Armadilhas comuns nesta fase

- **Não confundir** os cálculos apresentados pelas partes (que podem ser rejeitados)
  com os valores homologados pelo juiz — usar SEMPRE os homologados
- **"Impugnação acolhida em parte"** — registrar o que foi acolhido e o que foi mantido separadamente
- A decisão pode remeter a laudo de perito contábil — registrar `"Conforme laudo pericial"` na base_calculo
- **Valor de liquidação ≠ valor da condenação original** — inclui atualização monetária e juros
- Custas da fase de liquidação (ex: honorários de perito) ≠ custas da sentença originária
- Se houver recurso pendente (agravo, recurso ordinário), os cálculos podem ser provisórios

---

## Campos específicos desta fase — resumo de prioridade

| Campo | Prioridade | O que buscar |
|---|---|---|
| `indice_correcao` | 🔴 Alta | Índice confirmado ou alterado — definitivo para os cálculos |
| `salario_base` | 🔴 Alta | Valor homologado para a base de cálculo |
| `fgts_periodo_completo` | 🔴 Alta | Período homologado — pode ter sido reduzido |
| `juros_mora` | 🟡 Média | Confirmar taxa vigente |
| `contribuicao_previdenciaria` | 🟡 Média | Prazo e responsável pelo recolhimento |
| `data_sentenca` | 🟡 Média | Data desta decisão (não da sentença originária) |
| `verbas_deferidas` | 🟡 Média | Apenas verbas com discussão específica nesta decisão |
| `custas_processuais` | 🟢 Baixa | Honorários de perito se mencionados |