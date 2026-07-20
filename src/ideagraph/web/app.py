# ruff: noqa: PLC0415
"""Flask app + status payload for the ideagraph provenance web UI.

``build_payload`` is dependency-free (core ideagraph only) so it can be tested
without the ``web`` extra; ``create_app`` imports Flask lazily.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ideagraph import (
    Evidence,
    ProvenanceGraph,
    find_stale_claims,
    hash_file,
    load_graph,
    validate_all,
)

#: Node-category label for the front end (which store the node came from).
_STATEMENT, _EVIDENCE, _ACTIVITY = "statement", "evidence", "activity"


def _resolver(base: Path):
    """Return a DigestResolver that re-hashes each evidence's reference file."""

    def _resolve(evidence: Evidence) -> str | None:
        ref = (evidence.metadata or {}).get("artefact") or evidence.reference
        if not ref:
            return None
        p = base / ref
        return hash_file(p) if p.exists() else None

    return _resolve


def build_payload(
    graph_path: str | Path, base: str | Path | None = None, bib: dict[str, dict[str, str]] | None = None
) -> dict[str, Any]:
    """Load the graph and compute a front-end payload with live status.

    Args:
        graph_path: Path to the ideagraph graph JSON file.
        base: Directory that relative evidence references resolve against, for
            staleness (defaults to the graph file's parent).
        bib: Optional ``{key: {title,author,year}}`` to label literature evidence.

    Returns:
        A dict with ``nodes``, ``edges``, and a ``summary`` of status counts —
        recomputed from disk on every call so the view reflects current state.
        Claim nodes also carry a ``support`` category (own/literature/both/
        unsupported).
    """
    from ideagraph import EvidenceKind, coverage
    from ideagraph.bib import format_citation

    graph_path = Path(graph_path)
    base = Path(base) if base is not None else graph_path.parent
    bib = bib or {}
    graph: ProvenanceGraph = load_graph(graph_path)

    verdicts = validate_all(graph)
    stale_ids = {c.id for c in find_stale_claims(graph, _resolver(base))}
    cov = coverage(graph)

    nodes: list[dict[str, Any]] = []
    for sid, s in graph.statements.items():
        assertion = sid in cov
        nodes.append(
            {
                "id": sid,
                "type": _STATEMENT,
                "stype": s.type.value,
                "level": 0,
                "label": sid,
                "order": s.order,
                "section": s.section,
                "status": ("stale" if sid in stale_ids else verdicts[sid].status.value) if sid in verdicts else None,
                "support": cov[sid].category if assertion else None,
                "source_digest": s.source_digest,
                "statement": s.statement,
                "tags": list(s.tags),
                "metadata": s.metadata,
            }
        )
    for eid, ev in graph.evidence.items():
        is_lit = ev.kind is EvidenceKind.LITERATURE
        citation = format_citation(ev.reference, bib.get(ev.reference)) if is_lit else None
        nodes.append(
            {
                "id": eid,
                "type": _EVIDENCE,
                "level": 1,
                "label": citation if is_lit else eid,
                "status": "literature" if is_lit else "evidence",
                "kind": ev.kind.value,
                "reference": ev.reference,
                "citation": citation,
                "digest": ev.digest,
                "metadata": ev.metadata,
            }
        )
    for aid, act in graph.activities.items():
        nodes.append(
            {
                "id": aid,
                "type": _ACTIVITY,
                "level": 2,
                "label": act.label,
                "status": "activity",
                "kind": act.kind.value,
                "metadata": act.metadata,
            }
        )

    discourse = {"elaborates", "contrasts", "depends_on", "cites", "motivates"}
    edges = [
        {
            "source": rel.subject_id,
            "target": rel.object_id,
            "predicate": rel.predicate.value,
            "discourse": rel.predicate.value in discourse,
        }
        for rel in graph.relations.values()
    ]

    # Headline summary = support coverage of the asserting statements.
    summary: dict[str, int] = {}
    for c in cov.values():
        summary[c.category] = summary.get(c.category, 0) + 1

    return {
        "nodes": nodes,
        "edges": edges,
        "summary": summary,
        "counts": {
            "statements": len(graph.statements),
            "evidence": len(graph.evidence),
            "activities": len(graph.activities),
        },
    }


def build_doc_payload(doc_path: str | Path, graph_payload: dict[str, Any]) -> dict[str, Any]:
    r"""Render a draft to reading-view HTML and resolve its provenance refs.

    Args:
        doc_path: Path to a LaTeX/Markdown draft with ``\\prov`` / ``prov:`` marks.
        graph_payload: The output of :func:`build_payload`, for id -> status lookup.

    Returns:
        A dict with ``name``, ``format``, ``html`` (spans carry ``data-id``), and
        ``refs`` mapping each referenced id to its ``status`` / ``type`` /
        ``known`` flag (``known=False`` = the draft cites an id absent from the
        graph — a dangling provenance reference).
    """
    from ideagraph.web.document import (
        detect_format,
        expand_inputs,
        parse_aux_labels,
        prov_contents,
        render_document,
        text_digest,
    )

    doc_path = Path(doc_path)
    fmt = detect_format(str(doc_path))
    if fmt == "latex":
        text = expand_inputs(doc_path)
        aux = doc_path.with_suffix(".aux")
        if not aux.exists():
            aux = doc_path.parent / "main.aux"
        body, ref_ids = render_document(text, fmt, labels=parse_aux_labels(aux), base=doc_path.parent)
    else:
        text = doc_path.read_text()
        body, ref_ids = render_document(text, fmt)
    contents = prov_contents(text, fmt)
    by_id = {n["id"]: n for n in graph_payload["nodes"]}

    def _drifted(rid: str) -> bool:
        # A statement drifts when its stored source_digest no longer matches the
        # current draft span it was captured from. Unknown ids or statements with
        # no captured digest cannot drift.
        node = by_id.get(rid)
        sd = node.get("source_digest") if node else None
        return bool(sd and rid in contents and text_digest(contents[rid]) != sd)

    refs = {
        rid: {
            "known": rid in by_id,
            "status": by_id[rid]["status"] if rid in by_id else "unknown",
            "type": by_id[rid]["type"] if rid in by_id else None,
            "support": by_id[rid].get("support", "unknown") if rid in by_id else "unknown",
            "drifted": _drifted(rid),
        }
        for rid in ref_ids
    }
    return {"name": doc_path.name, "format": fmt, "html": body, "refs": refs}


def build_library_payload(root: str | Path) -> dict[str, Any]:
    """Index a library and return its cross-article snapshot for the web view.

    Args:
        root: Library root directory.

    Returns:
        The library snapshot (``articles`` / ``nodes`` / ``edges`` / ``counts``).
    """
    from ideagraph.library import Library

    with Library(root) as lib:
        lib.index()
        return lib.snapshot()


def create_app(
    graph_path: str | Path | None = None,
    base: str | Path | None = None,
    docs: list[str | Path] | None = None,
    bib: dict[str, dict[str, str]] | None = None,
    library: str | Path | None = None,
):
    """Build the Flask app serving the provenance UI.

    Args:
        graph_path: Path to the ideagraph graph JSON file (Graph/Document tabs).
        base: Directory relative evidence references resolve against.
        docs: Optional draft files (LaTeX/Markdown) to expose in the Document tab.
        bib: Optional parsed BibTeX for labelling literature evidence.
        library: Optional library root directory (enables the Library tab: the
            cross-article idea graph over every article under it).

    Returns:
        A configured :class:`flask.Flask` application.

    Raises:
        ModuleNotFoundError: If Flask is not installed (install ``ideagraph[web]``).
    """
    try:
        from flask import Flask, Response, abort, jsonify
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised via CLI guard
        raise ModuleNotFoundError("the web UI needs Flask; install it with `pip install ideagraph[web]`") from exc

    doc_list = [Path(d) for d in (docs or [])]
    app = Flask(__name__)

    @app.route("/api/config")
    def api_config():  # type: ignore[no-untyped-def]
        return jsonify({"graph": graph_path is not None, "library": library is not None})

    @app.route("/api/graph")
    def api_graph():  # type: ignore[no-untyped-def]
        if graph_path is None:
            abort(404)
        return jsonify(build_payload(graph_path, base, bib))

    @app.route("/api/library")
    def api_library():  # type: ignore[no-untyped-def]
        if library is None:
            abort(404)
        return jsonify(build_library_payload(library))

    @app.route("/api/docs")
    def api_docs():  # type: ignore[no-untyped-def]
        return jsonify([{"i": i, "name": d.name} for i, d in enumerate(doc_list)])

    @app.route("/api/doc/<int:i>")
    def api_doc(i):  # type: ignore[no-untyped-def]
        if i < 0 or i >= len(doc_list):
            abort(404)
        return jsonify(build_doc_payload(doc_list[i], build_payload(graph_path, base, bib)))

    asset_root = doc_list[0].resolve().parent if doc_list else None
    _asset_exts = {".png", ".svg", ".jpg", ".jpeg", ".gif", ".webp", ".pdf"}

    @app.route("/asset/<path:relpath>")
    def asset(relpath):  # type: ignore[no-untyped-def]
        import mimetypes

        if asset_root is None:
            abort(404)
        target = (asset_root / relpath).resolve()
        if asset_root not in target.parents or target.suffix.lower() not in _asset_exts or not target.is_file():
            abort(404)
        mime = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        return Response(target.read_bytes(), mimetype=mime)

    @app.route("/vendor/<path:name>")
    def vendor(name):  # type: ignore[no-untyped-def]
        from importlib.resources import files

        allowed = {"vis-network.min.js": "vis-network.min.js", "mathjax.js": "mathjax-tex-svg.js"}
        fname = allowed.get(name)
        if fname is None:
            abort(404)
        data = (files("ideagraph.web") / "static" / fname).read_bytes()
        return Response(data, mimetype="application/javascript")

    @app.route("/")
    def index():  # type: ignore[no-untyped-def]
        return Response(_INDEX_HTML, mimetype="text/html")

    return app


#: Self-contained page; loads the vendored vis-network (served at /vendor/, no
#: network needed). Renders a status-coloured provenance DAG (Graph tab) and, if
#: drafts were passed, a reading view with inline provenance marks (Document tab).
_INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>ideagraph provenance</title>
<script src="/vendor/vis-network.min.js"></script>
<script>window.MathJax={tex:{inlineMath:[['$','$'],['\\\\(','\\\\)']],displayMath:[['$$','$$'],['\\\\[','\\\\]']]},
  svg:{fontCache:'local'},startup:{typeset:false},options:{skipHtmlTags:['script','style']}};</script>
<script src="/vendor/mathjax.js" id="MathJax-script"></script>
<style>
  :root { --bg:#0f1720; --panel:#f7f9fc; }
  * { box-sizing:border-box; }
  body { margin:0; font-family: system-ui, -apple-system, sans-serif; display:flex; flex-direction:column;
         height:100vh; color:#1a2330; }
  #bar { padding:12px 18px; background:var(--bg); color:#fff; display:flex; align-items:center; gap:16px;
         flex-wrap:wrap; }
  #bar b { font-size:18px; letter-spacing:.2px; }
  .tabs { display:flex; gap:5px; margin-left:8px; }
  .tab { padding:6px 15px; border-radius:8px; font-size:15px; cursor:pointer; color:#c8d3df; background:#1c2836; }
  .tab.active { background:#2f6df6; color:#fff; font-weight:600; }
  .tab.hidden { display:none; }
  .chip { display:inline-flex; align-items:center; padding:4px 12px; border-radius:12px; font-size:14px;
          font-weight:600; color:#fff; }
  .counts { color:#9fb0c3; font-size:15px; }
  .legend { margin-left:auto; display:flex; gap:16px; font-size:14px; color:#c8d3df; }
  .legend span { display:inline-flex; align-items:center; gap:6px; }
  .sw { width:14px; height:14px; border-radius:3px; display:inline-block; }
  #cols { display:flex; padding:8px 0; background:#eef2f7; border-bottom:1px solid #dde3ec;
          font-size:14px; font-weight:700; color:#5b6b7f; text-transform:uppercase; letter-spacing:.5px; }
  #cols div { flex:1; text-align:center; }
  #main { flex:1; display:flex; min-height:0; }
  .view { flex:1; display:flex; flex-direction:column; min-width:0; min-height:0; }
  .view.hidden { display:none; }
  #net { flex:1; min-height:0; background:#fbfcfe; }
  #libnet { flex:1; min-height:0; background:#fbfcfe; }
  #libbar { padding:8px 16px; border-bottom:1px solid #dde3ec; background:#eef2f7; font-size:13px; color:#42536a; }
  #docbar { padding:8px 16px; border-bottom:1px solid #dde3ec; background:#eef2f7; font-size:13px; }
  #docbody { flex:1; overflow:auto; padding:28px 48px; }
  #docbody article { max-width:880px; margin:0 auto; font-size:19px; line-height:1.7; color:#1c2735; }
  #docbody h2 { font-size:27px; margin:1.2em 0 .4em; } #docbody h3 { font-size:21px; margin:1em 0 .3em; }
  #docbody figure { margin:1.8em auto; text-align:center; }
  #docbody .figimg { max-width:100%; height:auto; border:1px solid #dde3ec; border-radius:4px; }
  #docbody .figpdf { width:100%; height:520px; border:1px solid #dde3ec; border-radius:4px; }
  #docbody figcaption { font-size:15px; line-height:1.5; color:#42536a; margin-top:.6em; text-align:left; }
  #docbody .fignote { color:#8494a8; font-style:italic; padding:12px; border:1px dashed #c3ccd8; border-radius:4px; }
  .prov { border-bottom:2.5px solid #8895a7; cursor:pointer; padding-bottom:1px; }
  .prov:hover { background:#eef3ff; }
  .prov[data-support=own]{ border-color:#1f9d55; }
  .prov[data-support=literature]{ border-color:#2f6df6; }
  .prov[data-support=both]{ border-color:#00897b; }
  .prov[data-support=other]{ border-color:#8895a7; }
  .prov[data-support=unsupported]{ border-bottom-style:dashed; border-color:#e0245e; background:#fdecef; }
  .prov[data-support=unknown]{ border-bottom-style:dashed; border-color:#8895a7; }
  .prov[data-drift=1]{ background:#fff4e0; box-shadow:inset 0 -6px 0 -4px #d98324; }
  #panel { width:380px; overflow:auto; border-left:1px solid #dde3ec; padding:18px; font-size:14px;
           background:var(--panel); }
  #panel h3 { margin:0 0 4px; font-size:15px; word-break:break-word; }
  #panel .badge { display:inline-block; padding:2px 9px; border-radius:10px; color:#fff; font-size:11px;
                  font-weight:700; margin-bottom:10px; }
  #panel .stmt { font-size:14px; line-height:1.45; margin:8px 0 12px; color:#243244; }
  #panel .kv { margin:3px 0; color:#42536a; } #panel .kv b { color:#1a2330; }
  #panel code { background:#e7edf5; padding:1px 5px; border-radius:4px; font-size:12px; word-break:break-all; }
  pre { white-space:pre-wrap; word-break:break-word; background:#e7edf5; padding:10px; border-radius:6px;
        font-size:12px; margin:6px 0 0; }
  .hint { color:#8494a8; }
</style>
</head>
<body>
<div id="bar">
  <b>ideagraph provenance</b>
  <span class="tabs">
    <span class="tab hidden" id="tab-graph" onclick="showTab('graph')">Graph</span>
    <span class="tab hidden" id="tab-doc" onclick="showTab('doc')">Document</span>
    <span class="tab hidden" id="tab-library" onclick="showTab('library')">Library</span>
  </span>
  <span id="summary"></span>
  <span class="counts" id="counts"></span>
  <span class="legend" id="toplegend">
    <span><i class="sw" style="background:#3949ab"></i>claim</span>
    <span><i class="sw" style="background:#00897b"></i>finding</span>
    <span><i class="sw" style="background:#8d6e63"></i>background</span>
    <span><i class="sw" style="background:#6a4fa3"></i>method</span>
    <span><i class="sw" style="background:#2f6df6"></i>evidence</span>
    <span><i class="sw" style="background:#d98324"></i>literature</span>
    <span><i class="sw" style="background:#8e44c9"></i>run</span>
    <span><i class="sw" style="border:3px solid #e0245e;background:transparent"></i>unsupported</span>
  </span>
</div>
<div id="main">
  <div class="view" id="view-graph">
    <div id="cols"><div>Statements</div><div>Evidence</div><div>Activities (runs)</div></div>
    <div id="net"></div>
  </div>
  <div class="view hidden" id="view-doc">
    <div id="docbar">Document: <select id="docsel" onchange="loadDoc(this.value)"></select>
      &nbsp;<span class="hint">underline = support: <b style="color:#1f9d55">own</b> ·
      <b style="color:#2f6df6">literature</b> · <b style="color:#00897b">both</b> ·
      <b style="color:#e0245e">unsupported</b> · <b style="background:#fff4e0">amber highlight</b> = drifted.
      Click a mark to inspect.</span></div>
    <div id="docbody"><article id="docart"></article></div>
  </div>
  <div class="view hidden" id="view-library">
    <div id="libbar">Library idea graph — nodes coloured by article; dashed red = dangling cross-reference.
      <span class="hint" id="libarticles"></span></div>
    <div id="libnet"></div>
  </div>
  <div id="panel"><span class="hint">Click a node or a provenance mark to inspect it.</span></div>
</div>
<script>
// status/support colours (doc marks + summary chips)
const COLOR = { valid:"#1f9d55", invalid:"#e0245e", stale:"#f5a623", needs_review:"#ef6c00",
  unresolved:"#8895a7", own:"#1f9d55", literature:"#2f6df6", both:"#00897b", other:"#8895a7",
  unsupported:"#e0245e", evidence:"#2f6df6", activity:"#8e44c9", unknown:"#8895a7" };
// statement-node fill by rhetorical type
const STYPE = { claim:"#3949ab", finding:"#00897b", result:"#00acc1", background:"#8d6e63",
  method:"#6a4fa3", definition:"#546e7a", motivation:"#c2185b", other:"#8895a7" };
const DISCOURSE = new Set(["elaborates","contrasts","depends_on","cites","motivates"]);
let byId = {};
function esc(s){ return String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }

const TABS = ["graph","doc","library"];
function showTab(t){
  for (const x of TABS){
    document.getElementById("view-"+x).classList.toggle("hidden", x!==t);
    document.getElementById("tab-"+x).classList.toggle("active", x===t);
  }
  // The top legend describes statement types (Graph/Document); the Library view
  // colours by article and carries its own legend, so hide it there.
  document.getElementById("toplegend").style.visibility = (t==="library") ? "hidden" : "visible";
}
// Distinct, stable colour per article for the library view.
const ARTICLE_PALETTE = ["#3949ab","#00897b","#d98324","#c2185b","#6a4fa3","#00acc1","#7cb342","#8d6e63","#e0245e","#5c6bc0"];
const _artColor = {};
function articleColor(a){
  if (!(a in _artColor)) _artColor[a] = ARTICLE_PALETTE[Object.keys(_artColor).length % ARTICLE_PALETTE.length];
  return _artColor[a];
}

function showNode(id){
  const panel = document.getElementById("panel");
  const n = byId[id];
  if (!n){ panel.innerHTML = `<h3>${esc(id)}</h3><span class="badge" style="background:#e0245e">unknown reference</span>`
      + `<div class="stmt">This provenance id is not in the graph — a dangling reference.</div>`; return; }
  const label = n.type === "statement" ? n.stype : (n.status === "literature" ? "literature" : n.type);
  const bg = n.type === "statement" ? (STYPE[n.stype] || "#8895a7") : (n.status === "literature" ? "#d98324" : (COLOR[n.status] || "#8895a7"));
  let h = `<h3>${esc(n.id)}</h3><span class="badge" style="background:${bg}">${esc(label)}</span>`;
  if (n.statement) h += `<div class="stmt">${esc(n.statement)}</div>`;
  if (n.support) h += `<div class="kv"><b>support:</b> ${esc(n.support)}</div>`;
  if (n.status) h += `<div class="kv"><b>status:</b> ${esc(n.status)}</div>`;
  if (n.section) h += `<div class="kv"><b>section:</b> ${esc(n.section)}</div>`;
  if (n.citation) h += `<div class="kv"><b>citation:</b> ${esc(n.citation)}</div>`;
  if (n.kind) h += `<div class="kv"><b>kind:</b> ${esc(n.kind)}</div>`;
  if (n.reference) h += `<div class="kv"><b>reference:</b> ${esc(n.reference)}</div>`;
  if (n.digest) h += `<div class="kv"><b>digest:</b> <code>${esc(n.digest)}</code></div>`;
  if (n.source_digest) h += `<div class="kv"><b>source digest:</b> <code>${esc(n.source_digest)}</code></div>`;
  if (n.tags && n.tags.length) h += `<div class="kv"><b>tags:</b> ${esc(n.tags.join(", "))}</div>`;
  if (n.metadata && Object.keys(n.metadata).length)
    h += `<div class="kv"><b>metadata:</b></div><pre>${esc(JSON.stringify(n.metadata, null, 2))}</pre>`;
  panel.innerHTML = h;
}

async function loadDoc(i){
  const d = await (await fetch("/api/doc/"+i)).json();
  const art = document.getElementById("docart");
  art.innerHTML = d.html;
  art.querySelectorAll(".prov").forEach(sp => {
    const id = sp.dataset.id, ref = d.refs[id] || {support:"unknown"};
    sp.dataset.support = ref.known ? (ref.support || "other") : "unknown";
    if (ref.drifted) sp.dataset.drift = "1";
    sp.title = ref.known
      ? `${id} — support: ${ref.support}, status: ${ref.status}${ref.drifted ? " ⚠ drifted from captured text" : ""}`
      : `${id} — not in graph`;
    sp.onclick = () => showNode(id);
  });
  if (window.MathJax && MathJax.typesetPromise) { try { await MathJax.typesetPromise([art]); } catch(e){} }
}

async function loadGraph() {
  const data = await (await fetch("/api/graph")).json();
  byId = Object.fromEntries(data.nodes.map(n => [n.id, n]));
  const nodes = data.nodes.map(n => {
    let bg, border;
    if (n.type === "statement") {
      bg = STYPE[n.stype] || "#8895a7";
      border = n.support === "unsupported" ? "#e0245e" : (n.status === "stale" ? "#f5a623" : bg);
    } else {
      bg = n.status === "literature" ? "#d98324" : (COLOR[n.status] || "#8895a7");
      border = bg;
    }
    const bw = (border !== bg) ? 4 : 2;
    return { id:n.id, label:n.label, level:n.level, shape:"box",
      color:{ background:bg, border:border, highlight:{background:bg, border:"#111"} },
      font:{ color:"#ffffff", size:18, face:"system-ui", bold: n.type==="statement" },
      margin:12, widthConstraint:{ maximum:230 }, shapeProperties:{ borderRadius:7 }, borderWidth:bw };
  });
  const edges = data.edges.map(e => ({ from:e.source, to:e.target, arrows:{to:{scaleFactor:.6}},
    dashes: e.discourse, label: e.discourse ? e.predicate : undefined,
    font:{ size:11, color:"#8d6e63", strokeWidth:3, strokeColor:"#ffffff" },
    smooth:{ type:"cubicBezier", forceDirection:"horizontal", roundness:.55 },
    color:{ color: e.discourse ? "#8d6e63" : "#c3ccd8", highlight:"#5b6b7f" }, width:1.5 }));
  document.getElementById("summary").innerHTML = Object.entries(data.summary).map(([k,v]) =>
    `<span class="chip" style="background:${COLOR[k]||'#8895a7'}">${v} ${k}</span>`).join(" ");
  document.getElementById("counts").textContent =
    `${data.counts.statements} statements · ${data.counts.evidence} evidence · ${data.counts.activities} runs`;
  const net = new vis.Network(document.getElementById("net"),
    { nodes:new vis.DataSet(nodes), edges:new vis.DataSet(edges) },
    { layout:{ hierarchical:{ enabled:true, direction:"LR", sortMethod:"directed",
        levelSeparation:430, nodeSpacing:120, treeSpacing:240, blockShifting:true,
        edgeMinimization:true, parentCentralization:true, shakeTowards:"roots" } },
      physics:false, interaction:{ hover:true, tooltipDelay:120 } });
  net.once("afterDrawing", () => net.fit({ animation:false }));
  net.on("click", p => p.nodes.length ? showNode(p.nodes[0])
    : (document.getElementById("panel").innerHTML = '<span class="hint">Click a node or a provenance mark to inspect it.</span>'));
}

async function loadDocs(){
  const docs = await (await fetch("/api/docs")).json();
  if (!docs.length) return;
  document.getElementById("tab-doc").classList.remove("hidden");
  const sel = document.getElementById("docsel");
  sel.innerHTML = docs.map(d => `<option value="${d.i}">${esc(d.name)}</option>`).join("");
  loadDoc(0);
}

let libById = {};
function showLibNode(id){
  const n = libById[id];
  const panel = document.getElementById("panel");
  if (!n){ panel.innerHTML = `<h3>${esc(id)}</h3><span class="badge" style="background:#e0245e">not in library</span>`
      + `<div class="stmt">A cross-reference points here, but the target statement is not indexed — dangling.</div>`; return; }
  const bg = STYPE[n.stype] || "#8895a7";
  let h = `<h3>${esc(n.id)}</h3><span class="badge" style="background:${bg}">${esc(n.stype)}</span>`;
  h += `<div class="stmt">${esc(n.text)}</div>`;
  h += `<div class="kv"><b>article:</b> ${esc(n.article)}</div>`;
  if (n.status) h += `<div class="kv"><b>status:</b> ${esc(n.status)}</div>`;
  panel.innerHTML = h;
}

async function loadLibrary(){
  const data = await (await fetch("/api/library")).json();
  libById = Object.fromEntries(data.nodes.map(n => [n.id, n]));
  const nodes = data.nodes.map(n => {
    const bg = articleColor(n.article);
    return { id:n.id, label:n.node, group:n.article, shape:"box",
      color:{ background:bg, border:bg, highlight:{background:bg, border:"#111"} },
      font:{ color:"#ffffff", size:16, face:"system-ui" },
      margin:10, widthConstraint:{ maximum:200 }, shapeProperties:{ borderRadius:7 }, borderWidth:2 };
  });
  // Include dangling cross-targets as stub nodes so the edge has an endpoint.
  for (const e of data.edges){
    if (e.dangling && !(e.target in libById)){
      libById[e.target] = null;
      nodes.push({ id:e.target, label:e.target, shape:"box", color:{background:"#fdecef",border:"#e0245e"},
        font:{color:"#e0245e",size:14}, borderWidth:2, shapeProperties:{borderRadius:7}, margin:8 });
    }
  }
  const edges = data.edges.map(e => {
    const cross = e.kind === "cross";
    const col = e.dangling ? "#e0245e" : (cross ? "#d98324" : "#c3ccd8");
    return { from:e.source, to:e.target, arrows:{to:{scaleFactor:.6}},
      dashes: cross, label: cross ? e.predicate : undefined,
      font:{ size:11, color:col, strokeWidth:3, strokeColor:"#ffffff" },
      color:{ color:col, highlight:"#5b6b7f" }, width: cross ? 2 : 1.2 };
  });
  document.getElementById("libarticles").innerHTML = "&nbsp; " + data.articles.map(a =>
    `<span style="color:${articleColor(a.id)};font-weight:700">■</span> ${esc(a.id)}`).join(" &nbsp; ")
    + ` &nbsp;·&nbsp; ${data.counts.statements} statements, ${data.counts.cross_edges} cross-links`;
  const net = new vis.Network(document.getElementById("libnet"),
    { nodes:new vis.DataSet(nodes), edges:new vis.DataSet(edges) },
    { physics:{ enabled:true, stabilization:{iterations:200}, barnesHut:{springLength:140, gravitationalConstant:-8000} },
      interaction:{ hover:true, tooltipDelay:120 } });
  net.on("click", p => p.nodes.length ? showLibNode(p.nodes[0])
    : (document.getElementById("panel").innerHTML = '<span class="hint">Click a node or a provenance mark to inspect it.</span>'));
}

async function init(){
  let cfg = { graph:true, library:false };
  try { cfg = await (await fetch("/api/config")).json(); } catch(e){}
  const first = cfg.graph ? "graph" : "library";
  if (cfg.graph){ document.getElementById("tab-graph").classList.remove("hidden"); await loadGraph(); await loadDocs(); }
  if (cfg.library){ document.getElementById("tab-library").classList.remove("hidden"); await loadLibrary(); }
  showTab(first);
}
init();
</script>
</body>
</html>
"""
