/**
 * app.js — Drobné JS utility pro Teorie Grafů aplikaci
 */

document.addEventListener('DOMContentLoaded', function () {
    // ========================================================================
    // Formulář — loading overlay při submit
    // ========================================================================
    const form = document.getElementById('generateForm');
    if (form) {
        form.addEventListener('submit', function () {
            // Vytvoř spinner overlay
            const overlay = document.createElement('div');
            overlay.className = 'spinner-overlay';
            overlay.innerHTML = `
                <div class="text-center">
                    <div class="spinner-border text-primary" style="width: 3rem; height: 3rem;" role="status">
                        <span class="visually-hidden">Generuji...</span>
                    </div>
                    <p class="text-muted mt-3">Generuji grafy...</p>
                </div>
            `;
            document.body.appendChild(overlay);

            // Aktivuj po malém delay pro animation
            requestAnimationFrame(function () {
                overlay.classList.add('active');
            });
        });

        // Validace min/max
        const nodeMin = document.getElementById('node_min');
        const nodeMax = document.getElementById('node_max');
        const edgeMin = document.getElementById('edge_min');
        const edgeMax = document.getElementById('edge_max');

        function validateMinMax(minEl, maxEl) {
            if (parseInt(minEl.value) > parseInt(maxEl.value)) {
                maxEl.value = minEl.value;
            }
        }

        if (nodeMin && nodeMax) {
            nodeMin.addEventListener('change', () => validateMinMax(nodeMin, nodeMax));
            nodeMax.addEventListener('change', () => validateMinMax(nodeMin, nodeMax));
        }

        if (edgeMin && edgeMax) {
            edgeMin.addEventListener('change', () => validateMinMax(edgeMin, edgeMax));
            edgeMax.addEventListener('change', () => validateMinMax(edgeMin, edgeMax));
        }

        // Logika checkboxů — interakce acyklický + orientovaný
        const acyclicCheck = document.getElementById('acyclic');
        const directedCheck = document.getElementById('directed');
        const bipartiteCheck = document.getElementById('bipartite');

        if (acyclicCheck && directedCheck) {
            acyclicCheck.addEventListener('change', function () {
                if (this.checked && !directedCheck.checked) {
                    // Acyklický + neorientovaný = strom → info
                    const edgeFields = document.querySelectorAll('#edge_min, #edge_max');
                    edgeFields.forEach(function (el) {
                        el.disabled = true;
                        el.title = 'Strom: počet hran = uzly - 1';
                    });
                } else {
                    const edgeFields = document.querySelectorAll('#edge_min, #edge_max');
                    edgeFields.forEach(function (el) {
                        el.disabled = false;
                        el.title = '';
                    });
                }
            });

            directedCheck.addEventListener('change', function () {
                // Trigger acyclic logic recheck
                acyclicCheck.dispatchEvent(new Event('change'));
            });
        }
    }

    // ========================================================================
    // Smooth scroll pro interní odkazy
    // ========================================================================
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // ========================================================================
    // Tooltip inicializace
    // ========================================================================
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
