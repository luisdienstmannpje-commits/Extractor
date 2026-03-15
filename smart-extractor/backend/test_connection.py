"""
test_connection.py — Validação rápida da chave GEMINI_API_KEY com Gemini Flash.

Uso (a partir da pasta backend):
  python test_connection.py

Garante que o .env está carregado (via config) e que a API responde a uma
chamada simples "Hello World" com o modelo gemini-2.0-flash.
"""

import sys

def main():
    # Carrega config (e portanto backend/.env)
    try:
        from config import settings
    except Exception as e:
        print("ERRO: Não foi possível carregar config (verifique backend/.env):", e)
        return 1

    if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
        print("ERRO: GEMINI_API_KEY não está definida em backend/.env")
        return 1

    print("GEMINI_API_KEY carregada (prefixo:", settings.GEMINI_API_KEY[:10] + "...)")

    # Prioridade: modelo da cascata (ai_client) → 2.5 Flash (recomendado) → 1.5 Flash
    modelos_teste = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash"]
    from google import genai
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    for model in modelos_teste:
        print(f"Enviando chamada 'Hello World' para {model}...")
        try:
            response = client.models.generate_content(
                model=model,
                contents="Responda em uma única palavra: Hello",
            )
            text = (response.text or "").strip()
            if not text:
                print("ERRO: Resposta vazia do modelo")
                continue
            print("Resposta do modelo:", text[:200])
            print(f"OK — Conexão com Gemini Flash validada ({model}).")
            if model != "gemini-2.0-flash":
                print("AVISO: gemini-2.0-flash está deprecado; considere atualizar MODELS_CASCADE em ai_client.py para gemini-2.5-flash.")
            return 0
        except Exception as e:
            err = str(e)
            if "404" in err or "NOT_FOUND" in err:
                print(f"  {model} indisponível (404), tentando próximo...")
                continue
            print("ERRO na chamada à API:", e)
            return 1

    print("ERRO: Nenhum modelo Flash disponível. Verifique quota e nomes em https://ai.google.dev/gemini-api/docs/models")
    return 1

if __name__ == "__main__":
    sys.exit(main())
