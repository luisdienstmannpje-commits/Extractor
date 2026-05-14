# Fixtures de Teste — Smart Extractor

## Estrutura

```
fixtures/
├── pdfs/       ← PDFs reais anonimizados (não comitar dados sensíveis)
├── expected/   ← JSON com resultado esperado validado pela perita
└── README.md   ← este arquivo
```

## Como adicionar um novo caso de teste

1. Anonimize o PDF (remova CPF, nome real, CNPJ se necessário)
2. Coloque em `pdfs/processo_XXX.pdf` (numeração sequencial)
3. Crie o JSON esperado em `expected/processo_XXX.json`
4. **Valide o JSON com a perita** antes de comitar — este é o gabarito
5. Rode `python tests/run_benchmark.py` — deve aparecer o novo processo
6. Comite os dois arquivos juntos

## Formato do JSON esperado

```json
{
  "numero_processo": "0001234-56.2023.5.04.0001",
  "reclamante": "Nome Anonimizado",
  "reclamada": "Empresa XYZ Ltda",
  "data_admissao": "15/01/2020",
  "data_demissao": "30/06/2023",
  "salario_base": "R$ 3.500,00",
  "motivo_rescisao": "Sem justa causa",
  "indice_correcao": "IPCA-E (pré-ajuizamento) / SELIC (pós-ajuizamento) — ADC 58/STF",
  "juros_mora": "SELIC",
  "data_sentenca": "10/03/2024",
  "vara_trabalho": "1ª Vara do Trabalho de Porto Alegre",
  "tipo_rito": "Ordinário",
  "justica_gratuita": true,
  "verbas_deferidas": [
    {"nome": "Horas Extras", "status_final": "deferida"},
    {"nome": "Férias Proporcionais + 1/3", "status_final": "deferida"},
    {"nome": "13º Salário Proporcional", "status_final": "deferida"}
  ],
  "_meta": {
    "pdf_nome": "processo_001.pdf",
    "doc_type": "sentenca",
    "validado_por": "perita",
    "data_validacao": "2025-01-01",
    "observacoes": "Sentença TRT4 ordinária, 3 verbas principais"
  }
}
```

## Campos obrigatórios no JSON

Os campos com `_` inicial são metadados e não são validados pelo benchmark.

Campos obrigatórios para validação:
- `numero_processo`
- `reclamante`
- `reclamada`
- `data_admissao`
- `data_demissao`
- `salario_base`
- `motivo_rescisao`
- `data_sentenca`
- `verbas_deferidas` (lista com pelo menos `nome` e `status_final`)

## Critério de acerto por campo

| Campo | Critério de match |
|-------|------------------|
| `numero_processo` | Exato |
| `data_*` | Exato (formato DD/MM/AAAA) |
| `salario_base` | Valor numérico ± 1% |
| `reclamante` / `reclamada` | Case-insensitive, ignora acentuação |
| `motivo_rescisao` | Case-insensitive, substring bidirecional |
| `indice_correcao` | Case-insensitive, contém o índice principal |
| `verbas_deferidas` | Verifica se cada `nome` esperado existe na lista extraída (fuzzy 85%) |
