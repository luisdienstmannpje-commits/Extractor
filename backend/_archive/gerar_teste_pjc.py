"""
Rode este script na pasta backend do projeto:

    cd ~/Desktop/extractor/smart-extractor/backend
    python gerar_teste_pjc.py

O arquivo .pjc será gerado na mesma pasta.
"""

from services.pjc_exporter import exportar_pjc, gerar_nome_arquivo

dados = {
    "numero_processo":       "0010070-87.2020.5.03.0092",
    "reclamante":            "EDER PEREIRA MARTINS",
    "reclamada":             "PROAIR SERVICOS AUXILIARES DE TRANSPORTE AEREO LTDA",
    "data_admissao":         "01/02/2017",
    "data_demissao":         "08/05/2019",
    "data_ajuizamento":      "28/01/2020",
    "divisor_horas":         "180",
    "fgts_periodo_completo": True,
}

nome = gerar_nome_arquivo(dados)
conteudo = exportar_pjc(dados)

with open(nome, "wb") as f:
    f.write(conteudo)

print(f"✅ Arquivo gerado: {nome}")
print(f"   Tamanho: {len(conteudo):,} bytes")
print()
print("Agora importe esse arquivo no PJeCalc:")
print("  Menu → Importar cálculo → selecionar o arquivo acima")