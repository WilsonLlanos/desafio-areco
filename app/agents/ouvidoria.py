"""Agente de ouvidoria. Resposta montada por código a partir da linha encontrada (FR-009, FR-013)."""
from dataclasses import dataclass, field

from app.api.schemas import Fonte
from app.queries import ouvidoria as q


@dataclass
class Resultado:
    resposta: str
    status: str
    fontes: list[Fonte] = field(default_factory=list)


def _fmt(d) -> str:
    return d.strftime("%d/%m/%Y") if d else "—"


def responder(conn, params: dict) -> Resultado:
    protocolo = params.get("protocolo")
    if not q.protocolo_valido(protocolo):
        return Resultado(
            "Não identifiquei um protocolo válido. O formato é OUV-NNNN (por exemplo, OUV-0002). "
            "Informe o número completo do protocolo.", "esclarecimento")
    linha = q.buscar_protocolo(conn, protocolo)
    if linha is None:
        return Resultado(f"O protocolo {protocolo} não foi encontrado na base de manifestações.",
                         "nao_encontrado",
                         [Fonte(tipo="consulta", ref="ouvidoria.buscar_protocolo", detalhe=f"protocolo={protocolo}")])
    resposta = (
        f"Protocolo {linha['protocolo']}: status \"{linha['status']}\". "
        f"Categoria: {linha['categoria']}; assunto: {linha['assunto']}; prioridade: {linha['prioridade']}; "
        f"canal: {linha['canal_entrada']}; área responsável: {linha['area_responsavel']}. "
        f"Aberto em {_fmt(linha['data_abertura'])}; data de resposta: {_fmt(linha['data_resposta'])}. "
        f"O prazo de referência de {linha['prazo_referencia_dias']} dias é demonstrativo, não um prazo legal."
    )
    return Resultado(resposta, "ok", [
        Fonte(tipo="protocolo", ref=linha["protocolo"], detalhe="manifestacoes.csv"),
    ])
