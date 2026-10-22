"""Índice dos documentos internos: um item por documento e um por pergunta do FAQ, com BM25 próprio.

BM25 implementado aqui (poucas linhas) em vez de `rank-bm25`, que traria `numpy` para 17 itens.
Itens com padrão de prompt injection não são indexados (injeção indireta, FR-029).
"""
import json
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from app.guards import detectar_injecao
from app.texto import termos

log = logging.getLogger("aurora.rag")
ESCORE_MINIMO = 2.0  # abaixo disso a base não tem a resposta (calibrado com AV-T001–T012)
_VERSAO = re.compile(r"Versão\s+([\w.]+)\s+—\s+(\d{2}/\d{2}/\d{4})")


@dataclass
class Item:
    id: str
    source: str            # arquivo de origem citado na resposta
    secao: str             # título do documento ou id do FAQ
    texto: str
    document_version: str
    domain: str = "informacoes_internas"
    tipo: str = "documento"  # "documento" | "faq"
    tokens: list[str] = field(default_factory=list)


def _carregar(data_dir: Path) -> list[Item]:
    base = Path(data_dir) / "informacoes_internas"
    itens = []
    for arq in sorted(base.glob("*.md")):
        texto = arq.read_text(encoding="utf-8-sig")
        titulo = next((l.lstrip("# ").strip() for l in texto.splitlines() if l.startswith("# ")), arq.stem)
        v = _VERSAO.search(texto)
        itens.append(Item(arq.stem, arq.name, titulo, texto, f"{v.group(1)} ({v.group(2)})" if v else "n/d"))
    versoes = {i.source: i.document_version for i in itens}
    for faq in json.loads((base / "faq_interno.json").read_text(encoding="utf-8-sig")):
        itens.append(Item(faq["id"], faq["documento"], faq["id"], f"{faq['pergunta']}\n{faq['resposta']}",
                          versoes.get(faq["documento"], "n/d"), tipo="faq"))
    return itens


class Indice:
    """BM25 (Okapi, k1=1.5, b=0.75) sobre radicais normalizados."""

    K1, B = 1.5, 0.75

    def __init__(self, data_dir: Path):
        self.itens: list[Item] = []
        self.descartados: list[str] = []
        for item in _carregar(data_dir):
            if detectar_injecao(item.texto):
                log.warning("item %s (%s) descartado do índice: padrão de prompt injection", item.id, item.source)
                self.descartados.append(item.id)
                continue
            # o nome do arquivo também é metadado buscável ("06_politica_home_office" → home, office)
            item.tokens = termos(item.texto + " " + Path(item.source).stem.replace("_", " "))
            self.itens.append(item)
        self._tf = [Counter(i.tokens) for i in self.itens]
        self._len_media = sum(len(i.tokens) for i in self.itens) / max(len(self.itens), 1)
        df = Counter(t for tf in self._tf for t in tf)
        n = len(self.itens)
        self._idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def _score(self, consulta: list[str], k: int) -> float:
        tf, tamanho = self._tf[k], len(self.itens[k].tokens)
        s = 0.0
        for t in consulta:
            f = tf.get(t, 0)
            if f:
                s += self._idf[t] * f * (self.K1 + 1) / (f + self.K1 * (1 - self.B + self.B * tamanho / self._len_media))
        return s

    def buscar(self, pergunta: str, k: int = 3) -> list[tuple[Item, float]]:
        consulta = termos(pergunta)
        pontos = sorted(((self.itens[i], self._score(consulta, i)) for i in range(len(self.itens))),
                        key=lambda x: x[1], reverse=True)
        return [(item, s) for item, s in pontos[:k] if s > 0]

    def documento(self, source: str) -> Item | None:
        return next((i for i in self.itens if i.source == source and i.tipo == "documento"), None)
