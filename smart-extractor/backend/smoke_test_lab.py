import sys
import os
sys.path.append(os.getcwd())
print("--- INICIANDO TESTE ---")
try:
    import services.lab.learning_io
    import services.lab.extractors
    import services.lab.titulo_executivo
    import services.lab.discrepancy
    import services.lab.style_transfer
    import services.lab.self_healing
    from services.learning_engine import salvar_aprendizado
    print("SUCESSO")
except Exception as e:
    print(f"ERRO: {e}")