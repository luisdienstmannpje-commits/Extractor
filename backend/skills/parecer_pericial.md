Skill: Parecer Pericial Trabalhista — Estilo Padrão Ouro

## Objetivo

Esta skill define o **padrão de redação** do parecer técnico pericial que a IA deve seguir
ao descrever as parcelas apuradas em um processo trabalhista.

## Regras de redação (Tone of Voice)

- Sempre que for descrever uma verba deferida, **inicie a frase com a palavra `Apuração`**.
- Seja **objetivo**: não invente explicações longas, vá direto ao ponto.
- **Agrupe os reflexos no final da frase**, usando a expressão `com reflexos em ...`.
- Use **numeração alfabética** nas linhas das parcelas: `a)`, `b)`, `c)`, etc.
- Escreva em **português jurídico simples**, mantendo clareza para peritos, advogados e juízes.
- Evite qualquer marcação de Markdown (sem `*`, `#`, `**` ou listas com `-`); o resultado
  será colado em Excel ou Word simples.

## Formato esperado do bloco de parcelas

A IA deve retornar **apenas** o bloco de texto referente à seção
`I. PARCELAS APURADAS`, já numerado, seguindo o formato:

```text
a) TÍTULO DA VERBA: Apuração da/verba..., com reflexos em ...
b) TÍTULO DA VERBA: Apuração da/verba..., com reflexos em ...
c) TÍTULO DA VERBA: Apuração da/verba..., com reflexos em ...
...
```

Onde:

- As letras `a)`, `b)`, `c)` seguem em ordem;
- O **título da verba** vem em maiúsculas;
- O texto após os dois pontos sempre começa com `Apuração...`;
- Os reflexos, quando existirem, são agrupados no final com
  `com reflexos em ...`.

## Exemplos de redação (Few-Shot)

Use os exemplos abaixo como **padrão de estilo**. Ao redigir novas linhas,
imite a estrutura, o tom e a concatenação dos reflexos.

### Exemplo 1 — Adicional Noturno

```text
a) ADICIONAL NOTURNO: Apuração do adicional noturno, com reflexos no RSR, 13º salário, férias + 1/3 e FGTS + 40%.
```

### Exemplo 2 — Horas Extras e Reflexos

```text
b) HORAS EXTRAS E REFLEXOS: Apuração das horas extras durante todo o contrato de trabalho, utilizadas as Súmulas 264 e 347 do TST, observado o divisor 180, com percentual de 50%, com reflexos em repouso semanal remunerado, 13º salário, férias + 1/3 e FGTS + 40%.
```

### Notas para a IA

- Sempre que possível, **mencione o divisor e o percentual** quando tratar de horas extras.
- Quando os dados estruturados informarem os reflexos de uma verba, utilize-os
  para completar o trecho `com reflexos em ...`, respeitando o padrão dos exemplos.
- Se não houver reflexos conhecidos para uma verba específica, termine a frase
  com ponto e finalize (`.`), sem inventar reflexos.

