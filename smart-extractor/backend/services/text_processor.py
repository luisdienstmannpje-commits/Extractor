import re
import unicodedata
from rapidfuzz import fuzz
from config import settings

# Dicionário de sinônimos para encontrar as seções
SECTION_SYNONYMS = {
    "sentenca": [
        "sentença", "sentenca", "decisão", "decisao", "julgamento",
        "fundamentação", "relatório"
    ],
    "acordao": [
        "acórdão", "acordao", "voto", "ementa"
    ],
    "dispositivo": [
        "dispositivo", "isto posto", "ante o exposto", "pelo exposto",
        "julgo procedente", "julgo parcialmente", "julgo improcedente",
        "conclusão", "decisão final"
    ]
}

def normalize_text(text: str) -> str:
    """
    Remove acentos, coloca em minúsculas e padroniza espaços.
    Ex: "ACÓRDÃO" -> "acordao"
    """
    if not text:
        return ""
    
    # 1. Lowercase
    text = text.lower()
    
    # 2. Remove acentos (NFD normalization)
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")
    
    # 3. Remove quebras de linha e espaços duplos
    text = re.sub(r"\s+", " ", text)
    
    return text.strip()

def find_section_hybrid(text: str, section_type: str) -> int:
    """
    Encontra a posição (índice) onde começa uma seção (sentença, acórdão, dispositivo).
    Usa estratégia Híbrida:
    1. Regex Exato (Rápido)
    2. Fuzzy Search (Inteligente - aceita erros de OCR)
    """
    normalized_text = normalize_text(text)
    keywords = SECTION_SYNONYMS.get(section_type, [])
    
    # 1. Tentativa via Regex (Busca exata)
    for keyword in keywords:
        # \b garante que é a palavra inteira
        pattern = re.escape(normalize_text(keyword))
        match = re.search(rf"\b{pattern}\b", normalized_text)
        if match:
            return match.start()
            
    # 2. Tentativa via Fuzzy (Busca por similaridade)
    # Divide o texto em linhas para comparar linha a linha
    lines = text.split('\n')
    current_pos = 0
    
    for line in lines:
        norm_line = normalize_text(line)
        
        for keyword in keywords:
            norm_keyword = normalize_text(keyword)
            
            # Se a similaridade for maior que o limite configurado (ex: 85%)
            ratio = fuzz.partial_ratio(norm_line, norm_keyword)
            
            if ratio >= settings.RAPIDFUZZ_THRESHOLD:
                return current_pos
        
        # Atualiza a posição do cursor (tamanho da linha + o \n)
        current_pos += len(line) + 1
        
    return -1 # Não encontrou