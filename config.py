import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 200))
    MAX_CHARS_CONTEXT = int(os.getenv("MAX_CHARS_CONTEXT", 25000))
    OCR_CHARS_THRESHOLD = int(os.getenv("OCR_CHARS_THRESHOLD", 50))
    RAPIDFUZZ_THRESHOLD = int(os.getenv("RAPIDFUZZ_THRESHOLD", 85))
    WORKERS_SIMULTANEOS = int(os.getenv("WORKERS_SIMULTANEOS", 3))
    PDFS_GRATUITOS_POR_USUARIO = int(os.getenv("PDFS_GRATUITOS_POR_USUARIO", 10))

    # ── Versionamento de Schema ───────────────────────────────────────────────
    # REGRA: incremente SCHEMA_VERSION sempre que qualquer um destes mudar:
    #   • campos adicionados/removidos em models.py
    #   • troca de modelo de IA (gemini-2.0-flash → outro)
    #   • mudança estrutural em playbook .md que altera campos extraídos
    #   • novo extrator HIGH/MEDIUM no pre_extractor.py
    #
    # Formato: "MAJOR.MINOR.PATCH"
    #   MAJOR → mudança incompatível (campos removidos ou renomeados)
    #   MINOR → campos novos adicionados ao schema
    #   PATCH → ajuste de prompt/playbook/regex sem mudança de campos
    #
    # Cache com versão diferente é descartado automaticamente na próxima leitura
    # (lazy invalidation — sem custo de varredura em batch, sem limpeza manual).
    #
    # Histórico:
    #   2.0.0 — Estrutura inicial com 33 campos
    #   2.1.0 — +12 campos (advogado, juiz, FGTS, aviso prévio etc.)
    #   2.2.0 — Jobs persistentes, 3 novos tipos de documento
    #   2.3.0 — Skill 7 integrada (pre_extractor HIGH/MEDIUM ativos)
    SCHEMA_VERSION: str = os.getenv("SCHEMA_VERSION", "2.3.0")

settings = Config()