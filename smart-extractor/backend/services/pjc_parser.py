"""
pjc_parser.py — Parser simples para arquivos .PJC (XML do PJe-Calc).

Objetivo: extrair parâmetros críticos de um .pjc já gerado (da empresa ou do sistema),
para permitir auditoria cruzada com a sentença/extração da IA:

- Índice de correção monetária trabalhista utilizado;
- Taxa de juros trabalhistas aplicada;
- Lista de nomes das verbas calculadas;
- Divisor (carga horária padrão) usado como base para horas extras.

Este módulo **não** depende do exporter legado; trabalha diretamente com XML.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Union
from xml.etree import ElementTree as ET


XmlInput = Union[str, bytes]


@dataclass
class PjcDadosBasicos:
    indice_trabalhista: Optional[str]
    juros_trabalhistas: Optional[str]
    nomes_verbas: List[str]
    divisor_horas: Optional[float]


class PjcParser:
    """
    Parser de .pjc (XML) focado em campos críticos para auditoria.

    Uso típico:
        parser = PjcParser.from_path("arquivo.pjc")
        dados = parser.extrair_dados_basicos()
    """

    def __init__(self, root: ET.Element):
        self._root = root

    # ------------------------------------------------------------------
    # Fábricas
    # ------------------------------------------------------------------

    @classmethod
    def from_path(cls, path: str) -> "PjcParser":
        tree = ET.parse(path)
        return cls(tree.getroot())

    @classmethod
    def from_string(cls, xml_content: XmlInput) -> "PjcParser":
        if isinstance(xml_content, bytes):
            root = ET.fromstring(xml_content)
        else:
            root = ET.fromstring(xml_content.encode("iso-8859-1"))
        return cls(root)

    # ------------------------------------------------------------------
    # Métodos de extração
    # ------------------------------------------------------------------

    def extrair_indice_trabalhista(self) -> Optional[str]:
        """
        Tenta localizar o índice de correção trabalhista (ex.: IPCAE, TRD, SELIC).

        O exporter legado grava em:
            <parametrosDeAtualizacao><ParametrosDeAtualizacao>
              <indiceTrabalhista>IPCAE</indiceTrabalhista>
              ...
              <juros>TRD_SIMPLES</juros>
        """
        # Busca direta
        elem = self._root.find(".//ParametrosDeAtualizacao/indiceTrabalhista")
        if elem is not None and elem.text:
            return elem.text.strip()
        # Fallback genérico
        elem = self._root.find(".//indiceTrabalhista")
        if elem is not None and elem.text:
            return elem.text.strip()
        return None

    def extrair_juros_trabalhistas(self) -> Optional[str]:
        """
        Tenta localizar a taxa de juros padrão aplicável às verbas.

        Exemplos típicos vistos no template:
            <juros>TRD_SIMPLES</juros>
        """
        elem = self._root.find(".//ParametrosDeAtualizacao/juros")
        if elem is not None and elem.text:
            return elem.text.strip()
        # Fallback genérico
        elem = self._root.find(".//juros")
        if elem is not None and elem.text:
            return elem.text.strip()
        return None

    def extrair_divisor_horas(self) -> Optional[float]:
        """
        Tenta localizar o divisor/carga horária padrão, quando presente.

        No exporter v5.9, é gravado como:
            <valorCargaHorariaPadrao>220.0000</valorCargaHorariaPadrao>
        """
        elem = self._root.find(".//valorCargaHorariaPadrao")
        if elem is None or not elem.text:
            return None
        raw = elem.text.strip()
        try:
            return float(raw.replace(",", "."))
        except ValueError:
            return None

    def extrair_nomes_verbas(self) -> List[str]:
        """
        Extrai nomes das verbas calculadas no .pjc.

        A estrutura exata pode variar conforme a versão do PJe-Calc, mas em geral
        há nós do tipo <Verba> ou listas de objetos contendo <nome>.
        A estratégia aqui é:
          - procurar elementos cujo nome termine com "Verba" ou seja exatamente "Verba";
          - dentro deles, extrair filhos <nome>.
        """
        nomes: List[str] = []

        # 1) Buscar nós <Verba> diretamente
        for verba in self._root.findall(".//Verba"):
            nome_elem = verba.find("nome")
            if nome_elem is not None and nome_elem.text:
                nomes.append(nome_elem.text.strip())

        # 2) Fallback: qualquer elemento que tenha um filho <nome>, sob um pai que
        #    pareça ser coleção de verbas (heurística). Evita duplicidade grosseira.
        if not nomes:
            for nome_elem in self._root.findall(".//nome"):
                texto = (nome_elem.text or "").strip()
                if not texto:
                    continue
                parent = nome_elem.getparent() if hasattr(nome_elem, "getparent") else None
                # xml.etree.ElementTree não expõe getparent, então usamos heurística simples:
                # apenas coletar todos os <nome> não vazios, e o chamador faz o filtro.
                nomes.append(texto)

        # Dedup mantendo ordem
        vistos = set()
        resultado: List[str] = []
        for n in nomes:
            if n not in vistos:
                vistos.add(n)
                resultado.append(n)
        return resultado

    # ------------------------------------------------------------------
    # API de alto nível
    # ------------------------------------------------------------------

    def extrair_dados_basicos(self) -> PjcDadosBasicos:
        """
        Extrai em uma única chamada os dados mais usados na auditoria.
        """
        return PjcDadosBasicos(
            indice_trabalhista=self.extrair_indice_trabalhista(),
            juros_trabalhistas=self.extrair_juros_trabalhistas(),
            nomes_verbas=self.extrair_nomes_verbas(),
            divisor_horas=self.extrair_divisor_horas(),
        )


__all__ = ["PjcParser", "PjcDadosBasicos"]

