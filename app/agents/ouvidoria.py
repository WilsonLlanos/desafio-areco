"""Agente de ouvidoria. Respostas montadas por código a partir dos dados consultados (FR-009 a FR-013)."""
from datetime import date

from app.agents.base import Resultado, esclarecimento
from app.api.schemas import Fonte
from app.queries import ouvidoria as q

_ROTULO_FILTRO = {"status": "status", "categoria": "categoria", "prioridade": "prioridade",
                  "canal": "canal de entrada"}
_PLURAL = {"status": "Status", "prioridade": "Prioridades", "categoria": "Categorias", "canal": "Canais"}
AVISO_PRAZO = "O prazo de referência de 10 dias é demonstrativo, não um prazo legal."


def _fmt(d) -> str:
    return d.strftime("%d/%m/%Y") if d else "—"


def _datas(params: dict) -> tuple[date | None, date | None, str]:
    """data_de/data_ate (ISO, ate exclusivo) → datas + descrição do período para a resposta."""
    de = date.fromisoformat(params["data_de"]) if params.get("data_de") else None
    ate = date.fromisoformat(params["data_ate"]) if params.get("data_ate") else None
    if not (de or ate):
        return None, None, ""
    return de, ate, f"abertas de {_fmt(de)} a {_fmt(ate and date.fromordinal(ate.toordinal() - 1))}"


def _filtros(params: dict, ref: dict) -> tuple[dict, str | None]:
    """Filtros válidos; devolve mensagem de erro se algum valor não existe na base de referência."""
    filtros = {}
    for chave in q.COLUNAS_FILTRO:
        valor = params.get(chave)
        if not valor:
            continue
        if valor not in ref[chave]:
            return {}, (f"{_ROTULO_FILTRO[chave].capitalize()} \"{valor}\" não existe. "
                        f"Valores válidos: {', '.join(ref[chave])}.")
        filtros[chave] = valor
    return filtros, None


def _descricao(filtros: dict, periodo: str) -> str:
    partes = [f"{_ROTULO_FILTRO[k]} {v}" for k, v in filtros.items()]
    if periodo:
        partes.append(periodo)
    return "; ".join(partes) if partes else "sem filtros"


def _buscar_protocolo(conn, params: dict) -> Resultado:
    protocolo = params.get("protocolo")
    if not q.protocolo_valido(protocolo):
        return esclarecimento(
            "Não identifiquei um protocolo válido. O formato é OUV-NNNN (por exemplo, OUV-0002). "
            "Informe o número completo do protocolo.")
    linha = q.buscar_protocolo(conn, protocolo)
    if linha is None:
        return Resultado(f"O protocolo {protocolo} não foi encontrado na base de manifestações.",
                         "nao_encontrado",
                         [Fonte(tipo="consulta", ref="ouvidoria.buscar_protocolo", detalhe=f"protocolo={protocolo}"),
                          Fonte(tipo="arquivo", ref="manifestacoes.csv")])
    resposta = (
        f"Protocolo {linha['protocolo']}: status \"{linha['status']}\". "
        f"Categoria: {linha['categoria']}; assunto: {linha['assunto']}; prioridade: {linha['prioridade']}; "
        f"canal: {linha['canal_entrada']}; área responsável: {linha['area_responsavel']}. "
        f"Aberto em {_fmt(linha['data_abertura'])}; data de resposta: {_fmt(linha['data_resposta'])}. "
        f"{AVISO_PRAZO}"
    )
    return Resultado(resposta, "ok", [Fonte(tipo="protocolo", ref=linha["protocolo"], detalhe="manifestacoes.csv"),
                                      Fonte(tipo="arquivo", ref="manifestacoes.csv")])


def _referencia(params: dict, ref: dict) -> Resultado:
    tipo = params.get("referencia_tipo")
    if tipo not in ref:
        return esclarecimento("Qual lista você quer consultar: status, categorias, prioridades ou canais?")
    valores = ref[tipo]
    fonte = Fonte(tipo="arquivo", ref="referencia_ouvidoria.json") if tipo != "canal" else \
        Fonte(tipo="arquivo", ref="dicionario_de_dados.md", detalhe="canais de entrada")
    return Resultado(f"{_PLURAL[tipo]} válidos na ouvidoria: {', '.join(valores)}.", "ok", [fonte],
                     {"valores": list(valores)})


def _contar(conn, params: dict, ref: dict) -> Resultado:
    filtros, erro = _filtros(params, ref)
    if erro:
        return esclarecimento(erro)
    de, ate, periodo = _datas(params)
    total = q.contar(conn, filtros, de, ate)
    desc = _descricao(filtros, periodo)
    return Resultado(f"Há {total} manifestação(ões) na base ({desc}).", "ok",
                     [Fonte(tipo="consulta", ref="ouvidoria.contar", detalhe=desc),
                      Fonte(tipo="arquivo", ref="manifestacoes.csv")], {"total": total})


def _listar(conn, params: dict, ref: dict) -> Resultado:
    filtros, erro = _filtros(params, ref)
    if erro:
        return esclarecimento(erro)
    de, ate, periodo = _datas(params)
    total = q.contar(conn, filtros, de, ate)
    desc = _descricao(filtros, periodo)
    fontes = [Fonte(tipo="consulta", ref="ouvidoria.listar", detalhe=desc), Fonte(tipo="arquivo", ref="manifestacoes.csv")]
    if total == 0:
        return Resultado(f"Nenhuma manifestação encontrada ({desc}).", "nao_encontrado", fontes, {"total": 0})
    linhas = q.listar(conn, filtros, de, ate)
    itens = "\n".join(f"- {r['protocolo']}: {r['assunto']} ({r['status']}, prioridade {r['prioridade']}, "
                      f"aberta em {_fmt(r['data_abertura'])})" for r in linhas)
    cabecalho = f"{total} manifestação(ões) ({desc})."
    if total > len(linhas):
        cabecalho += (f" Mostrando as {len(linhas)} primeiras por data de abertura; "
                      "refine por status, categoria, prioridade, canal ou período para ver as demais.")
    fontes += [Fonte(tipo="protocolo", ref=r["protocolo"]) for r in linhas]
    return Resultado(f"{cabecalho}\n{itens}", "ok", fontes,
                     {"total": total, "protocolos": [r["protocolo"] for r in linhas]})


def responder(conn, params: dict, ref: dict | None = None) -> Resultado:
    """Despacha a consulta de ouvidoria. `ref` = valores enumerados válidos (carregar_referencia)."""
    consulta = params.get("consulta")
    if consulta == "buscar_protocolo" or (not consulta and "protocolo" in params):
        return _buscar_protocolo(conn, params)
    if ref is None:
        raise ValueError("referência de ouvidoria é obrigatória para consultas por filtro")
    if consulta == "referencia":
        return _referencia(params, ref)
    if consulta == "contar":
        return _contar(conn, params, ref)
    if consulta == "listar":
        return _listar(conn, params, ref)
    return esclarecimento(
        "O que você quer saber da ouvidoria? Posso buscar um protocolo (OUV-NNNN), contar ou listar "
        "manifestações por status, categoria, prioridade, canal ou período, e informar os valores válidos.")
