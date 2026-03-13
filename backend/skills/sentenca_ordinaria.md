# Skill: Leitura de Sentença — Rito Ordinário e Sumaríssimo

## Quando usar esta skill
O documento é uma SENTENÇA de 1ª instância da Justiça do Trabalho.
Palavras-chave que identificam este tipo: "sentença", "juiz(a) do trabalho",
"vara do trabalho", "julgo procedente", "julgo improcedente", "julgo parcialmente".

## Estrutura esperada do documento
1. RELATÓRIO — identifica as partes e resume os pedidos
2. FUNDAMENTAÇÃO — o juiz analisa cada pedido
3. DISPOSITIVO — contém o que foi DEFERIDO ou INDEFERIDO (foco principal)

---

## Regras de extração

### Identificação do processo (Relatório)
- `numero_processo`: formato CNJ (ex: 0001234-56.2023.5.03.0001)
- `vara_trabalho`: nome completo da vara (ex: "2ª Vara do Trabalho de Belo Horizonte")
- `reclamante`: nome completo do trabalhador (autor)
- `reclamada`: nome completo da empresa (ré) — incluir CNPJ se mencionado
- `tipo_rito`: buscar "rito ordinário", "rito sumaríssimo" ou "procedimento sumaríssimo"
- `funcao_reclamante`: cargo ou função exercida, buscar "exercia a função de", "contratado como", "na função de"
- `advogado_reclamante`: nome do advogado do autor — buscar no cabeçalho ou assinatura da petição inicial
- `juiz_responsavel`: nome do juiz que assinou a sentença — buscar na assinatura digital ao final

### Datas (Relatório e Fundamentação)
- `data_sentenca`: data em que a sentença foi prolatada — buscar nesta ordem de prioridade:
  1. "Assinado digitalmente em DD/MM/AAAA" ou "Assinado em DD/MM/AAAA" (padrão PJe)
  2. "Publicado em DD/MM/AAAA"
  3. Data no cabeçalho ou rodapé do documento
  4. "Cidade, DD de mês de AAAA" ao final do texto
- `data_ajuizamento`: data do protocolo da petição inicial
- `data_admissao`: buscar "admitido em", "desde", "a partir de", "iniciou em"
- `data_demissao`: buscar "dispensado em", "rescisão em", "demitido em", "saiu em"
- `motivo_rescisao`: tipo da rescisão — buscar "sem justa causa", "pedido de demissão",
  "rescisão indireta", "término de contrato", "aposentadoria"
- `tipo_contrato`: natureza jurídica reconhecida — buscar "CLT", "pejotização", "pessoa jurídica",
  "CNPJ", "autônomo", "avulso". Se houve pejotização reconhecida, registrar "Pejotização reconhecida"

### Parâmetros financeiros (Fundamentação e Dispositivo)
- `salario_base`: último salário reconhecido pelo juiz — buscar:
  "salário de R$", "remuneração de R$", "percebia a importância de R$",
  "piso salarial de R$", "piso da categoria de R$", "salário normativo de R$",
  "salário contratual de R$", "remuneração mensal de R$", "vencimento de R$"
  Priorizar o valor reconhecido pelo juiz na fundamentação, não o alegado pelas partes.
- `jornada_contratual`: carga horária contratada — buscar "jornada de X horas", "44h semanais",
  "regime de X horas"
- `horario_trabalho`: horário de entrada, saída e intervalo RECONHECIDO PELO JUIZ na fundamentação —
  buscar "trabalhava das X às X", "jornada das X às X horas", "com intervalo de X"
  Formato esperado: "07h00 às 17h00 com 1h de intervalo"

### Parâmetros de cálculo (Dispositivo)
- `indice_correcao`: buscar "IPCA-E", "SELIC", "TR", "correção monetária pelo..."
- `juros_mora`: buscar "juros de 1% ao mês", "juros legais", "juros pela SELIC"
- `contribuicao_previdenciaria`: buscar "contribuições previdenciárias", "INSS", quem recolhe e quem
  desconta — registrar o texto completo da determinação
- `ir_retido_fonte`: buscar "imposto de renda", "IR na fonte", quem é responsável pelo recolhimento
- **Dedução / Compensação de valores pagos**: a IA **DEVE** procurar expressamente no dispositivo
  e na fundamentação se o juiz autorizou "dedução", "abatimento" ou "compensação" de valores já
  pagos a idêntico título (normalmente para evitar enriquecimento sem causa). Frases típicas:
  "Autorizo a dedução dos valores pagos a idêntico título", "Compensem-se os valores já pagos",
  "Abata-se o que já foi quitado". Se identificar essa autorização:
  - marcar `autorizada_deducao = true` no modelo `ProcessoTrabalhista`;
  - transcrever a redação relevante (ou o trecho mais claro) para `observacoes_deducao`
    (ex.: "Autorizada a dedução dos valores pagos a idêntico título para evitar enriquecimento sem causa.").

### Horas extras e adicionais — extração granular (Fundamentação e Dispositivo)
A IA **deve caçar obrigatoriamente** estes três aspectos para verbas de horas extras (e adicionais correlatos, ex.: adicional noturno, intervalo intrajornada), de forma a permitir parametrização precisa no PJe-Calc e no parecer da perita:

**1. Divisor de horas extras (incluindo variação no tempo)**
- Procurar expressões como: "divisor 120", "divisor 150", "divisor 180", "divisor 200", "divisor 220"; "conforme Súmulas 264 e 347 do TST", "observado o divisor X".
- **Se o juiz adotar divisores diferentes em períodos diferentes** (ex.: divisor 120 em um lapso e 180 em outro), extrair e registrar no campo `divisor_horas` **os dois valores**, no formato em que a sentença ou a perita utilizam: ex. `"120/180"` ou `"120 no período X e 180 no período Y"`. Não simplificar para um único número quando houver variação.
- Quando houver um único divisor, registrar em `divisor_horas` como string (ex.: `"180"`).

**2. Percentual aplicado (padrão constitucional vs. outro)**
- O **padrão constitucional** para horas extras é 50% (art. 7º, XVI, CF). A IA deve **sempre** extrair o percentual mencionado pelo juiz.
- Se o juiz fixar percentual **diferente** (ex.: 60%, 80%, 100%), registrar **explicitamente** no campo `percentual` da verba (ex.: `"60%"`). Não assumir 50% quando a sentença disser 60% ou outro valor.
- Buscar: "50%", "60%", "percentual de 60%", "adicional de 60%", "100%", "em dobro".

**3. Critério dos reflexos (média física, média duodecimal, valores efetivos)**
- Além da **lista** de reflexos deferidos (13º, férias, FGTS, DSR, aviso prévio), a IA deve **procurar ativamente** como os reflexos foram calculados — essa escolha altera o resultado no PJe-Calc (valor fixo vs. média). Buscar expressões como:
  - "reflexos **pela média**", "**pela média física**" (ou "média física sobre RSR", "média física sobre as parcelas");
  - "**média duodecimal**" (média das 12 últimas parcelas);
  - "**média aritmética**";
  - "**valores efetivamente pagos**" ou "valor fixo" (quando o juiz não adotar média);
  - "reflexos em **proporção**" ou "proporcionalmente".
- Registrar esse critério no campo `base_calculo` da verba, ou em `observacoes`, de forma clara (ex.: "Reflexos pela média física sobre RSR, aviso prévio, férias + 1/3, 13º salário e FGTS + 40%").
- Opcionalmente, detalhar no próprio array `reflexos` quando o critério for explícito (ex.: `"Aviso Prévio (pela média física)"`, `"13º salário (média duodecimal)"`), para que a perita e o sistema do tribunal identifiquem o critério por parcela.
- Para reflexos, o modelo deve produzir, por verba, um array `reflexos` contendo os itens mencionados; quando houver menção a "média física", "média duodecimal" ou critério análogo, incluir essa informação em `base_calculo` ou `observacoes` da mesma verba.

### Correção monetária e juros (ADC 58 e correlatos)
- Ler cuidadosamente os trechos que tratam de **correção monetária** e **juros de mora**, buscando especialmente:
  - "IPCA-E", "SELIC", "TR", "correção monetária pelo IPCA-E", "taxa SELIC";
  - menções à **ADC 58 do STF** e às decisões correlatas sobre índices de correção.
- Sempre que a sentença adotar o padrão da ADC 58, registrar em `indice_correcao` e `juros_mora` de forma estruturada, por exemplo:
  - `indice_correcao`: `"IPCA-E (fase pré-judicial) / SELIC (fase judicial)"`
  - `juros_mora`: `"1% ao mês até a citação, e posteriormente incluídos na taxa SELIC"`, se assim constar.
- Se o texto mencionar expressamente "Índices de correção monetária IPCA-E na fase pré-judicial e, a partir da citação, a incidência da taxa SELIC", capturar essa redação completa no campo correspondente, preservando o estilo técnico.

### Aviso prévio, CTPS e seguro-desemprego (Dispositivo)
- `aviso_previo_dias`: número total de dias do aviso prévio deferido — buscar "aviso prévio de X dias",
  "aviso prévio indenizado (X dias)". Incluir a proporcionalidade da Lei 12.506/2011 se aplicada.
  Registrar como string: "33 dias", "42 dias — 30 + 12 (Lei 12.506/2011)"
- `data_saida_ctps`: data de saída a ser anotada na CTPS considerando a projeção do aviso prévio —
  buscar "saída em DD/MM/AAAA", "projeção do aviso prévio", "OJ 82 da SDI-I do TST".
  Esta data é posterior à data real de demissão quando há aviso prévio indenizado.
- `anotacao_ctps`: se o juiz determinou anotação da CTPS — buscar "proceder à anotação",
  "anotar na CTPS", "registrar na CTPS". Registrar prazo e penalidade se mencionados.
  Ex: "Determinada — prazo 8 dias após trânsito em julgado, sob pena de multa"
- `seguro_desemprego`: resultado do pedido de seguro-desemprego — buscar "seguro-desemprego",
  "guias CD/SD", "indenização substitutiva". Possíveis valores:
  - "Guias CD/SD a serem entregues no prazo de X dias"
  - "Indenização substitutiva de R$ X (X parcelas de R$ Y)"
  - "Indeferido"
  - null se não foi pedido

### Regras especiais de FGTS (Dispositivo e Fundamentação)
Estes campos são críticos para o cálculo correto no PjeCalc:
- `fgts_sobre_aviso_previo`: registrar se o FGTS incide sobre o aviso prévio indenizado.
  Regra padrão: "Sim — FGTS incide sobre aviso prévio indenizado (Súm. 305 TST)"
  Buscar menção expressa à Súmula 305/TST ou OJ 42 SDI-I TST.
- `fgts_multa_40_aviso_previo`: registrar se a multa de 40% incide sobre o aviso prévio.
  Regra padrão: "Não — multa de 40% NÃO incide sobre aviso prévio (Súm. 305/OJ 42 TST)"
- `fgts_sobre_ferias_indenizadas`: registrar se o FGTS incide sobre férias indenizadas.
  Regra padrão: "Não — FGTS NÃO incide sobre férias indenizadas (OJ 195 SDI-1 TST)"
- `fgts_periodo_completo`: período total que o FGTS abrange — buscar "todo o período contratual",
  "desde DD/MM/AAAA". Registrar como "Todo o período contratual — DD/MM/AAAA a DD/MM/AAAA"
- `fgts_observacoes`: qualquer observação adicional sobre o FGTS — ex: se os depósitos nunca foram
  realizados (caso de pejotização), se há pendência de guias, valor aproximado se mencionado
- `honorarios_sucumbenciais`: quem paga — "reclamada", "reclamante", "ambas as partes (recíproca)"
- `percentual_honorarios`: percentual fixado — ex: "5%", "10%", "entre 5% e 15%"
- **Base de cálculo dos honorários sucumbenciais**: além do percentual, extraia obrigatoriamente **sobre o quê** o juiz aplicou o percentual. Buscar: "sobre o valor líquido da condenação (OJ 348 SDI-I TST)", "sobre o valor bruto", "sobre o proveito econômico". Preencher em `base_calculo_honorarios_sucumbenciais` ou no texto de `custas_processuais`/observações quando não houver campo específico. Ex.: "10% sobre o valor líquido da condenação — OJ 348".
- `justica_gratuita`: true se o juiz deferiu os benefícios da justiça gratuita ao reclamante
- `custas_processuais`: quem paga as custas e sobre qual valor foram calculadas (ex.: "Reclamada, R$ 200,00 calculadas sobre R$ 10.000,00")
- **Valor arbitrado à condenação**: no dispositivo, junto às custas, o juiz costuma arbitrar um valor provisório (ex.: "Custas de R$ 200,00, calculadas sobre R$ 10.000,00, valor arbitrado à condenação"). Extrair esse valor para o campo `valor_arbitrado_condenacao` (ex.: "R$ 10.000,00"). Auxilia a perita na escala do cálculo (custas 2% → valor arbitrado = custas / 0,02).

### Verbas indenizatórias de valor fixo (Dispositivo)
- `dano_moral`: valor em R$ fixado expressamente — buscar "dano moral de R$", "indenização por
  danos morais no valor de R$". NÃO incluir na lista de verbas_deferidas.
- `dano_material`: valor em R$ fixado — buscar "dano material", "dano emergente", "lucros cessantes"

### Limitação aos valores da inicial (Rito Sumaríssimo — IN 41/2018 TST)
- A IA **deve procurar obrigatoriamente** no texto se o juiz determinou:
  - **Limitação da condenação aos valores da inicial** (ex.: "a condenação fica limitada aos valores dos pedidos", "nos limites da inicial").
  - Ou se declarou que os valores da inicial são **mera estimativa** (ex.: "os valores indicados na inicial têm caráter estimativo", "aplicação da IN 41/2018 do TST").
- **Ação**: Extrair essa diretriz de forma clara no campo `limitação_valores_inicial` (ou em observações em destaque). Exemplos de preenchimento: "Condenação limitada aos valores da inicial"; "Valores da inicial são mera estimativa (IN 41/2018 TST)". Essa informação é crítica para o calculista: define se o valor apurado pode ultrapassar o pedido ou não.

### Honorários periciais (valor ou arbitragem)
- Se a sentença **deferir honorários periciais** mas **não fixar valor em R$** (ex.: "honorários periciais a serem fixados na liquidação", "valor a arbitrar na fase de liquidação"), a IA **deve** preencher o campo de valor dos honorários periciais (`honorarios_periciais` ou equivalente) **estritamente** com a string: **"A arbitrar na liquidação"**. Não usar textos genéricos ou redundantes como "no valor definido na sentença".
- Se o juiz fixar valor em R$, extrair o valor normalmente (ex.: "R$ 1.500,00").

### Multas rescisórias (Dispositivo)
- `multa_art_467`: buscar "multa do art. 467", "50% sobre as verbas incontroversas" — registrar
  o texto da condenação ou o valor se fixado
- `multa_art_477`: buscar "multa do art. 477", "1 salário por atraso na quitação rescisória" —
  registrar o texto ou valor

### Verbas deferidas — lista completa (Dispositivo)
Leia APENAS o DISPOSITIVO para extrair o que foi deferido. Ignore pedidos INDEFERIDOS.
Para cada verba deferida, extraia:

- `nome`: nome exato da verba (ex: "Horas Extras", "Adicional Noturno", "FGTS + 40%",
  "Aviso Prévio Indenizado", "Saldo de Salário", "Férias Proporcionais + 1/3",
  "13º Salário Proporcional", "Intervalo Intrajornada")
- `status_final`: sempre "mantida" para sentença de 1ª instância (ainda não houve reforma)
- `periodo`: período de apuração — **nunca assumir que a verba abrange todo o contrato**. A IA deve **caçar ativamente** limitações temporais impostas pelo juiz, por exemplo:
  - "a partir de DD/MM/AAAA", "desde DD/MM/AAAA", "apuração a partir de 01/07/2017";
  - "até DD/MM/AAAA", "limitado até novembro de 2018";
  - "no período de X a Y", "de X a Y", "entre X e Y".
  Preencher `periodo` com a **exata** limitação temporal (ex.: "a partir de 01/07/2017", "01/02/2016 a 30/11/2018"). Se o juiz não limitar, aí sim usar todo o contrato (ex.: "todo o contrato" ou intervalo data_admissão a data_demissao).
- `percentual`: percentual aplicável — ex: "50%", "60%", "100%". Para **horas extras**, não assumir 50%; extrair o valor fixado pelo juiz (50% é o padrão constitucional, mas a sentença pode fixar 60% ou outro).
- `quantidade_diaria`: quando houver — ex: "2h extras por dia", "30 min de intervalo suprimido"
- `base_calculo`: o que compõe a base — ex: "salário base", "salário base + adicional noturno". Para **horas extras/intervalo**, incluir aqui o **critério dos reflexos** quando o juiz especificar: ex. "Reflexos pela média física sobre RSR, aviso prévio, férias + 1/3, 13º e FGTS + 40%".
- `valor_fixado`: se o juiz fixou valor certo em R$ ao invés de percentual
- `integracao_salarial`: true se a verba integra o salário para reflexos, false se indenizatória
- **IMPORTANTE**: Verbas estritamente rescisórias (Saldo de Salário, Aviso Prévio, 13º Salário, Férias, Multas 467 e 477) **não** integram a base de cálculo de outras verbas. Para essas verbas, o campo `integracao_salarial` deve ser sempre `false`, **a menos que** o juiz determine expressamente o contrário.
- `reflexos`: lista dos reflexos deferidos — apenas os expressamente mencionados.
  Buscar frases de gatilho: "com reflexos em", "repercussão em", "com repercussão em",
  "integrando o salário para fins de", "com integração salarial em", "incidindo sobre".
  Possíveis reflexos: "13º salário", "Férias + 1/3", "FGTS + 40%", "DSR", "Aviso Prévio"
- `observacoes`: limitações, ressalvas ou particularidades da condenação

### Verbas rescisórias — sempre verificar
Mesmo que não sejam objeto de pedido específico, verificar se o dispositivo condena ao pagamento de:
- Saldo de salário
- Aviso prévio (trabalhado ou indenizado)
  - Se deferido, verificar se o juiz aplicou a Lei 12.506/2011: 30 dias + 3 dias por ano de serviço
  - Buscar: "aviso prévio proporcional", "Lei 12.506", "acrescido de X dias"
  - Registrar duração total em `observacoes` da verba (ex: "42 dias — 30 + 12 pela Lei 12.506/2011")
- 13º salário proporcional
- Férias vencidas e proporcionais + 1/3
- FGTS + multa de 40%

### Intervalo intrajornada — regra pós-Reforma Trabalhista (contratos a partir de 11/11/2017)
- Natureza **indenizatória** para contratos após a Reforma — NÃO gera reflexos
- Natureza **salarial** para contratos anteriores à Reforma — gera reflexos normalmente
- Verificar a data de admissão para determinar qual regra aplica
- Gatilhos: "supressão do intervalo", "intervalo intrajornada", "art. 71, § 4º da CLT",
  "intervalo não usufruído", "intervalo suprimido"
- Registrar em `integracao_salarial`: false se pós-Reforma, true se pré-Reforma
- Registrar em `observacoes`: "Natureza indenizatória — sem reflexos (pós-Reforma)" ou
  "Natureza salarial — com reflexos (pré-Reforma)"

### Armadilhas comuns
- O juiz pode deferir na fundamentação mas LIMITAR no dispositivo — usar sempre o dispositivo
- "Defiro em parte" significa fração concedida — registrar a limitação em `observacoes`
- Verbas deferidas "por reflexo" não são autônomas — incluir apenas no campo `reflexos` da verba principal
- Não confundir dano moral (valor fixo, não gera reflexos) com verbas de natureza salarial
- Multas dos arts. 467 e 477 são campos separados, não entram em `verbas_deferidas`
- **Rito Sumaríssimo — limitação**: Caçar ativamente frases como "condenação limitada aos valores dos pedidos" ou "valores da inicial são meras estimativas (IN 41/2018 TST)". Registrar em `limitação_valores_inicial` para a perita; define se o cálculo pode ultrapassar o valor da inicial.
- **Honorários periciais sem valor**: Se o juiz não fixar valor em R$ (deixando para a liquidação), preencher **apenas** "A arbitrar na liquidação". Evitar texto redundante ("no valor definido na sentença").

---

## 📖 DICIONÁRIO DE VARIAÇÕES LINGUÍSTICAS E EXEMPLOS

Use esta seção como **guia de raciocínio lógico**: quando encontrar redações parecidas com os exemplos abaixo, interprete-as da mesma forma e preencha os campos estruturados com o valor correspondente.

### 1. Divisor de horas extras (interpretação implícita)

- Se o juiz escrever algo equivalente a:
  - "defiro horas extras além da 8ª diária e 44ª semanal"
  - "jornada normal de 8h diárias e 44h semanais"
  então o **divisor implícito** a ser utilizado é:
  - `divisor_horas = "220"`.

- Se o juiz escrever algo equivalente a:
  - "jornada de 6h, divisor aplicável ao bancário"
  - "empregado bancário submetido à jornada de 6h"
  então o **divisor** a ser utilizado é:
  - `divisor_horas = "180"`.

- Se o juiz escrever:
  - "divisor 200 para a jornada descrita"
  então o **divisor** é explicitamente:
  - `divisor_horas = "200"`.

- Se o juiz ou a liquidação indicar **dois divisores em períodos diferentes** (ex.: "divisor 120 no período A e 180 no período B", ou na prática "divisor 120/180"):
  - Preencher `divisor_horas` com **"120/180"** (ou a redação exata da sentença, ex.: "120 até DD/MM/AAAA e 180 a partir de DD/MM/AAAA"). **Não** reduzir a um único número; a variação é crítica para o cálculo.

Sempre que houver menção clara ou implícita ao divisor, preencha o campo `divisor_horas` com o número correspondente **como string** (por exemplo `"180"`, `"200"`, `"220"`, ou `"120/180"` quando houver variação).

### 1.1 Horas extras — percentual e critério de reflexos (extração granular)

- **Exemplo de texto do juiz / parecer de liquidação:** "Horas extras com divisor 120/180, percentual de 60%, com reflexos pela média física sobre RSR, aviso prévio, férias + 1/3, 13º salário e FGTS + 40%."
- **Como a IA deve extrair (verbas_deferidas, verba de horas extras):**
  - `divisor_horas` (no nível do processo ou da verba, conforme o modelo): **"120/180"**.
  - `percentual`: **"60%"** (não assumir 50% quando a sentença ou o parecer indicar 60%).
  - `reflexos`: **["RSR", "aviso prévio", "férias + 1/3", "13º salário", "FGTS + 40%"]** (ou a lista exata mencionada).
  - `base_calculo` ou `observacoes`: **"Reflexos pela média física sobre RSR, aviso prévio, férias + 1/3, 13º salário e FGTS + 40%"** — para que a perita e o PJe-Calc saibam que o critério foi "média física".

- **Outro exemplo:** "Adicional de horas extras a 50%, observado o divisor 180, com reflexos nos termos das Súmulas 264 e 347 do TST."
- **Extrair:** `percentual` = **"50%"**; `divisor_horas` = **"180"**; em `observacoes` ou `base_calculo`: menção às Súmulas 264 e 347. Se o juiz **não** disser "média física", não inventar; registrar apenas o que constar.

- **Regra:** Sempre que aparecer "**pela média**", "**pela média física**", "**média duodecimal**", "**média aritmética**" ou "**valores efetivamente pagos**" para reflexos de horas extras (ou intervalo intrajornada), incluir esse critério em `base_calculo` ou `observacoes` da verba, de forma explícita e granular. Quando útil, incluir no item do `reflexos` (ex.: "Aviso Prévio (pela média física)").

- **Exemplo — média duodecimal:** "Reflexos pela média duodecimal sobre 13º, férias e FGTS."
  - Extrair: `base_calculo` ou `observacoes`: **"Reflexos pela média duodecimal sobre 13º, férias e FGTS"**; em `reflexos` pode constar, por exemplo, "13º salário (média duodecimal)", "Férias + 1/3 (média duodecimal)", "FGTS + 40% (média duodecimal)".

### 2. Marcos temporais específicos por verba (nunca assumir todo o contrato)

- A IA **não** deve assumir que uma verba abrange todo o período contratual. Deve **caçar** no dispositivo e na fundamentação se o juiz limitou a condenação a um intervalo de datas.
- **Exemplo:** "Apuração do intervalo intrajornada **a partir de 01/07/2017**."
  - O contrato pode ter começado em fevereiro; a condenação do intervalo só vale de 01/07/2017 em diante. Preencher `periodo` da verba "Intervalo Intrajornada" com **"a partir de 01/07/2017"** (ou "01/07/2017 a [data_demissão]" se quiser deixar explícito o fim).
- **Exemplo:** "Horas extras **limitadas até novembro de 2018**."
  - Preencher `periodo` da verba "Horas Extras" com **"até 30/11/2018"** ou "todo o contrato até 30/11/2018", conforme o contexto (e data_admissão).
- **Exemplo:** "Adicional noturno no período de 01/01/2019 a 31/12/2020."
  - `periodo` = **"01/01/2019 a 31/12/2020"**.
- Se **não** houver menção a data de início/fim para a verba, aí sim usar "todo o contrato" ou o intervalo entre data_admissao e data_demissao.

### 3. Correção monetária e ADC 58 (interpretação de índices)

- Se o juiz escrever expressões como:
  - "aplicar tese do STF na ADC 58"
  - "aplicam-se os parâmetros fixados na ADC 58 do STF"
  e NÃO detalhar a redação, adote a interpretação padrão:
  - `indice_correcao = "IPCA-E (fase pré-judicial) / SELIC (fase judicial)"`
  - `juros_mora` conforme a sentença (se houver) ou mantendo o padrão do título.

- Se o juiz escrever algo como:
  - "TR até 24/03/2015 e IPCA-E a partir do dia 25"
  então **não simplifique**: extraia exatamente a quebra de datas descrita, por exemplo:
  - `indice_correcao = "TR até 24/03/2015 e IPCA-E a partir de 25/03/2015"`

- Se o juiz escrever expressões como:
  - "taxa legal divulgada pelo Banco Central na forma da Resolução CMN 5.171, de 29 de agosto de 2024, na forma do §3º do art. 406 do Código Civil"
  então a **taxa legal** referida é a SELIC (Resolução CMN 5.171/2024 regulamenta sua divulgação pelo Bacen). Extraia de forma limpa:
  - `juros_mora` e/ou `indice_correcao`: use **"SELIC"** (ou "taxa SELIC", "SELIC na forma do art. 406 do CC e Res. CMN 5.171/2024") conforme o contexto da frase, sem reproduzir todo o juridiquês.

Quando houver menção a múltiplos períodos (TR, IPCA-E, SELIC), **preserve a sequência e as datas** na string do campo, sem tentar normalizar para um único rótulo.

### 4. Reflexos (ocultos, de praxe ou agrupados)

- Se o juiz escrever:
  - "com os reflexos de praxe"
  - "com os reflexos legais"
  - "com os reflexos pertinentes" ou "demais reflexos legais"
  e **não** listar quais são esses reflexos, a IA **NÃO** deve escrever literalmente "reflexos legais" no JSON, pois isso é inútil para o PJe-Calc.
  - Sempre que a verba for tipicamente salarial (ex.: Horas Extras, Adicional Noturno, Adicional de Insalubridade), e o juiz usar apenas essas expressões genéricas, a IA deve **expandir automaticamente** o array de reflexos como:
    - `reflexos = ["DSR", "Aviso Prévio", "Férias + 1/3", "13º Salário", "FGTS + 40%"]`.
  - Se, além da expressão genérica, houver lista parcial explícita (ex.: "reflexos legais em 13º e férias"), manter a lista explícita e **completar** quando fizer sentido, documentando em `observacoes` da verba que se tratam de "reflexos legais (de praxe)".

- Se o juiz escrever algo equivalente a:
  - "integrações em 13º, RSR, e nas parcelas rescisórias"
  então converta **explicitamente** o grupo "parcelas rescisórias" para as parcelas típicas:
  - "Aviso Prévio"
  - "Férias + 1/3"
  - "Multa 40% do FGTS"
  Nesse caso, a lista final de reflexos deve ser:
  - `reflexos = ["13º salário", "DSR", "Aviso Prévio", "Férias + 1/3", "FGTS + 40%"]`

Em qualquer caso em que a linguagem seja vaga ("reflexos de praxe", "demais reflexos legais"), a IA deve:

1. Priorizar a **expansão padrão segura** para verbas salariais principais (["DSR", "Aviso Prévio", "Férias + 1/3", "13º Salário", "FGTS + 40%"]) quando o contexto indicar claramente que se trata dos reflexos "de praxe".
2. Procurar pistas explícitas nas frases próximas e complementar/conferir a lista padrão quando o juiz nomear reflexos específicos.
3. Em verbas de natureza claramente indenizatória (sem reflexos), manter `reflexos` vazio mesmo que o texto seja impreciso.

### 5. Imposto de Renda (Lei 7.713/88 e regime RRA)

- Se o juiz escrever algo equivalente a:
  - "observado o disposto no artigo 12-A, § 1º, da Lei 7.713/88 (redação da Lei 12.350/2010)"
  então está se referindo ao **regime de competência** para IR sobre verbas trabalhistas (RRA — Rendimentos Recebidos Acumuladamente). Preencha o campo de imposto de renda (ou observações correlatas) indicando:
  - `ir_retido_fonte` ou texto equivalente: **"Regime de Competência (RRA — Rendimentos Recebidos Acumuladamente), art. 12-A § 1º Lei 7.713/88 (Lei 12.350/2010)"** ou de forma resumida: **"RRA — Rendimentos Recebidos Acumuladamente"**.

### 6. FGTS e multa de 40% sobre aviso prévio (OJ 42 SDI-I TST)

- Se o juiz escrever algo equivalente a:
  - "devido o FGTS, mas não o acréscimo de 40% sobre o aviso prévio"
  - "FGTS devido, sem incidência dos 40% sobre o aviso prévio indenizado"
  então a **multa de 40% do FGTS não incide** sobre o aviso prévio (aplicação da OJ 42 SDI-I TST). Preencha de forma explícita:
  - `fgts_sobre_aviso_previo`: pode ser **"Sim"** ou equivalente (FGTS sobre aviso é devido).
  - `fgts_multa_40_aviso_previo`: **"Não — multa de 40% NÃO incide sobre aviso prévio (OJ 42 SDI-I TST)"** ou, de forma curta, **"Não incide"**.
  Assim a extração reflete corretamente: FGTS devido sobre o aviso; multa de 40% não incide sobre o aviso.

### 7. Divisores especiais (categorias diferenciadas — juiz omisso)

- Se o juiz deferir **jornada contratual** sem citar o divisor de horas extras (ex.: "jornada de 35 horas semanais", "jornada de 6h diárias e 36h semanais", "44h semanais"), a IA deve **inferir o divisor** a partir da jornada semanal e preencher `divisor_horas`:
  - Jornada **30h semanais** → `divisor_horas = "150"`.
  - Jornada **35h semanais** → `divisor_horas = "175"`.
  - Jornada **36h semanais** → `divisor_horas = "180"`.
  - Jornada **40h semanais** → `divisor_horas = "200"`.
  - Jornada **44h semanais** → `divisor_horas = "220"`.
- Use essa regra **somente quando o juiz for omisso** quanto ao divisor. Se o juiz citar divisor ou Súmulas 264/347 com número, priorize o valor expresso na sentença.
- Preencha também `jornada_contratual` com o texto extraído (ex.: "35h semanais", "6h diárias e 36h semanais").

### 8. Data de saída na CTPS e projeção (OJ 82 da SDI-I do TST)

- Se o juiz escrever algo equivalente a:
  - "proceder à anotação de saída na CTPS considerando a projeção do aviso prévio indenizado (OJ 82 da SDI-1 do TST)"
  - "anotar na CTPS a data de saída com projeção do aviso prévio (OJ 82)"
  então:
  1. **Calcule ativamente** a data de saída na CTPS: tome a `data_demissao` e **some os dias** indicados em `aviso_previo_dias` (ex.: 30, 33, 42). O resultado é a data a ser anotada na CTPS. Preencha `data_saida_ctps` com essa data no formato DD/MM/AAAA.
  2. Em `anotacao_ctps` ou em observações do contrato, registre a citação **"OJ 82 da SDI-I do TST"** (ou "projeção do aviso prévio — OJ 82") para rastreabilidade.
- Se `data_demissao` ou `aviso_previo_dias` não estiverem disponíveis na extração, preencha `data_saida_ctps` como null e use `anotacao_ctps` com o texto literal do juiz, indicando que a data deve ser calculada pelo perito.

### 9. Férias fatiadas (dobro, simples, proporcionais por período)

- Se o juiz escrever algo equivalente a:
  - "condeno ao pagamento das férias 2023/2024 em dobro e 2024/2025 de forma simples"
  - "férias vencidas em dobro e férias proporcionais simples"
  então a IA deve:
  1. **Criar verbas separadas** em `verbas_deferidas` para cada período ou tipo (ex.: uma verba "Férias 2023/2024" e outra "Férias 2024/2025"; ou "Férias vencidas" e "Férias proporcionais").
  2. Em cada verba, preencher **`observacoes`** (ou `percentual`/campo de detalhe) de forma **explícita**:
     - Se em dobro: "Férias em dobro" ou "Em dobro (art. 137 CLT)".
     - Se simples: "Férias simples" ou "Forma simples".
  3. Essa distinção é **crítica** para a parametrização no PJe-Calc (dobro altera base de cálculo e reflexos). Nunca agrupe em uma única verba quando o juiz distinguir períodos ou modalidades (dobro vs. simples).

### 10. Rito Sumaríssimo e parâmetros críticos do dispositivo

**9.1 Limitação aos valores da inicial**
- Se o juiz escrever algo equivalente a:
  - "A condenação fica limitada aos valores dos pedidos da inicial"
  - "Os valores indicados na inicial têm caráter de mera estimativa (IN 41/2018 do TST)"
  então preencher `limitação_valores_inicial` de forma explícita:
  - No primeiro caso: **"Condenação limitada aos valores da inicial"**.
  - No segundo: **"Valores da inicial são mera estimativa (IN 41/2018 TST)"**.
  A IA deve **caçar ativamente** essas frases no dispositivo; essa diretriz define se o valor apurado pode ultrapassar o pedido.

**9.2 Honorários periciais sem valor fixo**
- Se o juiz escrever algo equivalente a:
  - "honorários periciais a serem fixados na liquidação"
  - "honorários do perito a arbitrar na fase de liquidação"
  e **não** houver valor em R$ fixado na sentença, preencher o campo de valor dos honorários periciais **estritamente** com: **"A arbitrar na liquidação"**. Não usar "no valor definido na sentença" nem outras variantes redundantes.

**9.3 Base de cálculo dos honorários sucumbenciais (OJ 348)**
- Se o juiz escrever algo equivalente a:
  - "10% sobre o valor líquido da condenação, nos termos da OJ 348 da SDI-I do TST"
  - "honorários de 15% sobre o proveito econômico"
  então extrair **não apenas** o percentual (`percentual_honorarios`: "10%" ou "15%"), **mas também** a base de cálculo. Preencher `base_calculo_honorarios_sucumbenciais` (ou texto único em observações) com: **"Sobre o valor líquido da condenação — OJ 348 SDI-I TST"** ou **"Sobre o proveito econômico"**. Saber se é líquido ou bruto altera o resultado da planilha.

**9.4 Valor arbitrado à condenação (custas)**
- Se o juiz escrever algo equivalente a:
  - "Custas de R$ 200,00, calculadas sobre R$ 10.000,00, valor arbitrado à condenação"
  - "Custas pela reclamada de R$ 200,00, sobre o valor de R$ 10.000,00 arbitrado à condenação"
  então extrair: `custas_processuais` com quem paga e o valor das custas (ex.: "Reclamada, R$ 200,00"); e **`valor_arbitrado_condenacao`** com **"R$ 10.000,00"**. Esse valor ajuda a perita a ter noção da escala (custas 2% → valor arbitrado = custas / 0,02).
```markdown
---
## Engenharia Reversa — Discrepância: verba_ausente
<!-- Laboratório de Aprendizado | 13/03/2026 03:09 | Processo: 0011219-69.2024.5.15.0052 -->

### Padrão de erro identificado
O cálculo das verbas rescisórias apresentado pela reclamada omite o saldo de salário, embora este tenha sido expressamente deferido na sentença. O padrão de erro reside na incompleta ou incorreta transcrição das verbas deferidas para a fase de liquidação, resultando em prejuízo ao reclamante.

### Como identificar na sentença
Palavras-chave: "deferido", "saldo de salário", "verbas rescisórias". Verificar a seção da sentença que trata das verbas rescisórias deferidas. Confirmar se há menção expressa ao saldo de salário. Comparar com o cálculo apresentado pela reclamada para identificar a omissão.

### Correção correta
Incluir o saldo de salário no cálculo das verbas rescisórias, apurando os dias trabalhados no mês da rescisão contratual e multiplicando pelo salário-dia do empregado. Detalhar a metodologia de cálculo na manifestação, indicando o período considerado e o valor do salário-dia.

### Base legal
artigo 467 e 477 da CLT

### Exemplo prático
**Texto na sentença (padrão problemático):**
> "JULGO PROCEDENTE EM PARTE o pedido para condenar a reclamada a pagar ao reclamante, nos termos da fundamentação supra, as seguintes verbas: férias proporcionais + 1/3, 13º salário proporcional, multa do artigo 467 e 477 da CLT e FGTS + 40%."

**Interpretação correta:**
Apesar da sentença não discriminar o saldo de salário expressamente neste trecho, a referência à "fundamentação supra" deve ser investigada. Se a fundamentação mencionar o saldo de salário como devido, este deve ser incluído no cálculo. A ausência de menção explícita na parte dispositiva não elimina a obrigação de inclusão se a fundamentação for clara a respeito.
```
---
## Engenharia Reversa — Discrepância: verba_ausente
<!-- Laboratório de Aprendizado | 13/03/2026 03:09 | Processo: 0011219-69.2024.5.15.0052 -->

### Padrão de erro identificado
Omissão, no memorial de cálculos, da verba "13º salário proporcional", apesar de seu deferimento expresso no dispositivo da sentença. O erro consiste na falha em transpor um item condenatório do julgado para a planilha de liquidação, resultando em cálculo a menor do crédito exequendo.

### Como identificar na sentença
Verificar o dispositivo da sentença (parte conclusiva/final do julgado) em busca de palavras-chave como "defiro", "condeno", "julgo procedente", associadas aos termos "13º salário proporcional", "décimo terceiro proporcional" ou "gratificação natalina proporcional". A discrepância é confirmada ao constatar a ausência desta rubrica específica na lista de verbas que compõem o principal bruto no cálculo de liquidação.

### Correção correta
Realizar o cálculo da verba deferida. Apurar o número de avos devidos com base no período trabalhado no ano da rescisão, considerando a projeção do aviso prévio (Súmula 371 do TST). A base de cálculo é a última remuneração do empregado. O valor apurado deve ser inserido como uma nova linha no memorial de cálculos, somando-se ao principal devido antes da incidência de juros e correção monetária.

### Base legal
Direito à verba: Lei nº 4.090/62 e Art. 7º, VIII, da Constituição Federal. Multas por inadimplemento de verbas rescisórias (frequentemente impactadas pela ausência do 13º proporcional): Artigos 467 e 477, § 8º, da CLT.

### Exemplo prático
**Texto na sentença (padrão problemático):**
> Pelo exposto, condeno a reclamada a pagar ao reclamante as seguintes parcelas: (...) c) 13º salário proporcional do ano de 2024 (7/12 avos); d) Multa do art. 477 da CLT.

**Interpretação correta:**
A sentença determinou o pagamento de 7/12 avos do 13º salário. O sistema deve: 1) Identificar a base de cálculo (última remuneração). 2) Calcular o valor correspondente a 7/12 desta base. 3) Inserir o resultado como uma verba principal devida. 4) Assegurar que este valor componha a base de cálculo da multa do art. 477 da CLT, pois trata-se de verba rescisória não paga no prazo legal.
---
## Engenharia Reversa — Discrepância: verba_ausente
<!-- Laboratório de Aprendizado | 13/03/2026 03:09 | Processo: 0011219-69.2024.5.15.0052 -->

### Padrão de erro identificado
O padrão de erro identificado reside na omissão do cálculo e pagamento das férias proporcionais acrescidas de 1/3 constitucional quando expressamente deferidas na sentença condenatória. A ausência desta verba implica em um cálculo incompleto das obrigações trabalhistas devidas ao reclamante, resultando em um valor final incorreto.

### Como identificar na sentença
Palavras-chave: "férias proporcionais", "1/3 constitucional", "deferido", "condenação". Padrões textuais: verificar se a sentença menciona expressamente a condenação ao pagamento de férias proporcionais acrescidas de 1/3. Campos a verificar: seção "Dispositivo" ou "Conclusão" da sentença, buscando a determinação explícita da condenação à referida verba. Ausência da verba na planilha de cálculos apresentada.

### Correção correta
Incluir as férias proporcionais (x/12 avos) acrescidas do 1/3 constitucional no cálculo das verbas rescisórias, observando o período aquisitivo incompleto e a projeção do aviso prévio indenizado (se houver). A base de cálculo será a remuneração do empregado à época da rescisão contratual.

### Base legal
artigo 467 e 477 da CLT

### Exemplo prático
**Texto na sentença (padrão problemático):**
> "Ante o exposto, julgo PROCEDENTE EM PARTE a presente reclamação trabalhista para condenar a reclamada a pagar ao reclamante as seguintes verbas: a) férias proporcionais + 1/3; (...)."

**Interpretação correta:**
A expressão "férias proporcionais + 1/3" implica na obrigatoriedade de inclusão no cálculo das férias proporcionais correspondentes ao período aquisitivo incompleto trabalhado, acrescidas de um terço do valor das férias, conforme previsão constitucional. O cálculo deverá observar a proporção de meses trabalhados no período aquisitivo, dividindo o número de meses trabalhados por 12 (considerando o período aquisitivo completo de 12 meses) e multiplicando o resultado pela remuneração mensal do empregado acrescida do 1/3 constitucional.
---
## Engenharia Reversa — Discrepância: verba_ausente
<!-- Laboratório de Aprendizado | 13/03/2026 03:10 | Processo: 0011219-69.2024.5.15.0052 -->

### Padrão de erro identificado
Omissão, na liquidação de sentença, da verba "aviso-prévio indenizado" quando esta foi expressamente deferida no dispositivo judicial. O erro comum é não incluir seu valor no montante total das verbas rescisórias, o que consequentemente leva ao cálculo incorreto das multas dos artigos 467 e 477 da CLT, que incidem sobre as verbas rescisórias devidas.

### Como identificar na sentença
Verificar o dispositivo da sentença em busca de termos e expressões como "deferir o pagamento de aviso-prévio indenizado", "condeno a reclamada ao pagamento de aviso-prévio", "projeção do aviso prévio" ou "integração do aviso prévio ao tempo de serviço". A presença de tais comandos indica que a verba deve compor o cálculo.

### Correção correta
O valor do aviso-prévio indenizado, bem como seus reflexos (em 13º salário e férias + 1/3), deve ser apurado e incluído na planilha de cálculos. Este montante integrará a base de cálculo das multas dos artigos 467 e 477 da CLT, pois o aviso-prévio indenizado possui natureza de verba rescisória.

### Base legal
Artigo 467 da CLT (multa de 50% sobre as verbas rescisórias incontroversas não pagas na data do comparecimento à Justiça do Trabalho) e Artigo 477, § 8º, da CLT (multa pelo atraso no pagamento das verbas constantes do instrumento de rescisão ou recibo de quitação).

### Exemplo prático
**Texto na sentença (padrão problemático):**
> "Julgo PROCEDENTES EM PARTE os pedidos para condenar a Reclamada a pagar ao Reclamante as seguintes parcelas: ... b) aviso-prévio indenizado de 33 dias, com a devida projeção em 13º salário e férias acrescidas do terço constitucional."

**Interpretação correta:**
O sistema deve identificar o deferimento do "aviso-prévio indenizado". O valor correspondente a 33 dias de salário do empregado deve ser calculado e adicionado ao total das verbas rescisórias. Este valor total (incluindo o aviso-prévio e seus reflexos) servirá de base para a apuração da multa do artigo 477 da CLT. Caso o pagamento não ocorra na primeira audiência, o valor do aviso-prévio também comporá a base da multa do artigo 467 da CLT.
---
## Engenharia Reversa — Discrepância: verba_ausente
<!-- Laboratório de Aprendizado | 13/03/2026 03:10 | Processo: 0011219-69.2024.5.15.0052 -->

### Padrão de erro identificado
Omissão, na planilha de liquidação, de verba principal expressamente deferida no dispositivo da sentença. O cálculo é apresentado sem a apuração dos valores devidos a título de intervalo intrajornada, resultando em um montante liquidado inferior ao determinado no título executivo judicial.

### Como identificar na sentença
Realizar a conferência entre o rol de verbas deferidas no dispositivo da sentença e as verbas efetivamente quantificadas na planilha de cálculo. A discrepância é confirmada ao se constatar a menção a termos como "defiro o pagamento de horas intervalares", "supressão do intervalo intrajornada" ou "violação do art. 71 da CLT" na decisão, sem a correspondente linha de cálculo na apuração.

### Correção correta
Inclusão da verba "Intervalo Intrajornada" no memorial de cálculos, com a devida apuração de principal e reflexos, conforme os parâmetros fixados pela sentença (base de cálculo, adicional, divisor, período da condenação). A manifestação de impugnação geralmente aponta a falha de forma direta, como no trecho: "b) INTERVALO INTRAJORNADA".

### Base legal
Fundamento normativo: artigo 467 e 477 da CLT.

### Exemplo prático
**Texto na sentença (padrão problemático):**
> Posto isto, julgo PROCEDENTE o pedido para condenar a reclamada ao pagamento de 1 (uma) hora extra diária, acrescida do adicional de 50%, pela supressão parcial do intervalo intrajornada durante todo o pacto laboral, com reflexos em DSR, aviso prévio, 13º salários, férias + 1/3 e FGTS (8% + 40%).

**Interpretação correta:**
O comando judicial determina a apuração de uma verba específica denominada "Intervalo Intrajornada" ou "Horas Extras Intervalares". O cálculo deve quantificar 1 hora por dia de trabalho, aplicar o adicional de 50% sobre o valor da hora normal e calcular os reflexos (impactos secundários) nas demais verbas salariais e rescisórias listadas. A ausência desta rubrica na planilha de liquidação caracteriza o erro 'verba_ausente'.
---
## Engenharia Reversa — Discrepância: verba_ausente
<!-- Laboratório de Aprendizado | 13/03/2026 03:11 | Processo: 0011219-69.2024.5.15.0052 -->

### Padrão de erro identificado
Omissão, na planilha de liquidação, de parcela salarial ou indenizatória expressamente deferida no dispositivo da sentença. O cálculo é apresentado de forma incompleta, não refletindo a totalidade da condenação e resultando em prejuízo ao credor.

### Como identificar na sentença
Verificar a congruência entre o dispositivo da sentença (parte final que resume a decisão) e as rubricas lançadas na planilha de cálculo. Procurar por termos como "defiro", "condeno ao pagamento de" ou "julgo procedente o pedido de", seguidos da nomenclatura da verba (ex: "adicional noturno"). A ausência desta verba na memória de cálculo é o indicador do erro.

### Correção correta
Realizar a inclusão da verba omissa e seus respectivos reflexos, se houver, na memória de cálculo. A apuração deve seguir estritamente os parâmetros definidos no título executivo judicial (base de cálculo, percentual, período, divisor, etc.), integrando o valor apurado ao montante total da condenação.

### Base legal
Artigo 73 da CLT (regula o adicional noturno). Artigos 467 e 477 da CLT (fundamentam multas aplicáveis em caso de não pagamento de verbas incontroversas e rescisórias, respectivamente, no prazo legal).

### Exemplo prático
**Texto na sentença (padrão problemático):**
> Do exposto, julgo PROCEDENTE o pedido para condenar a reclamada ao pagamento de **adicional noturno** sobre as horas laboradas após as 22h, com o adicional de 20%, e reflexos em DSR, aviso prévio, 13º salários, férias + 1/3 e FGTS (8% + 40%).

**Interpretação correta:**
A liquidação deve, obrigatoriamente, conter uma linha de apuração para a verba "Adicional Noturno" e outras linhas para cada um dos "reflexos" deferidos. A ausência do cálculo do principal (adicional noturno) ou de qualquer um dos seus reflexos (DSR, 13º, etc.) na planilha constitui erro material por omissão, devendo a conta ser retificada para incluir tais parcelas.
---
## Engenharia Reversa — Discrepância: verba_ausente
<!-- Laboratório de Aprendizado | 13/03/2026 03:11 | Processo: 0011219-69.2024.5.15.0052 -->

### Padrão de erro identificado
Ocorre a ausência de inclusão da verba vale-alimentação no cálculo das verbas rescisórias, mesmo havendo determinação expressa na sentença para sua integração salarial para todos os efeitos. Isso resulta em um cálculo incompleto e prejudicial ao reclamante.

### Como identificar na sentença
Palavras-chave: "vale-alimentação", "integração salarial", "natureza salarial", "reflexos".
Padrões textuais: Sentenças que expressamente determinam a integração do vale-alimentação ao salário para fins de cálculo de outras verbas, especialmente rescisórias.
Campos a verificar: Dispositivo da sentença, fundamentação legal utilizada para determinar a natureza salarial do vale-alimentação, planilha de cálculos apresentada (se houver) para verificar se a verba foi corretamente considerada.

### Correção correta
Incluir o valor do vale-alimentação na base de cálculo das verbas rescisórias (aviso prévio, férias + 1/3, 13º salário, FGTS + 40%), proporcionalmente ao período trabalhado, conforme determinado na sentença. Recalcular as verbas rescisórias considerando a integração do vale-alimentação, observando a prescrição quinquenal.

### Base legal
artigo 467 e 477 da CLT

### Exemplo prático
**Texto na sentença (padrão problemático):**
> "Defiro o pedido de integração do vale-alimentação ao salário do reclamante, com reflexos em aviso prévio, férias + 1/3, 13º salário, FGTS + 40% e demais verbas rescisórias."

**Interpretação correta:**
A determinação judicial é clara quanto à necessidade de considerar o vale-alimentação como parte integrante do salário para todos os efeitos, inclusive no cálculo das verbas rescisórias. A ausência de tal consideração implica em erro no cálculo. O valor mensal do vale-alimentação deve ser somado ao salário base para cálculo das verbas rescisórias mencionadas na sentença.