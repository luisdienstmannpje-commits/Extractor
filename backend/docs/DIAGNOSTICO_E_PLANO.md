# Diagnóstico arquitetural e plano de documentação

## TAREFA 1 — Diagnóstico

### 1. Avaliação da arquitetura atual

- **Pontos fortes**
  - Pipeline linear e bem definido (10 passos em `workers/processor.py`), fácil de seguir.
  - Legal Rule Engine modular: regras isoladas por arquivo, descoberta automática, hierarquia normativa clara (10–50).
  - Separação razoável: API (`main`), orquestração (`processor`), serviços (extração, validação, cálculo, persistência), motor de regras (`legal_engine/` + `jurisprudencia/`).
  - Contratos estáveis: `validar_dados` / `validar_dados_completo`, `process_lawsuit_pdf`, `gerar_explicacoes`, `LegalRule.aplicar(contexto)`.
  - Testes por regra em `tests/jurisprudencia/` e testes de serviços dedicados.

- **Pontos de atenção**
  - Toda a documentação está em um único README longo (arquitetura + pipeline + regras + mapa de arquivos), o que obriga a IA a carregar muito contexto de uma vez.
  - Regras jurídicas em dois lugares (`legal_engine/rules/` e `jurisprudencia/`) com IDs que podem duplicar (registry ignora o segundo); não é óbvio para um agente onde colocar uma regra nova.
  - Dependências de `main.py` para `pjc_exporter` e `excel_exporter` não estão no tree do README (módulos podem estar fora do backend ou com outro nome), gerando dúvida na navegação.

### 2. Riscos de manutenção ou acoplamento

- **processor.py** concentra orquestração, limpeza pós-IA e derivações (jornada, divisor_horas, prescrição, etc.). Qualquer mudança em passo ou contrato pode impactar testes e memória de cálculo.
- **legal_validator.py** é uma fina camada sobre o engine; quem não lê a doc pode achar que ainda existe lógica de validação dentro dele.
- Duas fontes de regras (`legal_engine/rules/` e `jurisprudencia/`) sem critério explícito “quando usar qual” aumenta risco de regra no lugar errado ou ID duplicado.
- **models.py** (ProcessoTrabalhista) é contrato global: novos campos exigem cuidado com cache (SCHEMA_VERSION) e com engine (ContextoJuridico / `_dict_para_contexto`).

### 3. Pontos que dificultam navegação por IA

- **Contexto único e grande**: README único com estrutura + pipeline + lista de regras + função de cada arquivo → a IA precisa ler ~200 linhas para qualquer tarefa pontual, aumentando tokens.
- **Falta de “entrada rápida”**: não há um índice do tipo “para alterar X, leia primeiro os arquivos Y e Z”.
- **Regras sem índice por domínio**: não há um único lugar que diga “tudo sobre FGTS está em A, B, C” ou “tudo sobre datas em D, E”.
- **Proibições e convenções** (não quebrar pipeline, uma regra por arquivo, não remover lógica jurídica) estão no final do README; um agente que comece por outro arquivo pode não vê-las.

### 4. Melhorias estruturais possíveis (apenas documentação)

- Dividir a documentação em **backend/docs/** com arquivos temáticos (visão do sistema, pipeline, mapa de código, regras para IA).
- Manter o **README** como índice e visão geral, com links para `docs/` para desenvolvimento assistido por IA.
- Incluir em **AI_RULES.md** as regras críticas e o fluxo “antes de alterar X, consulte Y”.
- Criar **CODE_MAP.md** em formato de tabela “arquivo → responsabilidade” e “domínio → arquivos” para busca rápida sem ler o README inteiro.

---

## TAREFA 3 — Plano de refatoração segura (só documentação)

Nenhuma alteração em código ou comportamento; apenas reorganização de documentação.

| Etapa | Ação | Critério de sucesso |
|-------|------|---------------------|
| 1 | Criar `backend/docs/` | Pasta existe. |
| 2 | Criar `docs/SYSTEM_OVERVIEW.md` | Visão do produto, componentes e fluxo em 1 página. |
| 3 | Criar `docs/PIPELINE.md` | Descrição dos 10 passos e dependências entre passos. |
| 4 | Criar `docs/CODE_MAP.md` | Tabela arquivo → responsabilidade; índice por domínio (FGTS, datas, regras, etc.). |
| 5 | Criar `docs/AI_RULES.md` | Regras críticas, o que não fazer, onde ler primeiro para cada tipo de mudança. |
| 6 | Atualizar `README.md` | Adicionar seção “Documentação para desenvolvimento assistido por IA” com link para `docs/` e lista dos 4 arquivos. |
| 7 | Rodar `pytest -q` | Todos os testes passando (zero mudança funcional). |

Ordem de execução: 1 → 2, 3, 4, 5 (podem ser em paralelo) → 6 → 7.
