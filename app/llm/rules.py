"""Roteamento e extração por regras: modo degradado sem chave de LLM (FR-034)."""
import csv
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from app.api.schemas import Classificacao
from app.config import ROOT
from app.periodo import MESES, anos_no_texto, extrair_periodo, intervalo

PROTOCOLO_TOKEN = re.compile(r"\bouv-\w*", re.I)
PROTOCOLO_VALIDO = re.compile(r"\bOUV-\d{4}\b", re.I)

# Palavras que identificam o domínio sozinhas (fortes) e termos que também aparecem em outros contextos.
PALAVRAS = {
    "ouvidoria": ["ouvidoria", "protocolo", "manifestacao", "manifestacoes", "reclamacao", "denuncia"],
    "financeiro": ["receita", "despesa", "orcamento", "gast", "custo", "lancamento", "financeiro",
                   "inadimplencia", "faturamento", "centro de custo"],
    "informacoes_internas": ["ferias", "reembolso", "politica", "compra", "phishing", "incidente",
                             "home office", "acesso", "privacidade", "procedimento"],
}
# Categorias de ouvidoria que coincidem com assuntos de políticas internas: não contam como
# "informações internas" quando a pergunta já é claramente de ouvidoria.
COMPARTILHADAS = {"reembolso", "privacidade"}

TIPOS_REFERENCIA = {"status": "status", "categorias": "categoria", "categoria": "categoria",
                    "prioridades": "prioridade", "prioridade": "prioridade", "canais": "canal", "canal": "canal"}
# "abertas em janeiro de 2026" fala da data de abertura, não do status Aberto
_ANTES_DE_DATA = r"(?!\s+(?:em|no|na|nos|nas|de|entre|durante|desde)\s+(?:20\d\d|" + "|".join(MESES) + r"))"
STATUS = {"aberto": r"abert[oa]s?" + _ANTES_DE_DATA, "em analise": r"em analise", "aguardando area responsavel": r"aguardando( area responsavel)?",
          "respondido": r"respondid[oa]s?", "concluido": r"concluid[oa]s?"}
STATUS_CANONICO = {"aberto": "Aberto", "em analise": "Em análise",
                   "aguardando area responsavel": "Aguardando área responsável",
                   "respondido": "Respondido", "concluido": "Concluído"}
CATEGORIAS = {"cobranca": "Cobrança", "atendimento": "Atendimento", "produto ou servico": "Produto ou serviço",
              "cancelamento": "Cancelamento", "reembolso": "Reembolso", "privacidade": "Privacidade",
              "elogio": "Elogio", "sugestao": "Sugestão"}
PRIORIDADES = {"baixa": "Baixa", "media": "Média", "alta": "Alta", "critica": "Crítica"}
CANAIS = {"portal": "Portal", "e-mail": "E-mail", "email": "E-mail", "telefone": "Telefone", "chat": "Chat"}


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")


def _contem(texto: str, palavra: str) -> bool:
    return re.search(rf"\b{re.escape(palavra)}\w*", texto) is not None  # aceita plural/flexões


@lru_cache(maxsize=4)
def _departamentos(data_dir: Path) -> dict[str, str]:
    """{nome normalizado: nome canônico} lidos do orçamento fornecido."""
    with (Path(data_dir) / "financeiro" / "orcamento_mensal.csv").open(encoding="utf-8-sig") as f:
        return {normalizar(r["departamento"]): r["departamento"] for r in csv.DictReader(f)}


class RulesLLM:
    modo = "degradado"

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else ROOT / "data"

    # --- classificação -------------------------------------------------------------------------
    def classify(self, pergunta: str) -> Classificacao:
        if PROTOCOLO_TOKEN.search(pergunta):
            return Classificacao(dominio="ouvidoria", confianca=0.95, candidatos=["ouvidoria"])
        norm = normalizar(pergunta)
        achados = {d: [p for p in ps if _contem(norm, p)] for d, ps in PALAVRAS.items()}
        achados = {d: ps for d, ps in achados.items() if ps}
        if "ouvidoria" in achados and set(achados.get("informacoes_internas", [])) <= COMPARTILHADAS:
            achados.pop("informacoes_internas", None)
        dominios = list(achados)
        if len(dominios) == 1:
            return Classificacao(dominio=dominios[0], confianca=0.8, candidatos=dominios)
        if len(dominios) > 1:
            return Classificacao(dominio="ambigua", confianca=0.4, candidatos=dominios)
        return Classificacao(dominio="fora_de_escopo", confianca=0.6)

    # --- extração de parâmetros ----------------------------------------------------------------
    def extract_params(self, dominio: str, pergunta: str) -> dict:
        if dominio == "ouvidoria":
            return self._ouvidoria(pergunta)
        if dominio == "financeiro":
            return self._financeiro(pergunta)
        return {}

    def _ouvidoria(self, pergunta: str) -> dict:
        if achado := PROTOCOLO_VALIDO.search(pergunta):
            return {"consulta": "buscar_protocolo", "protocolo": achado.group(0).upper()}
        if PROTOCOLO_TOKEN.search(pergunta):
            return {"consulta": "buscar_protocolo", "protocolo": None}  # token com formato inválido
        norm = normalizar(pergunta)
        p: dict = {}
        for chave, rx in STATUS.items():
            if re.search(rf"\b{rx}\b", norm):
                p["status"] = STATUS_CANONICO[chave]
                break
        for chave, nome in CATEGORIAS.items():
            if re.search(rf"\b{chave}s?\b", norm):
                p["categoria"] = nome
                break
        if "priorid" in norm:
            for chave, nome in PRIORIDADES.items():
                if re.search(rf"\b{chave}s?\b", norm):
                    p["prioridade"] = nome
                    break
        if m := re.search(r"\b(?:canal|via|pelo|pela|por)\s+(?:o\s+|a\s+)?(portal|e-?mail|telefone|chat)\b", norm):
            p["canal"] = CANAIS[m.group(1)]
        per = extrair_periodo(norm)
        if per.get("ano") in (2025, 2026):
            de, ate = intervalo(per["ano"], per.get("mes_inicio", 1), per.get("mes_fim", 12))
            p["data_de"], p["data_ate"] = de.isoformat(), ate.isoformat()
        # tipo de consulta
        atributo = re.search(r"\b(status|categorias?|prioridades?|canais)\b", norm)
        if re.search(r"\bquant[oa]s?\b|\bnumero de\b|\btotal de\b", norm):
            p["consulta"] = "contar"
        elif atributo and not (p.keys() & {"status", "categoria", "prioridade", "canal"}) and re.search(
                r"podem|possiveis|validos?|validas?|existem|disponiveis|opcoes|^quais (sao )?(os |as )?"
                r"(status|categorias|prioridades|canais)", norm):
            p["consulta"] = "referencia"
            p["referencia_tipo"] = TIPOS_REFERENCIA[atributo.group(1)]
        elif p.keys() & {"status", "categoria", "prioridade", "canal", "data_de"} or re.search(
                r"\blist|\bmostre|\bquais manifestac", norm):
            p["consulta"] = "listar"
        return p

    def _financeiro(self, pergunta: str) -> dict:
        norm = normalizar(pergunta)
        p: dict = {}
        per = extrair_periodo(norm)
        p.update(per)
        anos = anos_no_texto(norm)
        if re.search(r"\bcompar", norm) and len(anos) >= 2:
            p["ano_b"] = anos[1]
        # consulta
        tem_rec, tem_desp = _contem(norm, "receita"), bool(re.search(r"\bdespesa|\bgast|\bcusto", norm))
        if "receita liquida" in norm:
            p["consulta"] = "receita_liquida"
        elif "inadimpl" in norm:
            p["consulta"] = "inadimplencia"
        elif "execucao orcamentaria" in norm or re.search(
                r"orcamento.*(executad|consumid|utilizad)|(executad|consumid|utilizad).*orcamento", norm):
            p["consulta"] = "execucao_orcamentaria"
        elif "ano_b" in p:
            p["consulta"] = "comparar_periodos"
            p["metrica"] = "receitas" if tem_rec and not tem_desp else "despesas"
        elif "orcamento" in norm:
            p["consulta"] = "orcamento_por_departamento"
            if re.search(r"\bmenor", norm):
                p["ordem"] = "menor"
            elif re.search(r"\bmaior|\bmais alto", norm):
                p["ordem"] = "maior"
        elif tem_rec and not tem_desp:
            p["consulta"] = "soma_receitas"
        elif tem_desp and not tem_rec:
            p["consulta"] = "soma_despesas"
        # critérios
        if re.search(r"\bincorrid", norm):
            p["criterio_gasto"] = "incorrida"
        elif re.search(r"\bpag[oa]s?\b|\bpagamentos? efetiv|\befetivamente pag|\brealizad", norm):
            p["criterio_gasto"] = "paga"
        if "vencimento" in norm:
            p["tipo_data"] = "vencimento"
        if m := re.search(r"\bcc[1-6]00\b", norm):
            p["centro_custo"] = m.group(0).upper()
        for chave, nome in _departamentos(self.data_dir).items():
            # "financeiro" é também o nome do domínio: só vale com "departamento/área/setor" antes
            rx = rf"\b(?:departamento|area|setor)\s+(?:de\s+|do\s+|da\s+)?{chave}\b" if chave == "financeiro" \
                else rf"\b{chave}\b"
            if re.search(rx, norm):
                p["departamento"] = nome
                break
        return p

    def answer(self, pergunta: str, trechos: list[dict]) -> dict:
        raise NotImplementedError("Resposta redigida por LLM não existe no modo degradado")
