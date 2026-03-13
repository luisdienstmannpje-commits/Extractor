# Skill: Leitura de Despacho/Decisão de Execução

## Quando usar esta skill
O documento é um **despacho ou decisão em fase de execução** que define parâmetros
para cumprimento da sentença/acórdão já transitado em julgado.
Palavras-chave: "fase de execução", "cumpra-se", "expeça-se mandado",
"penhora", "bloqueio BACENJUD", "requisição de pagamento",
"RPV", "precatório", "planilha de débito", "atualize-se",
"intime-se a executada", "título executivo".

## O que este documento contém

Despachos de execução geralmente fixam:
1. **Parâmetros finais de atualização** — índice + período + taxa de juros definitivos
2. **Valor total da execução** — principal + atualização + juros + honorários + INSS
3. **Modalidade de pagamento** — RPV ou precatório
4. **Determinações processuais** — penhora, bloqueio BACENJUD, intimações, prazo de pagamento

---

## Campos prioritários

### Parâmetros de cálculo (definitivos para esta execução)

- `indice_correcao`: índice determinado nesta fase — pode ter sido **atualizado** pela jurisprudência do STF
  - Buscar referência à ADC 58, Tema 1.191 STF, IPCA-E, SELIC, TR
  - Este é o índice **definitivo** para a execução — prevalece sobre a sentença se houve atualização

- `juros_mora`: taxa vigente para esta execução
  - Buscar: "juros de mora de 1% ao mês", "SELIC", "taxa SELIC acumulada"

- `data_sentenca`: data deste despacho/decisão de execução

- `contribuicao_previdenciaria`: determinação específica para o pagamento
  - Buscar: "recolher INSS no prazo de X dias", "guia GPS", "recolhimento patronal e do empregado"
  - Buscar: prazo para recolhimento após o pagamento

- `ir_retido_fonte`: responsável e prazo determinados para esta execução

### Valor da execução

Se o despacho mencionar ou homologar o valor total:
- Registrar em `observacoes` da **primeira verba**:
  ```
  "Valor total da execução: R$ X.XXX.XXX,XX
   Principal: R$ X.XXX,XX | Correção: R$ X.XXX,XX | Juros: R$ X.XXX,XX | FGTS: R$ X.XXX,XX | INSS: R$ X.XXX,XX"
  ```

### FGTS na execução

- `fgts_periodo_completo`: período **definitivo** de apuração — pode ter sido reduzido por prescrição
- `fgts_observacoes`: guias pendentes, prazo de recolhimento, banco depositário

---

## RPV vs Precatório — modalidade de pagamento

Identificar a modalidade e registrar em `observacoes` da primeira verba:

| Situação | Registro |
|---|---|
| Valor ≤ 60 salários mínimos (pessoa em geral) | `"Pagamento via RPV — prazo: 60 dias"` |
| Valor ≤ 40 salários mínimos (alimentar/idoso) | `"Pagamento via RPV prioritário — prazo: 60 dias"` |
| Valor > 60 salários mínimos | `"Pagamento via Precatório — expedição determinada"` |
| Valor renunciado pelo credor para entrar no teto de RPV | `"RPV por renúncia ao excedente — art. 100, §3º CF"` |

---

## Verbas neste documento

Nesta fase, as verbas **já foram definidas** pela sentença/acórdão. Foque em:

- Registrar verbas **excluídas por prescrição intercorrente**:
  - `status_final: "excluída"`
  - `observacoes: "Excluída por prescrição intercorrente — art. 11-A CLT"`

- Registrar verbas com **valor final fixado** pelo juiz (se calculou diretamente):
  - `status_final: "homologada"`
  - `valor_fixado`: valor calculado pelo juiz

- Registrar verbas com **período reduzido** por prescrição ou bloqueio:
  - `status_final: "corrigida"`
  - `periodo`: período definitivo
  - `observacoes`: motivo da redução

- Se **nenhuma verba foi alterada** neste despacho: lista vazia ou não preencher

---

## Prescrição intercorrente — regras específicas

Art. 11-A CLT: prescrição de 2 anos em caso de paralisação da execução por inércia do exequente.

Como identificar no despacho:
- "declaro a prescrição intercorrente"
- "processo ficou paralisado por mais de 2 anos"
- "inércia do exequente por período superior a 2 anos"
- Verificar se foi declarada de ofício (pelo juiz) ou por provocação da executada

Como registrar:
```
{
  "nome": "Crédito trabalhista integral",
  "status_final": "excluída",
  "periodo": null,
  "observacoes": "Extinto por prescrição intercorrente — art. 11-A CLT
                  Período de paralisação: DD/MM/AAAA a DD/MM/AAAA"
}
```

---

## BACENJUD / SISBAJUD — penhora eletrônica

Se o despacho determinar penhora eletrônica (bloqueio em conta bancária):
- Registrar em `observacoes` da primeira verba: `"Penhora eletrônica determinada — SISBAJUD"`
- Se houver valor específico de penhora: incluir o valor
- Isso é útil para o perito calcular eventual saldo devedor após penhora parcial

---

## Custas na execução

**Atenção:** as custas da fase de execução são diferentes das custas da sentença.
- **Custas de execução**: geralmente 2% sobre o valor da execução (CLT art. 789)
- **Não sobrescrever** `custas_processuais` se já preenchido com custas da sentença
- Registrar custas de execução em `observacoes` da primeira verba se mencionadas:
  `"Custas de execução: 2% sobre R$ X.XXX,XX = R$ XXX,XX"`

---

## Honorários advocatícios na execução

Se o juiz fixar honorários adicionais para a fase de execução (art. 827 CPC):
- Percentual geralmente entre 5% e 15%
- Registrar em `percentual_honorarios` se for diferente do fixado na sentença
- `observacoes`: `"Honorários da fase de execução: X% — art. 827 CPC"`

---

## Armadilhas comuns

- **Valores "antes de atualização"**: despacho pode citar valores históricos da condenação
  — usar sempre o valor **atualizado** mais recente quando disponível
- **"Homologa-se o cálculo de R$ X"** pode ser provisório se houver impugnação pendente
  — verificar se o despacho é definitivo ou sujeito a impugnação
- **Índice atualizado pelo STF**: se o STF alterou o índice após a sentença (ADC 58),
  o despacho de execução deve usar o índice novo — prevalece sobre o índice da sentença
- **Múltiplos réus** (litisconsórcio passivo): verificar se há solidariedade ou se cada um responde separadamente
- **Execução parcial** (só verbas não pagas): não confundir com execução integral

---

## Resumo de ações por tipo de despacho

| Tipo de despacho | Campos a atualizar |
|---|---|
| "Atualize-se pelos índices e expeça-se RPV" | `indice_correcao`, `juros_mora`, modalidade em `observacoes` |
| "Homologa-se cálculo de R$ X" | valor em `observacoes` da 1ª verba |
| "Declaro prescrição intercorrente" | verbas com `status_final: "excluída"` |
| "Determino penhora de R$ X via SISBAJUD" | penhora em `observacoes` |
| "Expeça-se precatório" | modalidade em `observacoes` |
| "Intime-se para pagamento em 48h" | modalidade RPV em `observacoes` |