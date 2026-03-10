# Skill: Leitura de Acórdão — Tribunal Regional do Trabalho (TRT)

## Quando usar esta skill
O documento é um ACÓRDÃO de 2ª instância (TRT) ou TST.
Palavras-chave que identificam este tipo: "acórdão", "turma", "desembargador",
"relator", "ementa", "recurso ordinário", "recurso de revista", "TRT", "TST".

## Estrutura esperada do documento
1. EMENTA — resumo do resultado (leitura rápida do placar, não é definitiva)
2. RELATÓRIO — histórico do processo e da sentença de origem
3. VOTO DO RELATOR — fundamentação do desembargador relator
4. VOTO VENCIDO (se houver) — posição minoritária, IGNORAR completamente
5. ACÓRDÃO (dispositivo) — resultado final do tribunal — FOCO PRINCIPAL

---

## Regras de extração

### Atenção: diferença crítica em relação à sentença
O acórdão REFORMA, MANTÉM ou EXCLUI verbas que já existiam na sentença.
O campo `status_final` de cada verba deve refletir o resultado APÓS o acórdão:
- `"mantida"` → o TRT confirmou o que o juiz havia concedido
- `"reformada"` → o TRT alterou valor, período ou percentual
- `"excluída"` → o TRT retirou a verba que o juiz havia concedido
- `"acrescida"` → o TRT adicionou verba que o juiz havia negado

### Identificação do processo (Relatório)
- `numero_processo`: formato CNJ — buscar no cabeçalho ou no Relatório
- `vara_trabalho`: vara de origem — buscar "oriundo da X Vara do Trabalho de..."
- `reclamante`: nome completo do trabalhador
- `reclamada`: nome completo da empresa
- `tipo_rito`: buscar no Relatório — "rito ordinário" ou "rito sumaríssimo"
- `funcao_reclamante`: cargo exercido — buscar no Relatório ou Voto
- `advogado_reclamante`: advogado do reclamante — buscar no Relatório ou cabeçalho
- `juiz_responsavel`: nome do desembargador relator que assinou o acórdão

### Datas (Relatório e Voto)
- `data_sentenca`: data do acórdão (decisão de 2ª instância) — buscar nesta ordem de prioridade:
  1. "Assinado digitalmente em DD/MM/AAAA" ou "Assinado em DD/MM/AAAA" (padrão PJe)
  2. "Publicado em DD/MM/AAAA"
  3. Data no cabeçalho do acórdão
  4. "Cidade, DD de mês de AAAA" ao final do dispositivo
- `data_ajuizamento`: data do ajuizamento original — geralmente no Relatório
- `data_admissao`: data de admissão do trabalhador — Relatório ou Voto
- `data_demissao`: data de demissão — Relatório ou Voto
- `motivo_rescisao`: tipo da rescisão reconhecido — Relatório ou Voto
- `tipo_contrato`: natureza jurídica reconhecida pelo TRT — CLT, pejotização, autônomo etc.

### Aviso prévio, CTPS e seguro-desemprego (Dispositivo do Acórdão)
- `aviso_previo_dias`: duração final do aviso prévio conforme o acórdão — incluir proporcionalidade
  da Lei 12.506/2011 se mantida ou alterada. Ex: "33 dias", "42 dias — 30 + 12 (Lei 12.506/2011)"
- `data_saida_ctps`: data de saída na CTPS com projeção do aviso prévio conforme o acórdão
- `anotacao_ctps`: se o TRT manteve ou determinou anotação da CTPS
- `seguro_desemprego`: resultado conforme o acórdão — guias deferidas, indenização substitutiva ou indeferido

### Regras especiais de FGTS (Dispositivo do Acórdão)
- `fgts_sobre_aviso_previo`: se o FGTS incide sobre aviso prévio — confirmar se o TRT manteve a regra
- `fgts_multa_40_aviso_previo`: se a multa de 40% incide sobre aviso prévio
- `fgts_sobre_ferias_indenizadas`: se o FGTS incide sobre férias indenizadas
- `fgts_periodo_completo`: período total coberto pelo FGTS conforme o acórdão
- `fgts_observacoes`: observações do TRT sobre o FGTS — reforma, inclusão de verbas na base etc.

### Parâmetros financeiros (Relatório e Voto)
- `salario_base`: salário reconhecido — pode estar no Voto se houve discussão sobre o valor.
  Buscar: "salário de R$", "remuneração de R$", "piso salarial de R$", "piso da categoria de R$",
  "salário normativo de R$", "salário contratual de R$", "remuneração mensal de R$".
  Usar o valor reconhecido pelo TRT, que pode diferir do fixado na sentença de origem.
- `jornada_contratual`: jornada contratada — buscar no Relatório ou Voto
- `horario_trabalho`: horário de entrada, saída e intervalo RECONHECIDO PELO TRIBUNAL —
  se o TRT alterou o que o juiz havia fixado, usar o horário do acórdão.
  Formato esperado: "07h00 às 17h00 com 1h de intervalo"

### Parâmetros de cálculo (Dispositivo do Acórdão)
- `indice_correcao`: usar o índice fixado no acórdão — pode ter sido alterado em relação à sentença
- `juros_mora`: juros fixados no acórdão
- `contribuicao_previdenciaria`: registrar determinação do acórdão (pode ter sido alterada)
- `ir_retido_fonte`: responsável conforme o acórdão

### Honorários, custas e justiça gratuita (Dispositivo)
- `honorarios_sucumbenciais`: resultado após o acórdão — o TRT pode ter alterado o responsável
- `percentual_honorarios`: percentual conforme o acórdão
- `justica_gratuita`: true se mantida ou acrescida pelo TRT
- `custas_processuais`: conforme determinação do acórdão

### Verbas indenizatórias de valor fixo
- `dano_moral`: valor APÓS o acórdão — pode ter sido mantido, aumentado, reduzido ou excluído.
  Registrar o valor final. Se excluído, registrar null.
- `dano_material`: mesmo critério que dano_moral

### Multas rescisórias
- `multa_art_467`: resultado após o acórdão — mantida, excluída ou acrescida
- `multa_art_477`: mesmo critério

### Verbas deferidas — lista APÓS reforma (Dispositivo do Acórdão)
Ler o ACÓRDÃO (dispositivo final), NÃO o Voto.
Verbas não mencionadas no acórdão = mantidas como na sentença de origem.

Para cada verba:
- `nome`: nome da verba
- `status_final`: "mantida", "reformada", "excluída" ou "acrescida"
- `periodo`: período final após o acórdão
- `percentual`: percentual final — se o TRT reduziu de 50% para 40%, registrar "40%"
- `quantidade_diaria`: quantidade diária reconhecida — se alterada pelo TRT, usar o novo valor
- `base_calculo`: base de cálculo conforme o acórdão
- `valor_fixado`: se o TRT fixou valor certo
- `integracao_salarial`: conforme o acórdão
- `reflexos`: reflexos mantidos ou acrescidos pelo TRT.
  Buscar frases de gatilho: "com reflexos em", "repercussão em", "com repercussão em",
  "integrando o salário para fins de", "com integração salarial em", "incidindo sobre".
  Se o TRT excluiu reflexos anteriormente deferidos, registrar em `observacoes`.
- `observacoes`: registrar a reforma, ex: "Reduzido de 50% para 40% pelo TRT" ou
  "Período reduzido de 01/2018-12/2020 para 01/2019-12/2020"

### Frases típicas do dispositivo e o que significam
- "dou provimento para EXCLUIR a condenação em..." → status_final: "excluída"
- "dou parcial provimento para REDUZIR o percentual de X para Y" → status_final: "reformada"
- "dou provimento para ACRESCER a condenação em..." → status_final: "acrescida"
- "NEGO provimento" / "mantenho a sentença" → todas as verbas = "mantida"
- "dou provimento ao recurso DA RECLAMADA" → empresa ganhou, verbas provavelmente excluídas/reduzidas
- "dou provimento ao recurso DO RECLAMANTE" → trabalhador ganhou, verbas provavelmente acrescidas

### Armadilhas comuns
- A EMENTA resume mas pode omitir detalhes — sempre confirmar no dispositivo final
- Votos vencidos NÃO integram o resultado — ignorar completamente
- Um acórdão pode julgar recursos de AMBAS as partes — analisar cada provimento separadamente
- "Dou provimento em parte" pode excluir algumas verbas e manter outras — listar cada uma
- Índice de correção e juros podem ter sido alterados — usar SEMPRE o mais recente (acórdão)

### Intervalo intrajornada — regra pós-Reforma Trabalhista (contratos a partir de 11/11/2017)
- Natureza **indenizatória** para contratos após a Reforma — NÃO gera reflexos
- Natureza **salarial** para contratos anteriores à Reforma — gera reflexos normalmente
- O TRT pode ter alterado a natureza em relação à sentença — usar sempre o entendimento do acórdão
- Gatilhos: "supressão do intervalo", "intervalo intrajornada", "art. 71, § 4º da CLT",
  "natureza indenizatória", "sem reflexos"
- Registrar em `integracao_salarial`: false se pós-Reforma, true se pré-Reforma
- Registrar em `observacoes`: "Natureza indenizatória — sem reflexos (pós-Reforma)" ou
  "Natureza salarial — com reflexos (pré-Reforma)"

### Aviso prévio proporcional — Lei 12.506/2011
- Se mantido ou acrescido pelo TRT, verificar se o acórdão menciona a proporcionalidade
- Buscar: "aviso prévio proporcional", "Lei 12.506", "acrescido de X dias"
- Registrar duração total em `observacoes` da verba (ex: "42 dias — 30 + 12 pela Lei 12.506/2011")
- Se o TRT alterou a duração do aviso em relação à sentença, registrar `status_final`: "reformada"