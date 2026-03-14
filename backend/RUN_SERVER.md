# Como subir o servidor (logs no terminal)

Os logs do pipeline ([LAB], [FINDER], [AI], [ENGINE], [KB], etc.) so aparecem no terminal se o servidor for iniciado **sempre** desta forma:

- **PORT=8001** (ou a porta que quiser) — para a mensagem de startup mostrar a URL correta
- **python -u** — saida desbloqueada (unbuffered)
- **uvicorn main:app --host 0.0.0.0 --port 8001**

## Forma recomendada: usar o script

### Git Bash / MINGW64 (recomendado)

```bash
cd backend
./run_server.sh
```

ou:

```bash
cd backend
bash run_server.sh
```

### CMD / PowerShell

```cmd
cd backend
run_server.bat
```

No PowerShell, se preferir uma linha:

```powershell
cd backend; $env:PORT="8001"; .\venv\Scripts\python.exe -u -m uvicorn main:app --host 0.0.0.0 --port 8001
```

## Depois de subir

Abra no navegador **a mesma porta** que o Uvicorn mostrar, por exemplo:

- `http://localhost:8001/`

Se abrir em outra porta (ex.: 8000), o frontend nao conversa com o backend e os botoes (Analisar, etc.) nao disparam os logs.

## Por que assim?

- Sem `PORT=8001`, a mensagem "[MAIN] Abra o sistema em..." pode mostrar 8000 enquanto o Uvicorn esta em 8001.
- Sem `python -u`, os prints ficam em buffer e o terminal parece parado durante o processamento.
- O script garante que voce (e qualquer um) rode sempre do mesmo jeito, com logs visiveis.
