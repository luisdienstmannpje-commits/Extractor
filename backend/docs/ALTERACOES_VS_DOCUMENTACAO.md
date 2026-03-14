# Alterações feitas vs. documentação (README + docs/)

Este documento lista **apenas as alterações feitas no código** (configuração em nova máquina + preparação para Teste 1) e confirma se há risco de **regressão** ou **divergência** em relação ao que está descrito no README e na pasta `docs/`.

---

## Resumo executivo

- **Pipeline (10 passos)**: não foi alterado. Ordem, contratos e módulos são os mesmos descritos em `PIPELINE.md` e `README.md`.
- **Regras jurídicas**: nenhuma regra foi adicionada, removida ou alterada. Motor de regras, Shadow Rules e Knowledge Base seguem como documentados.
- **Estrutura (pastas, arquivos principais)**: inalterada. Foi criado apenas **um arquivo novo** de utilitário: `test_connection.py`.
- As mudanças feitas são: **configuração de ambiente** (`.env`, Tesseract no Windows) e **atualização do modelo Gemini** (2.0-flash deprecado → 2.5-flash). Nenhuma delas altera regras, pipeline ou estrutura documentada.

---

## 1. config.py — carregamento do .env

**O que a documentação diz**
- README: *"config.py: Variáveis de ambiente (GEMINI_API_KEY, Firebase, MAX_FILE_SIZE_MB, SCHEMA_VERSION etc.)"*
- Nenhum doc exige como o `.env` deve ser carregado.

**O que foi alterado**
- Antes: `load_dotenv()` (carrega a partir do diretório de trabalho atual).
- Depois: `load_dotenv(Path(__file__).resolve().parent / ".env")` — carrega sempre `backend/.env`, independente de onde o processo foi iniciado.

**Regressão?** Não. Mesmas variáveis; comportamento mais previsível em nova máquina ou ao rodar da raiz do projeto.

---

## 2. services/sentence_finder.py — Tesseract no Windows

**O que a documentação diz**
- README / CODE_MAP: *"sentence_finder: extract_sentence_from_pdf; tipo de doc; OCR híbrido; bloco de decisão"*.
- Nenhum doc define onde deve estar o executável do Tesseract.

**O que foi alterado**
- Em Windows, se existir `C:\Program Files\Tesseract-OCR\tesseract.exe`, esse caminho é definido em `pytesseract.pytesseract.tesseract_cmd`.
- Objetivo: evitar `TesseractNotFoundError` quando o Tesseract não está no PATH.

**Regressão?** Não. Só afeta ambiente Windows; lógica de extração e de classificação de documento permanece a mesma.

---

## 3. services/ai_client.py — modelo Gemini

**O que a documentação diz**
- README / PIPELINE: *"IA: ai_client — Gemini (Flash → Pro), playbook, truncagem"* e *"cascata Flash → Pro"*.
- Nenhum doc fixa o nome exato do modelo (ex.: "gemini-2.0-flash").

**O que foi alterado**
- `MODELS_CASCADE`: primeiro modelo de `"gemini-2.0-flash"` para `"gemini-2.5-flash"` (2.0-flash está deprecado e retorna 404 para chaves novas).
- `CHARS_LIMIT`: adicionada entrada para `gemini-2.5-flash`; mantida `gemini-2.0-flash` para compatibilidade.
- `gerar_parcelas_parecer`: valor padrão de `model_name` de `"gemini-2.0-flash"` para `"gemini-2.5-flash"`.

**Regressão?** Não. Contrato continua: cascata Flash → Pro; mesma API e mesmo fluxo. Apenas o identificador do modelo foi atualizado para um que ainda está disponível na API.

---

## 4. test_connection.py (novo arquivo)

**O que a documentação diz**
- Nenhum doc menciona este script. É utilitário de diagnóstico.

**O que foi feito**
- Criado `backend/test_connection.py`: valida carregamento do `.env`, existência de `GEMINI_API_KEY` e uma chamada simples ao Gemini Flash (com fallback de modelos).

**Regressão?** Não. Não faz parte do pipeline nem dos contratos descritos em README/docs; não altera comportamento do extrator.

---

## O que NÃO foi alterado (conferido)

- **workers/processor.py**: nenhuma alteração. Os 10 passos, ordem e chamadas estão como em `PIPELINE.md`.
- **legal_engine/**: nenhuma alteração em regras, engine, rule_registry ou dynamic_rule_loader.
- **models.py**: não alterado.
- **learning_engine.py**, **knowledge_base.py**, **main.py**: não alterados.
- **Skills (.md)**, **frontend**: não alterados.
- **Contrato de `process_lawsuit_pdf`**: entrada e retorno (status, data, alertas_juridicos, regras_aplicadas, etc.) permanecem como documentados.

---

## Conclusão

- O código que você trouxe do GitHub **foi modificado** apenas nos pontos acima (config, sentence_finder, ai_client e novo script de teste).
- Nenhuma **regra**, **pipeline** ou **estrutura** documentada no README e em `docs/` foi alterada de forma que cause regressão ou comportamento diferente do desenhado.
- As mudanças são de **ambiente** (`.env`, Tesseract) e de **disponibilidade de API** (modelo Gemini), mantendo o mesmo desenho do sistema.

Se quiser reverter apenas as alterações de “nova máquina”, basta desfazer as mudanças em `config.py`, `sentence_finder.py` e `ai_client.py` (e opcionalmente remover `test_connection.py`). O restante do repositório está alinhado com a documentação.
