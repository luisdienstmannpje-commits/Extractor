"""
normalizer.py
Camada 5 — Sentence Understanding Layer

Mapeia variações linguísticas da linguagem jurídica trabalhista
para chaves padronizadas do sistema.

Extensível via MAPA_NORMALIZACAO — sem necessidade de alterar lógica.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger("[NORMALIZER]")

# ---------------------------------------------------------------------------
# MAPA PRINCIPAL — variação linguística → chave padronizada
# ---------------------------------------------------------------------------

MAPA_NORMALIZACAO: dict[str, str] = {

    # --- 13º Salário ---
    "décimo terceiro salário proporcional":     "decimo_terceiro_proporcional",
    "décimo terceiro proporcional":             "decimo_terceiro_proporcional",
    "13° proporcional":                         "decimo_terceiro_proporcional",
    "13º proporcional":                         "decimo_terceiro_proporcional",
    "gratificação natalina proporcional":       "decimo_terceiro_proporcional",
    "décimo terceiro salário":                  "decimo_terceiro",
    "13° salário":                              "decimo_terceiro",
    "13º salário":                              "decimo_terceiro",
    "gratificação natalina":                    "decimo_terceiro",

    # --- Férias ---
    "férias proporcionais + 1/3":               "ferias_proporcionais_com_terco",
    "férias proporcionais mais um terço":       "ferias_proporcionais_com_terco",
    "férias + um terço":                        "ferias_proporcionais_com_terco",
    "férias proporcionais":                     "ferias_proporcionais",
    "férias vencidas em dobro":                 "ferias_dobro",
    "férias em dobro":                          "ferias_dobro",
    "férias vencidas":                          "ferias_vencidas",
    "férias indenizadas":                       "ferias_indenizadas",
    "abono pecuniário":                         "abono_pecuniario_ferias",
    "abono de férias":                          "abono_pecuniario_ferias",

    # --- Horas Extras ---
    "horas extras acima da 8ª diária":          "horas_extras_diarias",
    "horas extras acima da oitava diária":      "horas_extras_diarias",
    "labor em sobrejornada":                    "horas_extras_diarias",
    "sobrejornada":                             "horas_extras_diarias",
    "horas extras acima da 44ª semanal":        "horas_extras_semanais",
    "horas extras acima da quadragésima quarta":"horas_extras_semanais",
    "horas extras":                             "horas_extras_diarias",
    "horas extraordinárias":                    "horas_extras_diarias",

    # --- DSR ---
    "descanso semanal remunerado":              "dsr",
    "repouso semanal remunerado":               "dsr",
    "dsr":                                      "dsr",
    "rsr":                                      "dsr",

    # --- FGTS ---
    "fgts + multa de 40%":                      "fgts_com_multa",
    "fgts e multa rescisória de 40%":           "fgts_com_multa",
    "fgts com multa":                           "fgts_com_multa",
    "depósitos do fgts":                        "fgts_depositos",
    "fgts":                                     "fgts_depositos",
    "multa rescisória de 40%":                  "multa_fgts_40",
    "multa de 40% do fgts":                     "multa_fgts_40",

    # --- Aviso Prévio ---
    "aviso prévio indenizado":                  "aviso_previo_indenizado",
    "aviso prévio trabalhado":                  "aviso_previo_trabalhado",
    "aviso prévio proporcional":                "aviso_previo_proporcional",
    "aviso prévio":                             "aviso_previo_indenizado",

    # --- Verbas Rescisórias ---
    "saldo de salário":                         "saldo_salario",
    "saldo salarial":                           "saldo_salario",
    "multa do artigo 467":                      "multa_art_467",
    "multa art. 467":                           "multa_art_467",
    "multa art 467":                            "multa_art_467",
    "multa do artigo 477":                      "multa_art_477",
    "multa art. 477":                           "multa_art_477",
    "multa art 477":                            "multa_art_477",

    # --- Dano ---
    "dano moral":                               "dano_moral",
    "indenização por danos morais":             "dano_moral",
    "dano material":                            "dano_material",
    "indenização por danos materiais":          "dano_material",
    "dano existencial":                         "dano_existencial",

    # --- Honorários ---
    "honorários advocatícios":                  "honorarios_advocaticios",
    "honorários sucumbenciais":                 "honorarios_advocaticios",
    "honorários de sucumbência":                "honorarios_advocaticios",

    # --- Adicional de Insalubridade / Periculosidade ---
    "adicional de insalubridade":               "adicional_insalubridade",
    "insalubridade":                            "adicional_insalubridade",
    "adicional de periculosidade":              "adicional_periculosidade",
    "periculosidade":                           "adicional_periculosidade",
    "adicional noturno":                        "adicional_noturno",
    "adicional de transferência":               "adicional_transferencia",

    # --- Índices de Correção ---
    "ipca-e":                                   "IPCAE",
    "ipca e":                                   "IPCAE",
    "tr":                                       "TR",
    "taxa referencial":                         "TR",
    "selic":                                    "SELIC",
    "taxa selic":                               "SELIC",

    # --- Bases de Cálculo ---
    "salário base":                             "salario_base",
    "salário contratual":                       "salario_base",
    "última remuneração":                       "ultima_remuneracao",
    "remuneração":                              "ultima_remuneracao",
    "salário hora":                             "salario_hora",
    "valor hora":                               "salario_hora",
}

# ---------------------------------------------------------------------------
# Chaves normalizadas válidas — para validação
# ---------------------------------------------------------------------------

CHAVES_VALIDAS: set[str] = set(MAPA_NORMALIZACAO.values())

# ---------------------------------------------------------------------------
# Funções públicas
# ---------------------------------------------------------------------------

def normalizar(texto: str) -> Optional[str]:
    """
    Recebe texto em linguagem natural e retorna a chave padronizada.
    Faz correspondência exata após normalização de espaços e caixa.
    Retorna None se não encontrar correspondência.
    """
    if not texto:
        return None

    chave = _pre_processar(texto)

    # Tentativa de correspondência exata
    if chave in MAPA_NORMALIZACAO:
        resultado = MAPA_NORMALIZACAO[chave]
        logger.debug(f"Normalizado: '{texto}' → '{resultado}'")
        return resultado

    # Tentativa de correspondência parcial (texto contido na chave)
    for padrao, valor in MAPA_NORMALIZACAO.items():
        if padrao in chave or chave in padrao:
            logger.debug(f"Normalizado (parcial): '{texto}' → '{valor}'")
            return valor

    logger.debug(f"Sem correspondência para: '{texto}'")
    return None


def normalizar_lista(textos: list[str]) -> list[str]:
    """
    Normaliza uma lista de textos. Ignora itens sem correspondência.
    """
    resultado = []
    for texto in textos:
        normalizado = normalizar(texto)
        if normalizado:
            resultado.append(normalizado)
        else:
            resultado.append(texto)  # mantém original se não encontrar
    return resultado


def eh_chave_valida(chave: str) -> bool:
    """
    Verifica se uma string já é uma chave padronizada válida do sistema.
    """
    return chave in CHAVES_VALIDAS


def listar_variacoes(chave_padronizada: str) -> list[str]:
    """
    Dado uma chave padronizada, retorna todas as variações linguísticas
    mapeadas para ela. Útil para debug e auditoria.
    """
    return [k for k, v in MAPA_NORMALIZACAO.items() if v == chave_padronizada]


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _pre_processar(texto: str) -> str:
    """
    Normaliza caixa, remove espaços extras e caracteres especiais
    para permitir correspondência robusta.
    """
    texto = texto.lower().strip()
    texto = re.sub(r'\s+', ' ', texto)
    texto = texto.replace('º', '°')
    return texto