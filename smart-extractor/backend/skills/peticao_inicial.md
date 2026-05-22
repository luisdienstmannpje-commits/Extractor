# Playbook de Extração: Petição Inicial

**OBJETIVO:** Você está lendo uma Petição Inicial trabalhista. O juiz AINDA NÃO JULGOU este processo. Seu objetivo é identificar QUAIS SÃO OS PEDIDOS do reclamante e os dados do contrato de trabalho.

**DIRETRIZES DE EXTRAÇÃO:**
1. **Foco na seção "DOS PEDIDOS" ou "REQUERIMENTOS":** Geralmente localizada no final da peça.
2. **Status Final:** Para TODAS as verbas extraídas, o `status_final` DEVE SER OBRIGATORIAMENTE `"pedido"`.
3. **Parâmetros do Pedido:** Se o reclamante especificar quantidades (ex: "2 horas extras por dia", "insalubridade em grau máximo"), coloque essa informação no campo `percentual`, `quantidade_diaria` ou `observacoes`.
4. **Jornada Alegada:** Preste atenção aos horários descritos na inicial para embasar os pedidos de horas extras.
5. **NÃO INVENTE CONDENAÇÕES:** A lista `verbas_deferidas` não deve ser preenchida. Apenas extraia o que está sendo requerido na lista `verbas_pedidas`.