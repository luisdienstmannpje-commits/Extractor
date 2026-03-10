# Skill: Filtro de Dispositivo — Localização Cirúrgica da Decisão

## Quando usar esta skill
Usar esta skill quando:
- O Smart Truncate não encontrou automaticamente o dispositivo
- A extração retornou muitos campos null inesperadamente
- O documento é muito longo (+40 páginas) e a janela de contexto foi insuficiente
- O PDF veio de OCR e os marcadores textuais estão corrompidos

## O que é o Dispositivo
É a parte final da sentença ou acórdão onde o juiz/desembargador
anuncia a decisão. É a única seção que importa para extração de verbas.
Tudo antes é fundamentação — relevante para contexto, não para extração.

## Marcadores de início do Dispositivo

### Sentenças (1ª instância)
- "DISPOSITIVO"
- "ISTO POSTO"
- "ANTE O EXPOSTO"
- "PELO EXPOSTO"
- "DIANTE DO EXPOSTO"
- "EM FACE DO EXPOSTO"
- "JULGO PROCEDENTE"
- "JULGO PARCIALMENTE PROCEDENTE"
- "JULGO IMPROCEDENTE"
- "CONDENO A RECLAMADA"

### Acórdãos (2ª instância)
- "ACORDAM"
- "ACÓRDÃO"
- "DOU PROVIMENTO"
- "NEGO PROVIMENTO"
- "DOU PARCIAL PROVIMENTO"
- "POR TAIS FUNDAMENTOS"
- "PELO QUE"

## Estratégia de busca em documentos corrompidos por OCR
Se os marcadores acima não forem encontrados por erro de digitação, tentar variações:
- "DISPOS|TIVO" → "DISPOSITIVO"
- "ANTE 0 EXPOSTO" → "ANTE O EXPOSTO" (zero no lugar do O)
- "ACOR0ÃO" → "ACÓRDÃO"
- "COND3NO" → "CONDENO"

## O que extrair a partir do Dispositivo
Ler do marcador encontrado até o final do documento. Ignorar tudo que vier antes.
Extrair apenas o que foi expressamente DEFERIDO.

### Campos prioritários no dispositivo
Ao localizar o dispositivo, buscar especificamente:

**Verbas calculáveis (entram em verbas_deferidas):**
- Horas extras e adicional respectivo (50%, 100%)
- Adicional noturno, de insalubridade, de periculosidade
- Intervalo intrajornada suprimido
- Saldo de salário, aviso prévio, 13º, férias, FGTS
- Diferenças salariais

**Verbas de valor fixo (campos próprios, fora de verbas_deferidas):**
- Dano moral → campo `dano_moral`
- Dano material → campo `dano_material`
- Multa art. 467 CLT → campo `multa_art_467`
- Multa art. 477 CLT → campo `multa_art_477`

**Parâmetros de cálculo:**
- Índice de correção monetária → campo `indice_correcao`
- Juros de mora → campo `juros_mora`
- Contribuições previdenciárias → campo `contribuicao_previdenciaria`
- IR retido na fonte → campo `ir_retido_fonte`
- Honorários advocatícios → campos `honorarios_sucumbenciais` e `percentual_honorarios`
- Custas → campo `custas_processuais`
- Justiça gratuita → campo `justica_gratuita`

## Fallback final
Se nenhum marcador for encontrado após todas as tentativas:
- Usar os últimos 30% do documento como aproximação do dispositivo
- Registrar em `observacoes` da primeira verba: "Dispositivo localizado por fallback — revisar manualmente"
- Preencher o máximo possível de campos com o que for encontrado nesse trecho