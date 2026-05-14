"""
patch_generator.py
Aplica patch cirúrgico em memoria_calculo/generator.py:
  - Adiciona parâmetro explicacoes à função gerar_memoria()
  - Adiciona campo "explicacoes" ao dict memoria
  - Compatível com chamadas existentes (parâmetro opcional)

Executar de dentro de backend/:
    python patch_generator.py
"""
import os, py_compile

TARGET = os.path.join("memoria_calculo", "generator.py")

with open(TARGET, "r", encoding="utf-8") as f:
    src = f.read()

# ── Patch 1: assinatura da função — adiciona explicacoes após avisos_dedup ───
OLD_SIG = (
    "def gerar_memoria(\n"
    "    job_id: str,\n"
    "    dados: dict,\n"
    "    model_used: str,\n"
    "    doc_type: str,\n"
    "    avisos_dedup: list[str] | None = None,\n"
    ") -> dict:"
)
NEW_SIG = (
    "def gerar_memoria(\n"
    "    job_id: str,\n"
    "    dados: dict,\n"
    "    model_used: str,\n"
    "    doc_type: str,\n"
    "    avisos_dedup: list[str] | None = None,\n"
    "    explicacoes: list | None = None,\n"
    ") -> dict:"
)

# ── Patch 2: campo no dict memoria — após deduplicacao ───────────────────────
OLD_DEDUP = (
    '        "deduplicacao": {\n'
    '            "duplicatas_removidas": len(avisos_dedup),\n'
    '            "avisos": avisos_dedup,\n'
    '        },\n'
    '    }'
)
NEW_DEDUP = (
    '        "deduplicacao": {\n'
    '            "duplicatas_removidas": len(avisos_dedup),\n'
    '            "avisos": avisos_dedup,\n'
    '        },\n'
    '        "explicacoes": explicacoes or [],\n'
    '    }'
)

assert OLD_SIG in src,   "❌ Patch 1 falhou: assinatura não encontrada"
assert OLD_DEDUP in src, "❌ Patch 2 falhou: bloco deduplicacao não encontrado"

src = src.replace(OLD_SIG, NEW_SIG)
src = src.replace(OLD_DEDUP, NEW_DEDUP)

with open(TARGET, "w", encoding="utf-8") as f:
    f.write(src)

try:
    py_compile.compile(TARGET, doraise=True)
    print(f"✅ {TARGET} atualizado e validado — sem erros de sintaxe")
except py_compile.PyCompileError as e:
    print(f"❌ Erro de sintaxe após patch: {e}")