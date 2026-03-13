"""
patch_processor.py
Aplica patch cirúrgico em workers/processor.py:
  - Passa explicacoes=explicacoes na chamada gerar_memoria() (step 10)

Executar de dentro de backend/:
    python patch_processor.py
"""
import os, py_compile

TARGET = os.path.join("workers", "processor.py")

with open(TARGET, "r", encoding="utf-8") as f:
    src = f.read()

OLD_CALL = (
    "    gerar_memoria(\n"
    "        job_id=job_id or str(doc_id),\n"
    "        dados=dados_finais,\n"
    "        model_used=ai_result[\"model_used\"],\n"
    "        doc_type=doc_type,\n"
    "        avisos_dedup=avisos_dedup,\n"
    "    )"
)
NEW_CALL = (
    "    gerar_memoria(\n"
    "        job_id=job_id or str(doc_id),\n"
    "        dados=dados_finais,\n"
    "        model_used=ai_result[\"model_used\"],\n"
    "        doc_type=doc_type,\n"
    "        avisos_dedup=avisos_dedup,\n"
    "        explicacoes=explicacoes,\n"
    "    )"
)

assert OLD_CALL in src, "❌ Patch falhou: bloco gerar_memoria() não encontrado"

src = src.replace(OLD_CALL, NEW_CALL)

with open(TARGET, "w", encoding="utf-8") as f:
    f.write(src)

try:
    py_compile.compile(TARGET, doraise=True)
    print(f"✅ {TARGET} atualizado e validado — sem erros de sintaxe")
except py_compile.PyCompileError as e:
    print(f"❌ Erro de sintaxe após patch: {e}")