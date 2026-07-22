// Render the cross-article idea graph with vis-network, reading its data from
// the endpoint named in the container's data-library-url attribute.
;(function () {
    'use strict'

    var STYPE = {
        claim: '#3949ab',
        finding: '#00897b',
        result: '#00acc1',
        background: '#8d6e63',
        method: '#6a4fa3',
        definition: '#546e7a',
        motivation: '#c2185b',
        other: '#8895a7',
    }
    var PALETTE = [
        '#3949ab',
        '#00897b',
        '#d98324',
        '#c2185b',
        '#6a4fa3',
        '#00acc1',
        '#7cb342',
        '#8d6e63',
        '#e0245e',
        '#5c6bc0',
    ]
    var artColor = {}
    function articleColor(a) {
        if (!(a in artColor)) {
            artColor[a] = PALETTE[Object.keys(artColor).length % PALETTE.length]
        }
        return artColor[a]
    }

    function esc(s) {
        return String(s).replace(/[&<>]/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]
        })
    }

    var byId = {}

    function showNode(id) {
        var panel = document.getElementById('panel')
        var n = byId[id]
        if (!n) {
            panel.innerHTML =
                '<h3>' +
                esc(id) +
                '</h3><span class="badge" style="background:#e0245e">not in library</span>' +
                '<div class="stmt">A cross-reference points here, but the target statement is not indexed — dangling.</div>'
            return
        }
        var bg = STYPE[n.stype] || '#8895a7'
        var h =
            '<h3>' +
            esc(n.id) +
            '</h3><span class="badge" style="background:' +
            bg +
            '">' +
            esc(n.stype || 'statement') +
            '</span>'
        if (n.text) h += '<div class="stmt">' + esc(n.text) + '</div>'
        h += '<div class="kv"><b>article:</b> ' + esc(n.article) + '</div>'
        if (n.status)
            h += '<div class="kv"><b>status:</b> ' + esc(n.status) + '</div>'
        panel.innerHTML = h
    }

    function render(data) {
        byId = {}
        data.nodes.forEach(function (n) {
            byId[n.id] = n
        })
        var nodes = data.nodes.map(function (n) {
            var bg = articleColor(n.article)
            return {
                id: n.id,
                label: n.node,
                group: n.article,
                shape: 'box',
                color: {
                    background: bg,
                    border: bg,
                    highlight: { background: bg, border: '#111' },
                },
                font: { color: '#ffffff', size: 16, face: 'system-ui' },
                margin: 10,
                widthConstraint: { maximum: 200 },
                shapeProperties: { borderRadius: 7 },
                borderWidth: 2,
            }
        })
        data.edges.forEach(function (e) {
            if (e.dangling && !(e.target in byId)) {
                byId[e.target] = null
                nodes.push({
                    id: e.target,
                    label: e.target,
                    shape: 'box',
                    color: { background: '#fdecef', border: '#e0245e' },
                    font: { color: '#e0245e', size: 14 },
                    borderWidth: 2,
                    shapeProperties: { borderRadius: 7 },
                    margin: 8,
                })
            }
        })
        var edges = data.edges.map(function (e) {
            var cross = e.kind === 'cross'
            var col = e.dangling ? '#e0245e' : cross ? '#d98324' : '#c3ccd8'
            return {
                from: e.source,
                to: e.target,
                arrows: { to: { scaleFactor: 0.6 } },
                dashes: cross,
                label: cross ? e.predicate : undefined,
                font: {
                    size: 11,
                    color: col,
                    strokeWidth: 3,
                    strokeColor: '#ffffff',
                },
                color: { color: col, highlight: '#5b6b7f' },
                width: cross ? 2 : 1.2,
            }
        })
        document.getElementById('libarticles').innerHTML =
            data.articles
                .map(function (a) {
                    return (
                        '<span class="lg"><i style="background:' +
                        articleColor(a.id) +
                        '"></i>' +
                        esc(a.id) +
                        '</span>'
                    )
                })
                .join('') +
            '<span class="muted">' +
            data.counts.statements +
            ' statements · ' +
            data.counts.cross_edges +
            ' cross-links</span>'
        var net = new vis.Network(
            document.getElementById('net'),
            { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) },
            {
                physics: {
                    enabled: true,
                    stabilization: { iterations: 200 },
                    barnesHut: {
                        springLength: 140,
                        gravitationalConstant: -8000,
                    },
                },
                interaction: { hover: true, tooltipDelay: 120 },
            }
        )
        net.on('click', function (p) {
            if (p.nodes.length) {
                showNode(p.nodes[0])
            } else {
                document.getElementById('panel').innerHTML =
                    '<span class="hint">Click a node to inspect it.</span>'
            }
        })
    }

    document.addEventListener('DOMContentLoaded', function () {
        var view = document.querySelector('.graph-view')
        if (!view) return
        fetch(view.dataset.libraryUrl)
            .then(function (r) {
                return r.json()
            })
            .then(render)
            .catch(function () {
                document.getElementById('net').innerHTML =
                    '<p class="muted">Failed to load library.</p>'
            })
    })
})()
