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
- `justica_gratuita`: true se o juiz deferiu os benefícios da justiça gratuita ao reclamante
- `custas_processuais`: quem paga as custas e sobre qual valor foram calculadas

### Verbas indenizatórias de valor fixo (Dispositivo)
- `dano_moral`: valor em R$ fixado expressamente — buscar "dano moral de R$", "indenização por
  danos morais no valor de R$". NÃO incluir na lista de verbas_deferidas.
- `dano_material`: valor em R$ fixado — buscar "dano material", "dano emergente", "lucros cessantes"

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
- `periodo`: período de apuração — buscar "de X a Y", "no período de X a X"
- `percentual`: percentual aplicável — ex: "50%", "30%", "100%"
- `quantidade_diaria`: quando houver — ex: "2h extras por dia", "30 min de intervalo suprimido"
- `base_calculo`: o que compõe a base — ex: "salário base", "salário base + adicional noturno"
- `valor_fixado`: se o juiz fixou valor certo em R$ ao invés de percentual
- `integracao_salarial`: true se a verba integra o salário para reflexos, false se indenizatória
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