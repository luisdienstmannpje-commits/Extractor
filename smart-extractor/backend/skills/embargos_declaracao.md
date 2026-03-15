# Skill: Leitura de Embargos de Declaração

## Quando usar esta skill
O documento é uma **decisão em embargos de declaração** (1ª instância ou TRT).
Palavras-chave: "embargos de declaração", "embargante", "embargado",
"omissão", "contradição", "obscuridade", "erro material",
"efeito infringente", "acolho os embargos", "rejeito os embargos".

## O que são e para que servem

Embargos de declaração são recurso para corrigir **omissão, contradição, obscuridade ou erro material**
na sentença ou acórdão. Não rediscutem o mérito — mas podem, excepcionalmente, alterar o resultado
quando acolhidos **com efeito infringente**.

---

## Estratégia de extração — 3 casos possíveis

### Caso 1: Embargos REJEITADOS
**O que muda:** Nada. A sentença/acórdão original permanece integralmente.

**Como registrar:**
- `verbas_deferidas`: lista vazia (nenhuma alteração)
- `observacoes` da primeira verba (se necessário): `"Embargos de declaração rejeitados — sentença mantida integralmente"`
- Não alterar nenhum campo de parâmetro (salário, índice, datas)

**Frases-gatilho:**
- "rejeito os embargos de declaração"
- "não conheço dos embargos" (intempestivos ou sem fundamento)
- "nego provimento aos embargos"

---

### Caso 2: Embargos ACOLHIDOS sem efeito infringente (esclarecimento apenas)
**O que muda:** O juiz apenas esclareceu algo — não alterou o resultado da condenação.

**Como registrar:**
- `status_final` das verbas: `"mantida"` (inalterada)
- Registrar o esclarecimento no campo específico que foi objeto dos embargos
- Ex: Se os embargos esclareceram o índice → atualizar `indice_correcao` com o texto esclarecido

**Frases-gatilho:**
- "acolho os embargos para sanar omissão quanto a..."
- "esclareço que..."
- "integro o acórdão com a seguinte complementação..."
- "para fins de prequestionamento, esclareço que..."

**Exemplos de esclarecimentos comuns:**
- Esclarecimento sobre o índice de correção: atualizar `indice_correcao`
- Esclarecimento sobre período do FGTS: atualizar `fgts_periodo_completo`
- Esclarecimento sobre reflexos de uma verba: atualizar `reflexos` da verba correspondente
- Esclarecimento sobre aviso prévio proporcional: atualizar `aviso_previo_dias`

---

### Caso 3: Embargos ACOLHIDOS com efeito infringente (⚠️ alteração de resultado)
**O que muda:** Há mudança concreta na sentença — resultado mais grave.

**Como registrar:**
- `status_final` das verbas alteradas: `"reformada"`, `"excluída"` ou `"acrescida"`
- Atualizar os campos correspondentes (período, percentual, base_calculo, valor_fixado)
- `observacoes` da verba: descrever exatamente o que mudou
  - Ex: `"Embargos acolhidos com efeito infringente — período reduzido de 01/2020-12/2022 para 06/2020-12/2022"`

**Frases-gatilho:**
- "acolho os embargos com efeito infringente para..."
- "dou efeito modificativo aos embargos..."
- "reconsidero a sentença/acórdão para..."

---

## Campos de extração neste documento

- `data_sentenca`: data **desta decisão dos embargos** (não da sentença original)
- `juiz_responsavel`: juiz/desembargador que julgou os embargos (pode ser diferente)
- `numero_processo`: mesmo número CNJ do processo originário
- `justica_gratuita`: se os embargos esclareceram ou alteraram este ponto
- Demais campos: atualizar **apenas** os que foram modificados ou esclarecidos pelos embargos

---

## Verbas a listar

- **Embargos rejeitados**: listar com `status_final: "mantida"` e uma observação geral, ou lista vazia
- **Embargos acolhidos sem efeito infringente**: listar apenas as verbas **objeto do esclarecimento**
- **Embargos acolhidos com efeito infringente**: listar as verbas **alteradas** com novo status e campos

---

## Honorários nos embargos (art. 85, §11 CPC)

Se o juiz condenar em honorários pelo julgamento dos embargos (embargos protelatórios):
- Registrar em `percentual_honorarios`: percentual fixado nos embargos
- Registrar em `observacoes`: `"Honorários adicionais de X% fixados nos embargos de declaração — art. 85, §11 CPC"`
- **Não sobrescrever** os honorários da sentença originária

---

## Prequestionamento — atenção especial

Embargos opostos "para fins de prequestionamento" indicam que a parte quer recorrer ao TST/STF:
- Não alteram o resultado da sentença/acórdão atual
- Geralmente acolhidos apenas para complementar a fundamentação
- Registrar em `observacoes`: `"Embargos acolhidos para fins de prequestionamento — resultado da sentença inalterado"`

---

## Embargos de ambas as partes

Quando ambas as partes embargam, analisar **separadamente**:
1. Embargos da reclamante → em geral buscam incluir/ampliar verbas
2. Embargos da reclamada → em geral buscam excluir/reduzir verbas
3. Registrar o resultado de cada um e o resultado final combinado

---

## Armadilhas comuns

- **Acolhidos ≠ provimento total**: embargos podem ser acolhidos apenas parcialmente
- **Votos vencidos em acórdão de embargos**: ignorar completamente (como nos acórdãos normais)
- **Embargos de 2ª instância** (contra acórdão do TRT): combinar com `acordao.md`
  — a lógica de reforma/exclusão/acréscimo se aplica da mesma forma
- **Embargos intempestivos**: se "não conhecidos" por tempestividade, não há qualquer mudança
- **Recurso pendente**: a menção a "aguarda julgamento do recurso ordinário" não altera o resultado atual

---

## Resumo de decisão rápida por frase

| Frase no documento | O que fazer |
|---|---|
| "rejeito os embargos" | Lista vazia, nada muda |
| "acolho para sanar omissão" | Atualizar campo omitido, status "mantida" |
| "acolho para esclarecer" | Atualizar campo esclarecido, status "mantida" |
| "acolho com efeito infringente" | Atualizar verbas alteradas com novo status |
| "para fins de prequestionamento" | Registrar nota, nada muda no resultado |
| "não conheço dos embargos" | Lista vazia, nada muda |
| "condenar em honorários pelos embargos" | Registrar honorários adicionais em observacoes |