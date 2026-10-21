const $ = (id) => document.getElementById(id);

function mostrarEstado(texto, erro = false) {
  const el = $("estado");
  el.textContent = texto;
  el.className = "estado" + (erro ? " erro" : "");
  el.hidden = !texto;
}

function fonteTexto(f) {
  return f.detalhe ? `${f.ref} (${f.detalhe})` : f.ref;
}

async function perguntar(texto) {
  const r = await fetch("/ask", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ pergunta: texto }),
  });
  const corpo = await r.json().catch(() => ({}));
  if (!r.ok) {
    const e = new Error(corpo.detail || `Erro ${r.status}`);
    e.traceId = corpo.trace_id;
    throw e;
  }
  return corpo;
}

$("form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  $("resultado").hidden = true;
  $("enviar").disabled = true;
  mostrarEstado("Consultando…");
  try {
    const d = await perguntar($("pergunta").value);
    $("resposta").textContent = d.resposta;
    $("dominio").textContent = d.dominio;
    $("agente").textContent = d.agente;
    $("confianca").textContent = d.confianca.toFixed(2);
    $("trace").textContent = d.trace_id;
    const ul = $("fontes");
    ul.replaceChildren(...d.fontes.map((f) => Object.assign(document.createElement("li"), { textContent: fonteTexto(f) })));
    if (!d.fontes.length) ul.textContent = "—";
    $("aviso").hidden = d.modo !== "degradado";
    $("resultado").hidden = false;
    mostrarEstado("");
  } catch (e) {
    mostrarEstado(e.message + (e.traceId ? ` (trace ${e.traceId})` : ""), true);
  } finally {
    $("enviar").disabled = false;
  }
});
