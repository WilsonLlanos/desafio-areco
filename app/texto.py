"""Normalização de texto em português, compartilhada por regras, RAG e guardas."""
import re
import unicodedata

STOPWORDS = set("""
a o as os um uma uns umas de do da dos das no na nos nas em por para pra com sem sobre entre ao aos
e ou que se como qual quais quando onde quem quanto quanta quantos quantas e eh sao ser foi era esta estao
ha houver tem ter meu minha meus minhas seu sua seus suas este esta isso isto esse essa aquele
eu voce voces ele ela eles elas nos me te lhe mais menos muito muita ja nao sim tambem so ate apos
pelo pela pelos pelas desde cada todo toda todos todas outro outra deve devem pode podem posso
""".split()) | {
    # palavras genéricas da base: aparecem em quase todo documento e geravam acertos falsos
    # ("política de viagens internacionais" casava com "Política de férias … portal interno")
    "politica", "politicas", "documento", "documentos", "procedimento", "processo", "regra", "regras",
    "interno", "interna", "internos", "internas", "empresa", "aurora", "ficticio", "ficticia",
}


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos."""
    sem_acento = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")


def radical(token: str) -> str:
    """Radical grosseiro: 6 primeiras letras ("reporto" e "reportados" → "report").

    Com 5 letras havia colisões como "conte" (contar) × "contem" (conter)."""
    return token[:6]


def termos(texto: str) -> list[str]:
    """Texto → radicais sem stopwords (usado na busca e na escolha de linhas)."""
    return [radical(t) for t in re.findall(r"[a-z0-9]+", normalizar(texto)) if t not in STOPWORDS]
