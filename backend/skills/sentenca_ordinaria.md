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
---
## Engenharia Reversa — Regra Preditiva: Horas Extras — Realização de jornada de tra
<!-- Laboratório de Aprendizado | 13/03/2026 21:45 | Processo: 1002192-49.2025.5.02.0221 -->

### Padrão de erro identificado
Omissão sistemática da parametrização para apuração de horas extras no sistema PJe-Calc, mesmo quando a verba é expressamente deferida em sentença. A reclamada falha em configurar o sistema para calcular as horas que excedem a 8ª diária, resultando em uma liquidação de sentença com valor a menor.

### Como identificar na sentença
Verificar o dispositivo da sentença em busca de expressões como "condeno ao pagamento de horas extras", "deferimento de horas extras", "excedentes à 8ª diária" ou "jornada superior à legal". A presença destes termos, aliada à ausência de pagamento correspondente nos holerites, sinaliza a alta probabilidade de erro de parametrização no cálculo de liquidação.

### Correção correta
Auditar a configuração da verba "Horas Extras" no PJe-Calc, assegurando que o sistema esteja parametrizado para apurar todo o labor que excede a 8ª hora diária, aplicando o adicional legal ou convencional pertinente. Utilizar os cartões de ponto e holerites anexados ao processo como contraprova para validar a jornada efetivamente praticada e a ausência do devido pagamento.

### Base legal
Art. 59 da Consolidação das Leis do Trabalho (CLT).

### Exemplo prático
**Texto na sentença (padrão problemático):**
> Julgo PROCEDENTE o pedido para condenar a reclamada ao pagamento de horas extras, assim consideradas as excedentes da 8ª diária e 44ª semanal, com adicional de 50% e reflexos em DSR, aviso prévio, 13º salários, férias acrescidas de 1/3 e FGTS com multa de 40%.

**Interpretação correta:**
O deferimento explícito de "horas extras excedentes da 8ª diária" impõe a verificação compulsória da parametrização no PJe-Calc. O sistema deve ser configurado para quantificar todas as horas registradas nos cartões de ponto que ultrapassem a oitava hora de trabalho em um mesmo dia. A ausência dessa configuração caracteriza erro material no cálculo, que deve ser corrigido para refletir a condenação judicial na sua integralidade.
---
## Engenharia Reversa — Regra Preditiva: Reflexos em DSR, Férias, 13º e FGTS — Não integração das horas extras habituais na base de cálculo
<!-- Laboratório de Aprendizado | 13/03/2026 21:46 | Processo: 1002192-49.2025.5.02.0221 -->

### Padrão de erro identificado
Omissão sistemática da integração da média das horas extras habituais na base de cálculo das verbas reflexas, como Descanso Semanal Remunerado (DSR), férias acrescidas do terço constitucional, 13º salário e Fundo de Garantia por Tempo de Serviço (FGTS). A falha ocorre na parametrização do sistema de cálculos (PJe-Calc), onde a base de cálculo das verbas principais não é configurada para incluir os valores apurados a título de sobrelabor.

### Como identificar na sentença
Buscar no dispositivo da sentença condenações que contenham a expressão-chave "reflexos em DSR, férias, 13º e FGTS" ou variações similares, associadas ao deferimento de horas extras. A presença desta determinação exige a verificação imediata da configuração da base de cálculo das verbas reflexas no sistema de liquidação.

### Correção correta
Auditar a parametrização do PJe-Calc para garantir que o valor médio das horas extras habitualmente prestadas, já majorado pelo DSR, seja efetivamente integrado à base de cálculo de férias + 1/3, 13º salário e FGTS. O processo envolve:
1. Apurar a média física ou duodecimal das horas extras, conforme período apuratório.
2. Calcular o reflexo em DSR sobre o valor apurado.
3. Somar o valor principal da remuneração, a média das horas extras e o DSR sobre horas extras para compor a base de cálculo final das demais verbas deferidas.
4. Utilizar holerites e cartões de ponto como prova documental para validar a habitualidade e os valores.

### Base legal
- **Súmula nº 45 do TST:** "A remuneração do serviço suplementar, habitualmente prestado, integra o cálculo da gratificação natalina, nos termos da Lei nº 4.090/62."
- **Súmula nº 172 do TST:** "Computam-se no cálculo do repouso remunerado as horas extras habitualmente prestadas."
- **Súmula nº 376, II, do TST:** "O valor das horas extras habitualmente prestadas integra o cálculo dos haveres trabalhistas, inclusive para fins de cálculo do FGTS."

### Exemplo prático
**Texto na sentença (padrão problemático):**
> "Condeno a reclamada ao pagamento de horas extras excedentes à 8ª diária e 44ª semanal, com adicional de 50%, divisor 220, observada a evolução salarial. Deferem-se, pela habitualidade, os reflexos em DSR, aviso prévio, férias + 1/3, 13º salários e FGTS (8% + 40%)."

**Interpretação correta:**
A determinação "reflexos em DSR, férias + 1/3, 13º salários e FGTS" impõe uma cadeia de cálculos sucessivos. A base de cálculo para Férias, 13º Salário e FGTS não é apenas o salário base, mas sim o salário base acrescido da média mensal do valor total das horas extras e do DSR apurado sobre essas horas extras.
- **Ação para o sistema:** Parametrizar o cálculo de "Férias" para que sua base de apuração seja `[Salário Base] + [Média Duodecimal de Horas Extras] + [Média Duodecimal de DSR sobre Horas Extras]`. Repetir a mesma lógica de composição da base para 13º Salário e FGTS.
---
## Exemplo de Aprendizado — 13/03/2026 21:45
<!-- Adicionado automaticamente pelo Laboratório de Aprendizado -->

**Fundamento jurídico:** Amostragem pericial — cross-reference sentença/liquidação
**Situação identificada:** Tese Vencedora: Existência de horas extras não remuneradas

**Descrição:**
Tese provada pela perita na amostragem pericial: Existência de horas extras não remuneradas. Registrar como playbook para orientar auditoria futura de cálculos similares.

<!-- Revisar e expandir com trecho real da sentença se necessário -->

---
## Exemplo de Aprendizado — 13/03/2026 21:45
<!-- Adicionado automaticamente pelo Laboratório de Aprendizado -->

**Fundamento jurídico:** Amostragem pericial — cross-reference sentença/liquidação
**Situação identificada:** Tese Vencedora: Não pagamento dos reflexos das horas extras em DSR, 13º salário, férias, aviso p

**Descrição:**
Tese provada pela perita na amostragem pericial: Não pagamento dos reflexos das horas extras em DSR, 13º salário, férias, aviso prévio e FGTS. Registrar como playbook para orientar auditoria futura de cálculos similares.

<!-- Revisar e expandir com trecho real da sentença se necessário -->

---
## Engenharia Reversa — Discrepância: verba_ausente
<!-- Laboratório de Aprendizado | 13/03/2026 21:56 | Processo: 0011219-69.2024.5.15.0052 -->

### Padrão de erro identificado
Omissão, no cálculo de liquidação, de verba rescisória expressamente deferida no dispositivo da sentença. O sistema pode falhar em extrair e processar todos os itens de uma enumeração de condenações, resultando em um cálculo incompleto.

### Como identificar na sentença
Verificar no dispositivo da sentença (capítulo "Do Dispositivo" ou "Isto Posto") a lista de verbas deferidas. Procurar por termos como "condeno a Reclamada ao pagamento de", "são devidas as seguintes verbas", seguido de uma enumeração de parcelas (ex: saldo de salário, aviso prévio, férias + 1/3). A verba "saldo de salário" é frequentemente listada junto às demais verbas rescisórias.

### Correção correta
Incluir a verba "Saldo de Salário" na planilha de cálculos de liquidação. A apuração deve considerar os dias efetivamente trabalhados no mês da rescisão, utilizando como base de cálculo a última remuneração do Reclamante, conforme holerites ou o valor fixado em sentença.

### Base legal
Artigo 467 e 477 da Consolidação das Leis do Trabalho (CLT). A omissão do saldo de salário, verba rescisória por excelência, impacta diretamente a pontualidade e integralidade do pagamento das verbas rescisórias, atraindo a incidência das multas previstas nos referidos artigos.

### Exemplo prático
**Texto na sentença (padrão problemático):**
> ...julgo procedentes os pedidos para condenar a reclamada na obrigação de pagar as seguintes verbas rescisórias: saldo de salário, férias proporcionais + 1/3, 13º salário proporcional, multa do artigo 467 e 477 da CLT e FGTS + 40%.

**Interpretação correta:**
O cálculo deve incluir, obrigatoriamente, a verba "saldo de salário". A extração de dados deve identificar e processar cada item da enumeração de condenação. Se o cálculo inicial apresentou apenas férias, 13º e multas, ele está incompleto e deve ser corrigido para adicionar a apuração do saldo de salário correspondente aos dias trabalhados no mês da rescisão.
---
## Engenharia Reversa — Discrepância: verba_ausente
<!-- Laboratório de Aprendizado | 13/03/2026 21:57 | Processo: 0011219-69.2024.5.15.0052 -->

### Padrão de erro identificado
Omissão no cálculo de verba rescisória expressamente deferida no dispositivo da sentença. O sistema de cálculo não reconhece ou não inclui o 13º Salário Proporcional na planilha de liquidação, apesar de sua menção inequívoca no julgado como parcela procedente.

### Como identificar na sentença
Verificar o dispositivo da sentença (parte conclusiva) em busca das palavras-chave: "13º salário proporcional", "décimo terceiro proporcional", "13º/proporcional". A identificação ocorre ao cruzar a presença desses termos associados a verbos condenatórios ("deferir", "julgar procedente", "condenar") com a ausência da rubrica correspondente na memória de cálculo gerada.

### Correção correta
Incluir a rubrica "13º Salário Proporcional" na liquidação de sentença. O cálculo deve apurar a proporção de avos devidos (1/12 por mês de trabalho ou fração igual ou superior a 15 dias) com base no período trabalhado no ano da rescisão, aplicando-a sobre a base de cálculo da última remuneração do reclamante, conforme fixado em sentença.

### Base legal
Atraso ou não pagamento das verbas rescisórias devidas, como o 13º salário proporcional, atrai a aplicação das penalidades previstas nos artigos 467 e 477 da CLT.

### Exemplo prático
**Texto na sentença (padrão problemático):**
> ...julgo PROCEDENTES EM PARTE os pedidos formulados na inicial para condenar a reclamada ao pagamento das seguintes parcelas: (...) c) 13º salário proporcional (7/12); d) Férias proporcionais + 1/3...

**Interpretação correta:**
O comando "condenar a reclamada ao pagamento [...] c) 13º salário proporcional (7/12)" é diretivo e mandatório. O modelo deve:
1.  Identificar a verba `13º salário proporcional`.
2.  Extrair a proporção `(7/12)`.
3.  Inserir uma linha de cálculo específica para esta verba na planilha de liquidação.
4.  Calcular o valor correspondente (base de cálculo * 7 / 12).
A não inserção desta linha de cálculo, mesmo com o comando explícito, constitui o erro a ser corrigido.
---
## Engenharia Reversa — Discrepância: verba_ausente
<!-- Laboratório de Aprendizado | 13/03/2026 21:57 | Processo: 0011219-69.2024.5.15.0052 -->

### Padrão de erro identificado
Omissão, no cálculo liquidando, de verba rescisória expressamente deferida no dispositivo da sentença. O erro consiste na ausência da apuração e inclusão das "Férias Proporcionais + 1/3", resultando em uma liquidação de valor inferior ao devido.

### Como identificar na sentença
Verificar o dispositivo (parte conclusiva) da sentença em busca de palavras-chave como "defiro", "condeno", "julgo procedente o pedido de". Mapear todas as verbas listadas, especialmente "férias proporcionais", "férias + 1/3" ou "férias acrescidas do terço constitucional". Confrontar a lista de verbas deferidas com as rubricas presentes na planilha de cálculos. A ausência de uma rubrica correspondente na planilha indica a discrepância.

### Correção correta
Realizar a apuração da verba "Férias Proporcionais + 1/3" utilizando a base de cálculo definida na sentença (geralmente a última remuneração) e o período de avos determinado. O valor apurado para as férias deve ser acrescido de um terço (1/3), e o total inserido como um item distinto na planilha de liquidação, com a devida incidência de reflexos, se houver.

### Base legal
artigo 467 e 477 da CLT

### Exemplo prático
**Texto na sentença (padrão problemático):**
> "...julgo PROCEDENTES EM PARTE os pedidos para condenar a reclamada a pagar ao reclamante as seguintes parcelas: ... c) Férias proporcionais (10/12 avos), acrescidas do terço constitucional;"

**Interpretação correta:**
Ao processar o trecho acima, o modelo deve identificar a condenação expressa em "Férias proporcionais (10/12 avos), acrescidas do terço constitucional". Em seguida, deve verificar se a planilha de cálculo contém uma linha para essa verba. Se ausente, o sistema deve calcular o valor correspondente a 10/12 avos do salário base, somar 1/3 a esse resultado e incluir o montante final no resumo de débitos.
---
## Engenharia Reversa — Discrepância: verba_ausente
<!-- Laboratório de Aprendizado | 13/03/2026 21:57 | Processo: 0011219-69.2024.5.15.0052 -->

### Padrão de erro identificado
Omissão, na planilha de liquidação, da verba "Aviso Prévio Indenizado", apesar de seu deferimento explícito no dispositivo da sentença. Tal falha resulta em apuração a menor do crédito exequendo e, consequentemente, no cálculo incorreto de seus reflexos e das multas legais aplicáveis.

### Como identificar na sentença
Verificar o dispositivo da sentença em busca de termos como "deferir", "condenar", "pagamento de" ou "procedente" associados às expressões "aviso prévio indenizado", "aviso prévio" ou "projeção do aviso prévio". A análise da fundamentação também pode revelar o deferimento, mesmo que o dispositivo seja sucinto.

### Correção correta
Incluir a verba "Aviso Prévio Indenizado" na memória de cálculo. O valor deve ser apurado com base na última remuneração do reclamante, observando a proporcionalidade legal. É imperativo projetar o período correspondente para fins de cálculo dos reflexos deferidos em férias + 1/3, 13º salário, e FGTS + 40%, bem como para a correta apuração da base de cálculo das multas dos artigos 467 e 477 da CLT.

### Base legal
Fundamento normativo: artigo 467 e 477 da CLT. A omissão do aviso prévio indenizado impacta diretamente a base de cálculo para a incidência das penalidades previstas nos referidos artigos, que versam sobre o pagamento de verbas rescisórias incontroversas e o prazo para quitação da rescisão.

### Exemplo prático
**Texto na sentença (padrão problemático):**
> Pelo exposto, julgo PROCEDENTES EM PARTE os pedidos formulados para condenar a reclamada ao pagamento das seguintes parcelas: saldo de salário (5 dias), aviso prévio indenizado (33 dias), férias proporcionais + 1/3, 13º salário proporcional e multa do art. 477 da CLT.

**Interpretação correta:**
A expressão "condenar a reclamada ao pagamento [...] aviso prévio indenizado (33 dias)" é um comando de liquidação direto e obrigatório. O cálculo deve apurar o valor correspondente a 33 dias de remuneração a título de aviso prévio e, adicionalmente, projetar este período para recalcular a proporcionalidade de férias e 13º salário. A base de cálculo da multa do art. 477 também deve considerar o valor do aviso prévio não pago no prazo legal.
---
## Engenharia Reversa — Discrepância: verba_ausente
<!-- Laboratório de Aprendizado | 13/03/2026 21:58 | Processo: 0011219-69.2024.5.15.0052 -->

### Padrão de erro identificado
Omissão, na fase de liquidação, da apuração da multa prevista no artigo 467 da CLT, apesar de seu deferimento explícito no dispositivo da sentença. O erro consiste na não inclusão da parcela de 50% sobre as verbas rescisórias incontroversas, resultando em um cálculo a menor do crédito exequendo.

### Como identificar na sentença
Verificar o dispositivo (parte conclusiva) da sentença em busca de palavras-chave como "defiro a multa do art. 467 da CLT", "procedente o pedido de multa do artigo 467", "condeno ao pagamento da multa do 467", "multa celetista do artigo 467". A presença de condenação em verbas rescisórias (saldo de salário, aviso prévio, férias + 1/3, 13º salário) é um pré-requisito para a incidência da multa.

### Correção correta
Calcular o valor correspondente a 50% (cinquenta por cento) do montante das verbas rescisórias de natureza incontroversa (aquelas reconhecidas como devidas pela própria decisão). O valor apurado deve ser somado ao principal da condenação, sob uma rubrica específica: "Multa do Art. 467 da CLT".

### Base legal
Artigo 467 da Consolidação das Leis do Trabalho (CLT). A identificação das verbas rescisórias sobre as quais a multa incide é contextualizada pelo Artigo 477 da CLT.

### Exemplo prático
**Texto na sentença (padrão problemático):**
> "Diante do exposto, condeno a Reclamada ao pagamento das seguintes parcelas: saldo de salário, aviso prévio indenizado, férias proporcionais acrescidas de 1/3 e 13º salário proporcional. Defiro, outrossim, a aplicação da multa do art. 467 da CLT sobre as verbas rescisórias incontroversas."

**Interpretação correta:**
O comando judicial é explícito. O cálculo deve apurar os valores individuais de "saldo de salário", "aviso prévio", "férias + 1/3" e "13º salário". A soma desses valores formará a base de cálculo da multa. Sobre essa base, aplica-se o percentual de 50%. O resultado é uma nova verba, "Multa do Art. 467 da CLT", que deve ser incluída no cálculo final.
---
## Engenharia Reversa — Discrepância: verba_ausente
<!-- Laboratório de Aprendizado | 13/03/2026 21:58 | Processo: 0011219-69.2024.5.15.0052 -->

### Padrão de erro identificado
Omissão, na planilha de liquidação, de verba expressamente deferida no dispositivo da sentença. O erro consiste na falha em transpor um título condenatório (neste caso, a Multa do Art. 477 da CLT) para a memória de cálculo, resultando em apuração de crédito a menor para o exequente.

### Como identificar na sentença
Verificar o dispositivo da sentença (parte conclusiva) em busca de termos condenatórios como "defiro", "julgo procedente o pedido de", "condeno a reclamada ao pagamento de" associados a palavras-chave como "multa do art. 477", "multa do artigo 477", "multa do § 8º do art. 477 da CLT" ou "penalidade por atraso no pagamento das verbas rescisórias". Após identificar o deferimento, cruzar a informação com as rubricas listadas na planilha de cálculo para confirmar a ausência da verba.

### Correção correta
Incluir a rubrica "Multa do Art. 477 da CLT" na planilha de liquidação. O valor a ser atribuído deve corresponder ao último salário-base ou à remuneração base do reclamante, conforme definido no título executivo judicial. A base de cálculo deve ser apurada a partir dos documentos dos autos (e.g., TRCT, holerites) na data da rescisão.

### Base legal
Art. 477, § 6º e § 8º, da Consolidação das Leis do Trabalho (CLT). O § 8º estabelece a aplicação de multa em valor equivalente ao salário do empregado em caso de inobservância do prazo para pagamento das verbas rescisórias estipulado no § 6º. O Art. 467 da CLT trata de verbas incontroversas e não se confunde com esta penalidade, embora ambos tratem de sanções por inadimplemento.

### Exemplo prático
**Texto na sentença (padrão problemático):**
> [...] Pelo exposto, condeno a reclamada ao pagamento da multa prevista no § 8º do artigo 477 da CLT, uma vez que o pagamento das verbas rescisórias incontroversas se deu fora do prazo legal.

**Interpretação correta:**
O comando sentencial "condeno a reclamada ao pagamento da multa prevista no § 8º do artigo 477 da CLT" é um título executivo claro e direto. O modelo de IA deve:
1.  Identificar o deferimento explícito da verba.
2.  Mapear a rubrica "Multa do Art. 477 da CLT".
3.  Verificar a existência desta rubrica na planilha de cálculo.
4.  Na ausência, sinalizar a discrepância `verba_ausente` e proceder com a inclusão da verba, calculada com base no último salário do autor constante nos autos.
---
## Engenharia Reversa — Discrepância: verba_ausente
<!-- Laboratório de Aprendizado | 13/03/2026 21:58 | Processo: 0011219-69.2024.5.15.0052 -->

### Padrão de erro identificado
Omissão no cômputo de verba de natureza indenizatória (Vale-Alimentação) expressamente deferida no dispositivo da sentença, resultando em liquidação a menor do crédito exequendo. O erro comum é a não inclusão de benefícios que não compõem a base salarial principal, mas que são parte da condenação.

### Como identificar na sentença
Verificar o dispositivo da sentença em busca de palavras-chave como "Vale-Alimentação", "ticket alimentação", "auxílio alimentação", associadas a termos de condenação ("defiro", "condeno", "julgo procedente"). Confrontar a lista de verbas deferidas no dispositivo com as verbas efetivamente incluídas na planilha de cálculos. A ausência da verba na memória de cálculo, apesar de sua presença na condenação, confirma a discrepância.

### Correção correta
Proceder à apuração do valor devido a título de Vale-Alimentação, observando os parâmetros definidos na decisão (valor diário/mensal, período de apuração) e, se aplicável, as normas coletivas (CCT/ACT). Incluir a verba apurada como um item distinto na memória de cálculo, especificando sua natureza indenizatória e o período correspondente.

### Base legal
A obrigação de incluir a verba decorre da própria força da coisa julgada material (art. 502, CPC). A base legal para as multas decorrentes do atraso ou incorreção no pagamento das verbas rescisórias, que podem ser impactadas pela ausência do Vale-Alimentação, são os artigos 467 e 477, § 8º, da Consolidação das Leis do Trabalho (CLT).

### Exemplo prático
**Texto na sentença (padrão problemático):**
> Ante o exposto, julgo PROCEDENTE EM PARTE o pedido para condenar a reclamada ao pagamento das seguintes parcelas: ... [outras verbas] ...; e Vale-Alimentação, no valor de R$ 30,00 (trinta reais) por dia de trabalho efetivo, durante todo o pacto laboral, conforme CCT.

**Interpretação correta:**
Identificada a condenação expressa em "Vale-Alimentação". Extrair os parâmetros de cálculo: valor (R$ 30,00/dia) e período ("todo o pacto laboral"). O sistema deve apurar o número de dias efetivamente trabalhados no período contratual, multiplicar pelo valor diário e lançar o montante total como uma verba indenizatória na planilha de cálculo. A verba deve ser adicionada à base de cálculo do FGTS (se a CCT assim determinar) mas não deve integrar a base para férias, 13º salário ou RSR, salvo disposição expressa em contrário.
---
## Engenharia Reversa — Regra Preditiva: Horas Extras — Não pagamento de horas traba
<!-- Laboratório de Aprendizado | 13/03/2026 22:58 | Processo: 1002192-49.2025.5.02.0221 -->

### Padrão de erro identificado
A omissão sistemática, na fase de liquidação, do lançamento e parametrização da verba "Horas Extras" no sistema PJe-Calc, mesmo quando há condenação expressa na sentença. O erro consiste na falha em apurar e remunerar o labor extraordinário que excede a jornada legal ou contratual, quantificado diariamente através dos controles de ponto.

### Como identificar na sentença
Verificar o dispositivo da sentença em busca de expressões-chave como "defiro horas extras", "julgo procedente o pedido de horas extraordinárias", "pagamento de sobrejornada" ou "labor excedente à jornada legal". Em seguida, auditar a planilha de cálculos no PJe-Calc para confirmar se a verba correspondente foi omitida ou se seus parâmetros (base de cálculo, divisor, adicional) estão zerados ou ausentes.

### Correção correta
Inserir ou corrigir a verba "Horas Extras" no PJe-Calc. A apuração deve ser configurada para utilizar os cartões de ponto como fonte, calculando as horas que excedem os limites diários e semanais definidos na condenação. A base de cálculo deve ser composta por todas as parcelas de natureza salarial, conforme holerites e Súmula 264 do TST. O divisor e o adicional aplicáveis devem seguir o dispositivo sentencial ou a norma coletiva e, na sua ausência, os padrões legais (divisor 220, adicional de 50%).

### Base legal
Art. 59 da Consolidação das Leis do Trabalho (CLT).

### Exemplo prático
**Texto na sentença (padrão problemático):**
> Julgo PROCEDENTE o pedido para condenar a reclamada ao pagamento de horas extras, assim consideradas as excedentes à 8ª diária e 44ª semanal, com adicional de 50%, a serem apuradas com base nos cartões de ponto juntados aos autos, com reflexos em DSR, aviso prévio, 13º salários, férias + 1/3 e FGTS (8% + 40%).

**Interpretação correta:**
A sentença defere o pagamento de horas extras. Se a planilha de cálculos no PJe-Calc não contiver a apuração desta verba, a ação corretiva é:
1.  **Incluir a verba:** "Horas Extras com adicional de 50%".
2.  **Parametrizar a apuração:** Configurar o sistema para quantificar as horas excedentes à 8ª diária e 44ª semanal, utilizando os controles de frequência como fonte de dados.
3.  **Definir a base de cálculo:** Compor com o salário-base e demais verbas salariais.
4.  **Configurar os reflexos:** Parametrizar o cálculo dos reflexos sobre as verbas deferidas (DSR, aviso prévio, 13º, etc.), conforme dispositivo.
---
## Engenharia Reversa — Regra Preditiva: Reflexos em DSR, 13º Salário, Férias, Aviso
<!-- Laboratório de Aprendizado | 13/03/2026 22:58 | Processo: 1002192-49.2025.5.02.0221 -->

### Padrão de erro identificado
Ausência de integração das horas extras habituais na base de cálculo do Descanso Semanal Remunerado (DSR), 13º Salário, Férias acrescidas de 1/3, Aviso Prévio e FGTS. A parametrização no sistema PJe-Calc frequentemente não reflete a natureza salarial das horas extras, resultando em apuração a menor das verbas reflexas.

### Como identificar na sentença
Identificar no dispositivo da sentença a condenação em 'horas extras' e seus 'reflexos' ou 'integrações' em DSR, 13º salário, férias + 1/3, aviso prévio e FGTS. A presença desta condenação é o gatilho para uma auditoria rigorosa da base de cálculo das verbas acessórias no PJe-Calc.

### Correção correta
No sistema PJe-Calc, na aba 'Verbas', assegurar que a base de cálculo para '13º Salário', 'Férias + 1/3', 'Aviso Prévio' e 'FGTS' inclua a verba 'Horas Extras' e os 'Reflexos de Horas Extras em DSR'. A base de cálculo do FGTS deve incidir sobre todas as verbas de natureza salarial apuradas. Realizar contraprova com a média das horas extras extraída dos holerites e cartões de ponto.

### Base legal
Súmula 172 do TST (Repouso Remunerado. Horas Extras. Cálculo.), Súmula 45 do TST (Serviço Suplementar), Súmula 151 do TST (Férias) e Súmula 63 do TST (Fundo de Garantia).

### Exemplo prático
**Texto na sentença (padrão problemático):**
> '...julgo PROCEDENTE EM PARTE o pedido para condenar a reclamada ao pagamento de horas extras excedentes à 8ª diária e 44ª semanal, com adicional de 50%, e reflexos em DSR, 13º salário, férias + 1/3, aviso prévio e FGTS (8% + 40%).'

**Interpretação correta:**
A expressão 'reflexos em' determina que o valor apurado a título de horas extras habituais, já majorado pelo DSR, deve compor a base de cálculo de todas as demais verbas elencadas. O cálculo do 13º salário, por exemplo, não será apenas sobre o salário-base, mas sim sobre o [salário-base + média duodecimal das horas extras + DSR sobre horas extras]. Esta integração deve ser configurada explicitamente no PJe-Calc para cada verba reflexa.
---
## Exemplo de Aprendizado — 13/03/2026 22:58
<!-- Adicionado automaticamente pelo Laboratório de Aprendizado -->

**Fundamento jurídico:** Amostragem pericial — cross-reference sentença/liquidação
**Situação identificada:** Tese Vencedora: Não pagamento de horas extras

**Descrição:**
Tese provada pela perita na amostragem pericial: Não pagamento de horas extras. Registrar como playbook para orientar auditoria futura de cálculos similares.

<!-- Revisar e expandir com trecho real da sentença se necessário -->

---
## Exemplo de Aprendizado — 13/03/2026 22:58
<!-- Adicionado automaticamente pelo Laboratório de Aprendizado -->

**Fundamento jurídico:** Amostragem pericial — cross-reference sentença/liquidação
**Situação identificada:** Tese Vencedora: Não pagamento dos reflexos de horas extras sobre outras verbas trabalhistas

**Descrição:**
Tese provada pela perita na amostragem pericial: Não pagamento dos reflexos de horas extras sobre outras verbas trabalhistas. Registrar como playbook para orientar auditoria futura de cálculos similares.

<!-- Revisar e expandir com trecho real da sentença se necessário -->

---
## Engenharia Reversa — Regra Preditiva: Horas Extras — Não pagamento das horas trab
<!-- Laboratório de Aprendizado | 13/03/2026 23:09 | Processo: 1003964-47.2025.5.02.0221 -->

### Padrão de erro identificado
Omissão sistemática da parametrização da verba 'Horas Extras' no sistema PJe-Calc, mesmo quando a condenação judicial defere expressamente o pagamento das horas laboradas além da jornada contratual de 8 horas diárias. A parte reclamada, ao apresentar os cálculos de liquidação, deixa de configurar a apuração do sobrelabor, resultando em liquidação a menor do julgado.

### Como identificar na sentença
Verificar no dispositivo da sentença a presença de termos como "horas extras", "sobrejornada", "jornada extraordinária", "excedentes da 8ª diária" ou "além da jornada legal/contratual". Cruzar a existência desta condenação com a ausência da verba correspondente na planilha de cálculos ou nos parâmetros de configuração do PJe-Calc apresentados pela parte contrária.

### Correção correta
Acessar o PJe-Calc, na aba 'Verbas', e incluir ou ajustar a verba 'Horas Extras'. Parametrizar o cálculo para apurar as horas que excedam a 8ª diária, utilizando os cartões de ponto anexados ao processo como fonte de dados para a quantidade de horas. Aplicar o adicional normativo ou o definido em sentença (e.g., 50%). Utilizar os holerites como contraprova para dedução de valores eventualmente já pagos sob a mesma rubrica.

### Base legal
Art. 59 da CLT, que estabelece a duração normal do trabalho e as condições para a prestação de horas suplementares, remuneradas com acréscimo de, no mínimo, 50% (cinquenta por cento) sobre o valor da hora normal.

### Exemplo prático
**Texto na sentença (padrão problemático):**
> "Ante o exposto, condeno a reclamada ao pagamento de horas extras, consideradas como tais as que ultrapassarem a 8ª hora diária e a 44ª hora semanal, de forma não cumulativa, com adicional de 50% (cinquenta por cento) e reflexos em DSR, aviso prévio, 13º salários, férias + 1/3 e FGTS + 40%. Apuração a partir dos controles de frequência carreados aos autos."

**Interpretação correta:**
A decisão é cogente. O cálculo de liquidação deve, obrigatoriamente, conter a apuração das horas que excedem a jornada diária de 8 horas, conforme os registros de ponto. No PJe-Calc, deve-se criar uma verba específica para 'Horas Extras 50%', configurando-a para apurar a quantidade de horas excedentes da 8ª diária e aplicar o adicional. A ausência desta configuração no cálculo da reclamada é um erro material que deve ser impugnado e corrigido, pois desobedece a um comando sentencial explícito.
---
## Engenharia Reversa — Regra Preditiva: Reflexos das Horas Extras — Não integração
<!-- Laboratório de Aprendizado | 13/03/2026 23:09 | Processo: 1003964-47.2025.5.02.0221 -->

### Padrão de erro identificado
Omissão sistemática da inclusão da média das horas extras habitualmente prestadas na base de cálculo das verbas reflexas, como Repouso Semanal Remunerado (RSR), 13º Salário, Férias acrescidas do terço constitucional e Aviso Prévio. A discrepância decorre de uma parametrização incorreta ou incompleta no sistema PJe-Calc, que desconsidera a natureza salarial da média das horas extras para compor a remuneração base dessas parcelas.

### Como identificar na sentença
Analisar o dispositivo da sentença em busca de comandos como "reflexos das horas extras", "integração das horas extras" ou "repercussão das horas extras" em verbas contratuais e rescisórias. A auditoria deve focar na parametrização do PJe-Calc, verificando se a base de cálculo configurada para RSR, 13º Salário, Férias + 1/3 e Aviso Prévio inclui uma rubrica correspondente à "Média de Horas Extras". A ausência desta rubrica na composição é o indicador primário do erro.

### Correção correta
No sistema PJe-Calc, acessar a aba "Verbas" e editar a "Base de Cálculo" de cada parcela reflexa deferida (RSR, 13º Salário, Férias + 1/3, Aviso Prévio). Adicionar à base a verba correspondente à média mensal das horas extras apuradas. Essa média deve ser calculada com base nos valores totais de horas extras (valor da hora normal + adicional) apurados em cada mês da contratualidade, conforme demonstrado nos cartões de ponto e holerites utilizados como contraprova.

### Base legal
- **Súmula nº 45 do TST:** A remuneração do serviço suplementar, habitualmente prestado, integra o cálculo da gratificação natalina.
- **Súmula nº 172 do TST:** Computam-se no cálculo do repouso remunerado as horas extras habitualmente prestadas.
- **Súmula nº 376, II, do TST:** O valor das horas extras habitualmente prestadas integra o cálculo dos haveres trabalhistas, independentemente da limitação prevista no "caput" do art. 59 da CLT.

### Exemplo prático
**Texto na sentença (padrão problemático):**
> "Condeno a reclamada ao pagamento de horas extras excedentes à 8ª diária e 44ª semanal, com adicional de 50%, apuradas com base nos cartões de ponto, e seus respectivos reflexos em aviso prévio, 13º salários, férias + 1/3 e RSR."

**Interpretação correta:**
O comando "respectivos reflexos" impõe que a média das horas extras habituais, e não apenas o salário base, componha a base de cálculo das verbas mencionadas. A execução correta do cálculo é:
1.  **Apurar:** Calcular o valor total mensal das horas extras devidas.
2.  **Calcular Média:** Obter a média duodecimal (ou pelo número de meses trabalhados no período de apuração) desses valores.
3.  **Integrar:** Somar essa média ao salário base para formar a base de cálculo final de cada verba reflexa.
    -   **Exemplo (Férias):** Base de Cálculo = (Último Salário + Média das Horas Extras do período aquisitivo) * 1/3.
A simples aplicação do percentual de reflexo sobre o total de horas extras, sem a devida integração na base de cálculo das verbas principais, está incorreta e deve ser ajustada.
---
## Engenharia Reversa — Regra Preditiva: FGTS e Multa de 40% — Ausência de recolhime
<!-- Laboratório de Aprendizado | 13/03/2026 23:09 | Processo: 1003964-47.2025.5.02.0221 -->

### Padrão de erro identificado
Omissão sistemática na parametrização do sistema PJe-Calc, onde a base de cálculo para o FGTS e a multa de 40% não inclui as horas extras deferidas e seus reflexos (descanso semanal remunerado, 13º salário, férias + 1/3), apesar da natureza salarial incontroversa destas verbas. A empresa executada tende a configurar o cálculo considerando apenas as verbas principais, ignorando a incidência sobre as acessórias.

### Como identificar na sentença
Buscar pela condenação simultânea de "horas extras" e seus "reflexos" juntamente com "FGTS e multa de 40%". A ausência de uma ressalva expressa na sentença para excluir as horas extras da base de cálculo do FGTS é o principal indicador para auditar a parametrização. Frases-chave incluem: "recolhimento do FGTS sobre as verbas salariais da condenação", "FGTS incidente sobre as parcelas deferidas".

### Correção correta
No sistema PJe-Calc, acessar a configuração da verba "FGTS e Multa de 40%". Na aba "Base de Cálculo", marcar explicitamente as verbas de "Horas Extras" e todos os seus reflexos calculados (e.g., "Reflexos de Horas Extras em DSR", "Reflexos de Horas Extras em 13º Salário", etc.) como incidentes para o FGTS. A contraprova deve ser feita utilizando os holerites e cartões de ponto para validar os valores das horas extras que servem de base.

### Base legal
Art. 15 da Lei nº 8.036/90, que estabelece que para os fins de apuração do FGTS, considera-se remuneração todas as parcelas de natureza salarial pagas ou devidas ao trabalhador, incluindo as horas extras e seus reflexos.

### Exemplo prático
**Texto na sentença (padrão problemático):**
> "Condeno a reclamada ao pagamento de horas extras excedentes à 8ª diária, com adicional de 50% e reflexos em DSRs, 13º salários e férias acrescidas de 1/3. Defiro, outrossim, o recolhimento do FGTS e multa de 40% sobre as parcelas de natureza salarial ora deferidas."

**Interpretação correta:**
A expressão "sobre as parcelas de natureza salarial ora deferidas" determina que o valor total apurado para as horas extras, bem como o valor de cada um dos seus reflexos (DSRs, 13º, férias + 1/3), deve compor a base de cálculo sobre a qual incidirá a alíquota de 8% do FGTS. O montante resultante do FGTS apurado servirá, então, como base para o cálculo da multa de 40%. A parametrização no sistema de cálculo deve refletir essa inclusão integral.
---
## Exemplo de Aprendizado — 13/03/2026 23:09
<!-- Adicionado automaticamente pelo Laboratório de Aprendizado -->

**Fundamento jurídico:** Amostragem pericial — cross-reference sentença/liquidação
**Situação identificada:** Tese Vencedora: Não pagamento de horas extras

**Descrição:**
Tese provada pela perita na amostragem pericial: Não pagamento de horas extras. Registrar como playbook para orientar auditoria futura de cálculos similares.

<!-- Revisar e expandir com trecho real da sentença se necessário -->

---
## Exemplo de Aprendizado — 13/03/2026 23:09
<!-- Adicionado automaticamente pelo Laboratório de Aprendizado -->

**Fundamento jurídico:** Amostragem pericial — cross-reference sentença/liquidação
**Situação identificada:** Tese Vencedora: Não pagamento dos reflexos das horas extras em verbas salariais e rescisórias

**Descrição:**
Tese provada pela perita na amostragem pericial: Não pagamento dos reflexos das horas extras em verbas salariais e rescisórias. Registrar como playbook para orientar auditoria futura de cálculos similares.

<!-- Revisar e expandir com trecho real da sentença se necessário -->

---
## Exemplo de Aprendizado — 13/03/2026 23:09
<!-- Adicionado automaticamente pelo Laboratório de Aprendizado -->

**Fundamento jurídico:** Amostragem pericial — cross-reference sentença/liquidação
**Situação identificada:** Tese Vencedora: Não recolhimento do FGTS sobre as verbas apuradas

**Descrição:**
Tese provada pela perita na amostragem pericial: Não recolhimento do FGTS sobre as verbas apuradas. Registrar como playbook para orientar auditoria futura de cálculos similares.

<!-- Revisar e expandir com trecho real da sentença se necessário -->
