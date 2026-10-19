/**
 * graph_visualizer.js — SVG-based graph algorithm step-by-step visualizer
 *
 * Renders a graph on SVG, fetches algorithm steps from the API,
 * and animates through them with edge coloring. Includes drag&drop.
 */

(function () {
    'use strict';

    // ========================================================================
    // CONSTANTS & COLORS (Light Theme for PEF Mendelu)
    // ========================================================================
    const COLORS = {
        defaultEdge: '#adb5bd',   // Light gray
        examine: '#ffc107',       // Yellow
        accept: '#198754',        // Green
        reject: '#dc3545',        // Red
        defaultNode: '#0054a6',   // PEF Blue
        highlightNode: '#ffc107', // Yellow
        nodeStroke: '#003a75',    // Darker Blue
        text: '#ffffff',          // White text inside nodes
        weightText: '#dc3545',    // Red for weights
        bg: '#ffffff',
    };

    const NODE_RADIUS = 22;
    const EDGE_WIDTH_DEFAULT = 2.5;
    const EDGE_WIDTH_HIGHLIGHT = 5;

    // ========================================================================
    // STATE
    // ========================================================================
    let graphData = null;
    let algoData = null;
    let currentStep = 0;
    let isPlaying = false;
    let playInterval = null;
    let nodePositions = {};
    let speed = 1000;

    // Drag and drop state
    let draggedNode = null;
    let dragOffset = { x: 0, y: 0 };

    // ========================================================================
    // DOM REFS
    // ========================================================================
    const svg = document.getElementById('graphSvg');
    const graphId = document.getElementById('graphId')?.value;
    const algoSelect = document.getElementById('algoSelect');
    const loadBtn = document.getElementById('loadAlgoBtn');
    const btnReset = document.getElementById('btnReset');
    const btnPrev = document.getElementById('btnPrev');
    const btnPlay = document.getElementById('btnPlay');
    const btnNext = document.getElementById('btnNext');
    const btnEnd = document.getElementById('btnEnd');
    const playIcon = document.getElementById('playIcon');
    const speedSlider = document.getElementById('speedSlider');
    const speedLabel = document.getElementById('speedLabel');
    const stepCounter = document.getElementById('stepCounter');
    const stepDescription = document.getElementById('stepDescription');
    const progressBar = document.getElementById('progressBar');
    const algoTitle = document.getElementById('algoTitle');
    const stepsLog = document.getElementById('stepsLog');
    const loadingOverlay = document.getElementById('loadingOverlay');

    if (!svg || !graphId) return;

    // Set SVG background
    svg.parentElement.style.background = COLORS.bg;

    // ========================================================================
    // DRAG AND DROP LOGIC
    // ========================================================================
    svg.addEventListener('mousedown', (e) => {
        const target = e.target;
        if (target.classList.contains('node-circle') || target.tagName === 'text') {
            const group = target.closest('.graph-node');
            if (group) {
                draggedNode = group.id.replace('node-', '');
                const p = nodePositions[draggedNode];
                if (!p) return;

                // Stop force layout if running (not applicable here as layout is precomputed)

                // Get exact mouse position relative to SVG
                const pt = svg.createSVGPoint();
                pt.x = e.clientX;
                pt.y = e.clientY;
                const svgP = pt.matrixTransform(svg.getScreenCTM().inverse());

                dragOffset.x = p.x - svgP.x;
                dragOffset.y = p.y - svgP.y;

                // Bring group to top
                svg.getElementById('nodes').appendChild(group);
            }
        }
    });

    svg.addEventListener('mousemove', (e) => {
        if (!draggedNode) return;
        const pt = svg.createSVGPoint();
        pt.x = e.clientX;
        pt.y = e.clientY;
        const svgP = pt.matrixTransform(svg.getScreenCTM().inverse());

        const p = nodePositions[draggedNode];
        p.x = svgP.x + dragOffset.x;
        p.y = svgP.y + dragOffset.y;

        updateGraphPositions();
    });

    svg.addEventListener('mouseup', () => { draggedNode = null; });
    svg.addEventListener('mouseleave', () => { draggedNode = null; });

    function updateGraphPositions() {
        if (!graphData) return;

        // Update single node position in DOM
        const p = nodePositions[draggedNode];
        const g = document.getElementById(`node-${draggedNode}`);
        if (g) {
            const circle = g.querySelector('circle');
            const text = g.querySelector('text');
            if (circle) {
                circle.setAttribute('cx', p.x);
                circle.setAttribute('cy', p.y);
            }
            if (text) {
                text.setAttribute('x', p.x);
                text.setAttribute('y', p.y + 5);
            }
        }

        // Update connected lines and weights
        graphData.edges.forEach((edge) => {
            if (edge.source == draggedNode || edge.target == draggedNode) {
                const p1 = nodePositions[edge.source];
                const p2 = nodePositions[edge.target];
                
                // Keep order stable for lookup
                const s = edge.source;
                const t = edge.target;

                const line = document.getElementById(edgeKey(s, t));
                if (line) {
                    // depending on how it was created
                    const isOriginalDirect = line.getAttribute('data-source') == s;
                    if (isOriginalDirect) {
                        line.setAttribute('x1', p1.x);
                        line.setAttribute('y1', p1.y);
                        line.setAttribute('x2', p2.x);
                        line.setAttribute('y2', p2.y);
                    } else {
                        line.setAttribute('x1', p2.x);
                        line.setAttribute('y1', p2.y);
                        line.setAttribute('x2', p1.x);
                        line.setAttribute('y2', p1.y);
                    }
                }

                // Update weight
                if (graphData.weighted) {
                    const wbg = document.getElementById(`weight-bg-${s}-${t}`);
                    const wtxt = document.getElementById(`weight-text-${s}-${t}`);
                    if (wbg && wtxt) {
                        const mx = (p1.x + p2.x) / 2;
                        const my = (p1.y + p2.y) / 2;
                        const dx = p2.x - p1.x;
                        const dy = p2.y - p1.y;
                        const len = Math.sqrt(dx * dx + dy * dy) || 1;
                        const offx = (-dy / len) * 14;
                        const offy = (dx / len) * 14;

                        wbg.setAttribute('x', mx + offx - 12);
                        wbg.setAttribute('y', my + offy - 10);
                        wtxt.setAttribute('x', mx + offx);
                        wtxt.setAttribute('y', my + offy + 3);
                    }
                }
            }
        });
    }

    // ========================================================================
    // LAYOUT — Simple force-directed
    // ========================================================================
    function computeLayout(nodes, edges, width, height) {
        const positions = {};
        const n = nodes.length;

        // Initialize
        nodes.forEach((node, i) => {
            const angle = (2 * Math.PI * i) / n - Math.PI / 2;
            const cx = width / 2;
            const cy = height / 2;
            const r = Math.min(width, height) * 0.35;
            positions[node] = {
                x: cx + r * Math.cos(angle),
                y: cy + r * Math.sin(angle),
                vx: 0, vy: 0,
            };
        });

        const iterations = 120;
        const repulsion = 5000;
        const attraction = 0.005;
        const idealLength = 140;
        const damping = 0.9;
        const centerGravity = 0.01;

        for (let iter = 0; iter < iterations; iter++) {
            // Repulsive
            for (let i = 0; i < n; i++) {
                for (let j = i + 1; j < n; j++) {
                    const a = positions[nodes[i]];
                    const b = positions[nodes[j]];
                    let dx = a.x - b.x;
                    let dy = a.y - b.y;
                    let dist = Math.sqrt(dx * dx + dy * dy) || 1;
                    let force = repulsion / (dist * dist);
                    let fx = (dx / dist) * force;
                    let fy = (dy / dist) * force;
                    a.vx += fx; a.vy += fy;
                    b.vx -= fx; b.vy -= fy;
                }
            }
            // Attractive
            edges.forEach((e) => {
                const a = positions[e.source];
                const b = positions[e.target];
                if (!a || !b) return;
                let dx = b.x - a.x;
                let dy = b.y - a.y;
                let dist = Math.sqrt(dx * dx + dy * dy) || 1;
                let force = attraction * (dist - idealLength);
                let fx = (dx / dist) * force;
                let fy = (dy / dist) * force;
                a.vx += fx; a.vy += fy;
                b.vx -= fx; b.vy -= fy;
            });
            // Gravity
            const cx = width / 2;
            const cy = height / 2;
            nodes.forEach((node) => {
                const p = positions[node];
                p.vx += (cx - p.x) * centerGravity;
                p.vy += (cy - p.y) * centerGravity;
            });
            // Update
            const padding = NODE_RADIUS + 10;
            nodes.forEach((node) => {
                const p = positions[node];
                p.vx *= damping; p.vy *= damping;
                p.x += p.vx; p.y += p.vy;
                p.x = Math.max(padding, Math.min(width - padding, p.x));
                p.y = Math.max(padding, Math.min(height - padding, p.y));
            });
        }
        return positions;
    }

    // ========================================================================
    // SVG RENDERING
    // ========================================================================
    function createSVGElement(tag, attrs) {
        const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
        for (const [key, val] of Object.entries(attrs)) {
            el.setAttribute(key, val);
        }
        return el;
    }

    function renderGraph() {
        if (!graphData) return;
        svg.innerHTML = '';

        const container = svg.parentElement;
        const width = container.clientWidth || 700;
        const height = container.clientHeight || 550;
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

        const { nodes, edges, weighted, positions } = graphData;
        
        // Preserve layout if the exact same nodes are already positioned
        let reuseLayout = false;
        if (Object.keys(nodePositions).length === nodes.length) {
            reuseLayout = nodes.every(n => !!nodePositions[n]);
        }
        
        if (!reuseLayout) {
            if (positions && Object.keys(positions).length === nodes.length) {
                // Obnovení ze serveru
                nodePositions = {};
                for (let k in positions) {
                    nodePositions[k] = { x: positions[k].x, y: positions[k].y, vx: 0, vy: 0 };
                }
            } else {
                nodePositions = computeLayout(nodes, edges, width, height);
            }
        }

        // Arrow Defs
        const defs = createSVGElement('defs', {});
        const marker = createSVGElement('marker', {
            id: 'arrowhead', markerWidth: '10', markerHeight: '7',
            refX: '10', refY: '3.5', orient: 'auto',
        });
        const polygon = createSVGElement('polygon', {
            points: '0 0, 10 3.5, 0 7', fill: COLORS.defaultEdge,
        });
        marker.appendChild(polygon);
        defs.appendChild(marker);
        svg.appendChild(defs);

        // Edges
        const edgeGroup = createSVGElement('g', { id: 'edges' });
        edges.forEach((edge) => {
            const p1 = nodePositions[edge.source];
            const p2 = nodePositions[edge.target];
            if (!p1 || !p2) return;

            const line = createSVGElement('line', {
                x1: p1.x, y1: p1.y, x2: p2.x, y2: p2.y,
                stroke: COLORS.defaultEdge,
                'stroke-width': EDGE_WIDTH_DEFAULT,
                'stroke-linecap': 'round',
                'data-source': edge.source,
                'data-target': edge.target,
                class: 'graph-edge',
                id: `edge-${edge.source}-${edge.target}`,
            });

            if (graphData.directed) {
                line.setAttribute('marker-end', 'url(#arrowhead)');
            }
            edgeGroup.appendChild(line);

            if (weighted && edge.weight != null) {
                const mx = (p1.x + p2.x) / 2;
                const my = (p1.y + p2.y) / 2;
                const dx = p2.x - p1.x;
                const dy = p2.y - p1.y;
                const len = Math.sqrt(dx * dx + dy * dy) || 1;
                const offx = (-dy / len) * 14;
                const offy = (dx / len) * 14;

                const bg = createSVGElement('rect', {
                    x: mx + offx - 12, y: my + offy - 10,
                    width: 24, height: 18, rx: 4,
                    fill: '#f8f9fa', 'fill-opacity': 0.95,
                    stroke: '#dee2e6', 'stroke-width': 1,
                    id: `weight-bg-${edge.source}-${edge.target}`
                });
                edgeGroup.appendChild(bg);

                const text = createSVGElement('text', {
                    x: mx + offx, y: my + offy + 3,
                    'text-anchor': 'middle',
                    'font-size': '11', 'font-weight': '600',
                    fill: COLORS.weightText,
                    class: 'weight-label',
                    id: `weight-text-${edge.source}-${edge.target}`
                });
                text.textContent = edge.weight;
                edgeGroup.appendChild(text);
            }
        });
        svg.appendChild(edgeGroup);

        // Nodes
        const nodeGroup = createSVGElement('g', { id: 'nodes' });
        nodes.forEach((node) => {
            const pos = nodePositions[node];
            if (!pos) return;

            const g = createSVGElement('g', {
                class: 'graph-node',
                id: `node-${node}`,
            });

            const circle = createSVGElement('circle', {
                cx: pos.x, cy: pos.y, r: NODE_RADIUS,
                fill: COLORS.defaultNode,
                stroke: COLORS.nodeStroke,
                'stroke-width': 2.5,
                class: 'node-circle',
            });
            g.appendChild(circle);

            const label = createSVGElement('text', {
                x: pos.x, y: pos.y + 5,
                'text-anchor': 'middle', 'font-size': '14', 'font-weight': 'bold',
                fill: COLORS.text, 'pointer-events': 'none',
            });
            label.textContent = node;
            g.appendChild(label);

            nodeGroup.appendChild(g);
        });
        svg.appendChild(nodeGroup);
    }

    // ========================================================================
    // STEP RENDERING
    // ========================================================================
    function edgeKey(source, target) {
        return `edge-${source}-${target}`;
    }

    function findEdgeElement(source, target) {
        let el = document.getElementById(edgeKey(source, target));
        if (!el) {
            el = document.getElementById(edgeKey(target, source));
        }
        return el;
    }

    function resetEdgesAndNodes() {
        document.querySelectorAll('.graph-edge').forEach((el) => {
            el.setAttribute('stroke', COLORS.defaultEdge);
            el.setAttribute('stroke-width', EDGE_WIDTH_DEFAULT);
        });
        document.querySelectorAll('.node-circle').forEach((el) => {
            el.setAttribute('fill', COLORS.defaultNode);
            el.setAttribute('stroke', COLORS.nodeStroke);
        });
    }

    function applyStep(stepIdx) {
        if (!algoData || !algoData.steps) return;
        const step = algoData.steps[stepIdx];
        if (!step) return;

        resetEdgesAndNodes();

        if (step.selected_edges) {
            step.selected_edges.forEach(([s, t]) => {
                const el = findEdgeElement(s, t);
                if (el) {
                    el.setAttribute('stroke', COLORS.accept);
                    el.setAttribute('stroke-width', EDGE_WIDTH_HIGHLIGHT);
                }
            });
        }

        if (step.current_edge) {
            const [s, t] = step.current_edge;
            const el = findEdgeElement(s, t);
            if (el) {
                let color = COLORS.examine;
                if (step.action === 'accept') color = COLORS.accept;
                else if (step.action === 'reject') color = COLORS.reject;
                el.setAttribute('stroke', color);
                el.setAttribute('stroke-width', EDGE_WIDTH_HIGHLIGHT);
            }
        }

        if (step.highlight_nodes && step.highlight_nodes.length > 0) {
            step.highlight_nodes.forEach((n) => {
                const nodeEl = document.querySelector(`#node-${n} .node-circle`);
                if (nodeEl) {
                    nodeEl.setAttribute('fill', COLORS.highlightNode);
                    nodeEl.setAttribute('stroke', '#d39e00');
                }
            });
        }

        stepDescription.innerHTML = formatDescription(step);
        stepCounter.textContent = `Krok ${stepIdx} / ${algoData.steps.length - 1}`;
        progressBar.style.width = `${(stepIdx / Math.max(algoData.steps.length - 1, 1)) * 100}%`;

        if (step.action === 'done') {
            progressBar.className = 'progress-bar bg-success';
        } else {
            progressBar.className = 'progress-bar';
        }

        updateLog(stepIdx);
    }

    function formatDescription(step) {
        let actionBadge = '';
        if (step.action === 'init') actionBadge = '<span class="badge bg-info me-2">INIT</span>';
        else if (step.action === 'examine') actionBadge = '<span class="badge bg-warning text-dark me-2">ZKOUMÁ</span>';
        else if (step.action === 'accept') actionBadge = '<span class="badge bg-success me-2">PŘIJATO</span>';
        else if (step.action === 'reject') actionBadge = '<span class="badge bg-danger me-2">ZAMÍTNUTO</span>';
        else if (step.action === 'done') actionBadge = '<span class="badge bg-primary me-2">HOTOVO</span>';
        return actionBadge + step.description;
    }

    function updateLog(upToStep) {
        if (!algoData) return;
        let html = '';
        for (let i = 0; i <= upToStep && i < algoData.steps.length; i++) {
            const s = algoData.steps[i];
            const activeClass = i === upToStep ? 'step-log-active' : '';
            let actionClass = '';
            if (s.action === 'accept') actionClass = 'step-accept';
            else if (s.action === 'reject') actionClass = 'step-reject';
            else if (s.action === 'examine') actionClass = 'step-examine';
            else if (s.action === 'done') actionClass = 'step-done';

            html += `<div class="step-log-item ${activeClass} ${actionClass}" data-step="${i}">
                <span class="step-num">${i}</span>
                <span class="step-text">${s.description}</span>
            </div>`;
        }
        stepsLog.innerHTML = html;

        stepsLog.querySelectorAll('.step-log-item').forEach((el) => {
            el.addEventListener('click', () => {
                currentStep = parseInt(el.dataset.step);
                applyStep(currentStep);
                updateButtons();
            });
        });

        const active = stepsLog.querySelector('.step-log-active');
        if (active) active.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }

    // ========================================================================
    // CONTROLS
    // ========================================================================
    function updateButtons() {
        if (!algoData) {
            [btnReset, btnPrev, btnPlay, btnNext, btnEnd].forEach((b) => (b.disabled = true));
            return;
        }
        const maxStep = algoData.steps.length - 1;
        btnReset.disabled = currentStep === 0;
        btnPrev.disabled = currentStep === 0;
        btnNext.disabled = currentStep >= maxStep;
        btnEnd.disabled = currentStep >= maxStep;
        btnPlay.disabled = false;
    }

    function stepForward() {
        if (!algoData) return;
        if (currentStep < algoData.steps.length - 1) {
            currentStep++;
            applyStep(currentStep);
            updateButtons();
        } else stopPlaying();
    }

    function stepBackward() {
        if (!algoData) return;
        if (currentStep > 0) {
            currentStep--;
            applyStep(currentStep);
            updateButtons();
        }
    }

    function goToStart() { currentStep = 0; applyStep(currentStep); updateButtons(); }
    function goToEnd() {
        if (!algoData) return;
        currentStep = algoData.steps.length - 1;
        applyStep(currentStep);
        updateButtons();
        stopPlaying();
    }

    function startPlaying() {
        if (isPlaying || !algoData) return;
        if (currentStep >= algoData.steps.length - 1) currentStep = 0;
        isPlaying = true;
        playIcon.className = 'bi bi-pause-fill';
        playInterval = setInterval(() => {
            stepForward();
            if (currentStep >= algoData.steps.length - 1) stopPlaying();
        }, speed);
    }

    function stopPlaying() {
        isPlaying = false;
        playIcon.className = 'bi bi-play-fill';
        if (playInterval) { clearInterval(playInterval); playInterval = null; }
    }

    function togglePlay() { isPlaying ? stopPlaying() : startPlaying(); }

    // ========================================================================
    // LOAD ALGORITHM
    // ========================================================================
    async function loadAlgorithm() {
        const algo = algoSelect.value;
        if (!algo || !graphId) return;

        loadingOverlay.style.display = 'flex';
        loadingOverlay.style.setProperty('display', 'flex', 'important');
        stopPlaying();

        try {
            let url = `/api/visualize/${graphId}/${algo}`;
            const srcSel = document.getElementById('sourceNodeSelect');
            const tgtSel = document.getElementById('targetNodeSelect');
            
            if (srcSel && tgtSel) {
                // If visible, append values
                const s = srcSel.value;
                const t = tgtSel.value;
                url += `?source=${s}&target=${t}`;
            }

            const response = await fetch(url);
            const data = await response.json();

            if (data.error) {
                stepDescription.innerHTML = `<span class="text-danger"><i class="bi bi-exclamation-triangle me-1"></i>${data.error}</span>`;
                return;
            }

            algoData = data;
            graphData = data.graph_data;
            currentStep = 0;

            algoTitle.innerHTML = `<i class="bi bi-diagram-3 me-2"></i>${data.algorithm_name || algo}`;

            renderGraph();
            applyStep(0);
            updateButtons();
        } catch (err) {
            stepDescription.innerHTML = `<span class="text-danger">Chyba: ${err.message}</span>`;
        } finally {
            loadingOverlay.style.setProperty('display', 'none', 'important');
        }
    }

    if (loadBtn) loadBtn.addEventListener('click', loadAlgorithm);
    if (btnReset) btnReset.addEventListener('click', goToStart);
    if (btnPrev) btnPrev.addEventListener('click', stepBackward);
    if (btnPlay) btnPlay.addEventListener('click', togglePlay);
    if (btnNext) btnNext.addEventListener('click', stepForward);
    if (btnEnd) btnEnd.addEventListener('click', goToEnd);

    if (speedSlider) {
        speedSlider.addEventListener('input', () => {
            speed = parseInt(speedSlider.value);
            speedLabel.textContent = (speed / 1000).toFixed(1) + 's';
            if (isPlaying) { stopPlaying(); startPlaying(); }
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
        switch (e.key) {
            case 'ArrowRight': e.preventDefault(); stepForward(); break;
            case 'ArrowLeft': e.preventDefault(); stepBackward(); break;
            case ' ': e.preventDefault(); togglePlay(); break;
            case 'Home': e.preventDefault(); goToStart(); break;
            case 'End': e.preventDefault(); goToEnd(); break;
        }
    });

    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            if (graphData) { renderGraph(); if (algoData) applyStep(currentStep); }
        }, 250);
    });

    async function loadStaticGraph() {
        if (!graphId) return;
        try {
            const response = await fetch(`/api/graph/${graphId}`);
            const data = await response.json();
            if (data.error) return;
            graphData = data.graph_data_vis;
            graphData.positions = data.positions;
            renderGraph();
        } catch (err) {
            console.error("Failed to load static graph", err);
        }
    }

    function saveAndDownloadSVGAsPNG() {
        if (!svg || !graphId) return;
        const btn = document.getElementById('btnDownloadPng');
        const oldHtml = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status"></span>Ukládám...';
        btn.disabled = true;

        const clone = svg.cloneNode(true);
        const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        bg.setAttribute('width', '100%');
        bg.setAttribute('height', '100%');
        bg.setAttribute('fill', '#ffffff');
        clone.insertBefore(bg, clone.firstChild);

        const serializer = new XMLSerializer();
        const svgString = serializer.serializeToString(clone);
        const svgBlob = new Blob([svgString], {type: 'image/svg+xml;charset=utf-8'});
        const URL = window.URL || window.webkitURL || window;
        const blobURL = URL.createObjectURL(svgBlob);

        const img = new Image();
        img.onload = async function() {
            const canvas = document.createElement('canvas');
            canvas.width = svg.clientWidth || 800;
            canvas.height = svg.clientHeight || 550;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0);
            const png = canvas.toDataURL('image/png');
            
            try {
                // Poslat na server k uložení
                await fetch(`/api/graph/${graphId}/save_png`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        image: png,
                        positions: nodePositions
                    })
                });

                // Spustit nativní stahování přes Blob URL (spolehlivější než Data URI)
                canvas.toBlob((blob) => {
                    const dlUrl = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.download = `graf_${graphId}.png`;
                    a.href = dlUrl;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(dlUrl);
                }, 'image/png');
                
            } catch (err) {
                console.error("Chyba při ukládání PNG na server", err);
            } finally {
                URL.revokeObjectURL(blobURL);
                btn.innerHTML = '<i class="bi bi-check2 me-1"></i>Uloženo!';
                setTimeout(() => {
                    btn.innerHTML = oldHtml;
                    btn.disabled = false;
                }, 2000);
            }
        };
        img.src = blobURL;
    }

    const btnDownloadPng = document.getElementById('btnDownloadPng');
    if (btnDownloadPng) {
        btnDownloadPng.addEventListener('click', saveAndDownloadSVGAsPNG);
    }

    if (algoSelect && algoSelect.options.length > 0) {
        loadAlgorithm();
    } else {
        const isStaticEditor = document.getElementById('isStaticEditor');
        if (isStaticEditor && isStaticEditor.value === 'true') {
            loadStaticGraph();
        }
    }
})();
