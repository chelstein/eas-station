/**
 * Snow Emergency Management Module
 * Handles snow emergency level management and visualization
 * 
 * Dependencies (loaded from core.js): showToast(), showStatus(), showConfirmation(), escapeHtmlAdmin()
 * External libraries: Mermaid.js for diagram rendering
 */

// ===== SNOW EMERGENCY ADMIN FUNCTIONS =====
const SNOW_LEVELS = {
    0: { name: 'None', color: '#28a745', bgClass: 'bg-success' },
    1: { name: 'Level 1', color: '#ffc107', bgClass: 'bg-warning' },
    2: { name: 'Level 2', color: '#fd7e14', bgClass: '' },
    3: { name: 'Level 3', color: '#dc3545', bgClass: 'bg-danger' }
};

function buildSnowMapGraph() {
    return `block-beta
    columns 3
    
    DF(["Defiance"]):1
    HE(["Henry"]):1
    WO(["Wood"]):1
    
    PA(["Paulding"]):1
    PU(["★ Putnam ★"]):1
    HA(["Hancock"]):1
    
    VW(["Van Wert"]):1
    AL(["Allen"]):1
    space:1
    
    classDef county fill:#e3f2fd,stroke:#0d6efd,color:#0d6efd,stroke-width:2px
    classDef neighbor fill:#f8f9fa,stroke:#6c757d,color:#212529,stroke-width:1.5px
    class PU county
    class DF,HE,WO,PA,HA,VW,AL neighbor`;
}

function initializeSnowMermaid() {
    const map = document.querySelector('.mermaid-snow-map');
    if (!map) return;

    const renderMermaid = () => {
        try {
            if (!window.mermaid) return;

            map.removeAttribute('data-processed');
            map.textContent = buildSnowMapGraph();

            mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' });
            mermaid.run({ nodes: [map] });
        } catch (err) {
            console.warn('Failed to render mermaid map', err);
        }
    };

    if (window.mermaid) {
        renderMermaid();
        return;
    }

    const mermaidScript = document.getElementById('mermaid-lib');
    if (mermaidScript) {
        mermaidScript.addEventListener('load', renderMermaid, { once: true });
        mermaidScript.addEventListener('error', () => console.warn('Mermaid library failed to load'));
    }
}

async function refreshSnowEmergencyAdmin() {
    const container = document.getElementById('admin-snow-emergency-editor');
    if (!container) return;

    container.innerHTML = `
        <div class="text-center text-muted py-4">
            <i class="fas fa-spinner fa-spin fa-2x mb-2"></i>
            <p>Loading snow emergency data...</p>
        </div>
    `;

    try {
        const response = await fetch('/api/snow_emergencies/all', {
            headers: { 'Accept': 'application/json' }
        });
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(data.message || data.error || 'Failed to load snow emergency data');
        }
        renderSnowEmergencyAdmin(data);
    } catch (error) {
        console.error('Error loading snow emergencies:', error);
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Failed to load snow emergency data: ${error.message}
            </div>
        `;
    }
}

function renderSnowEmergencyAdmin(data) {
    const container = document.getElementById('admin-snow-emergency-editor');
    if (!container) return;

    const emergencies = data.emergencies || [];
    const levels = data.levels || SNOW_LEVELS;

    let html = '<div class="row g-3">';
    emergencies.forEach(e => {
        const levelInfo = levels[e.level] || SNOW_LEVELS[e.level] || { name: 'Unknown', color: '#6c757d' };
        const isPrimary = e.is_primary || false;
        const isOptOut = e.issues_emergencies === false;
        const history = Array.isArray(e.history) ? [...e.history].reverse() : [];
        const historyHtml = history.length
            ? history
                .map(entry => `
                    <div class="d-flex flex-column mb-1">
                        <span class="text-muted small">${formatSnowTimestamp(entry.set_at)} • ${escapeHtmlAdmin(entry.set_by || 'Unknown')}</span>
                        <span class="small">Level ${entry.previous_level ?? 0} ➜ Level ${entry.new_level ?? e.level}</span>
                    </div>
                `)
                .join('')
            : '<div class="text-muted small">No history recorded yet.</div>';
        html += `
            <div class="col-md-6 col-lg-4 col-xl-3">
                <div class="card h-100 ${isOptOut ? 'border-secondary' : e.level > 0 ? 'border-' + (e.level === 3 ? 'danger' : 'warning') : 'border-success'}">
                    <div class="card-header d-flex justify-content-between align-items-start py-2" style="background-color: ${levelInfo.color}20;">
                        <div>
                            <strong class="small">${escapeHtmlAdmin(e.county_name)} County</strong>
                            ${isPrimary ? '<span class="badge bg-primary ms-2">Primary</span>' : ''}
                        </div>
                        ${isOptOut ? '<span class="badge bg-secondary ms-2">No snow policy</span>' : ''}
                    </div>
                    <div class="card-body py-2">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <span class="badge" style="background-color: ${levelInfo.color};">
                                ${escapeHtmlAdmin(levelInfo.name || e.level_name)}
                            </span>
                            <small class="text-muted">${e.level_set_by ? `Set by ${escapeHtmlAdmin(e.level_set_by)}` : 'Not set yet'}</small>
                        </div>
                        <div class="form-check form-switch small mb-2">
                            <input class="form-check-input" type="checkbox" id="snow-policy-${e.county_fips}" ${isOptOut ? '' : 'checked'}
                                onchange="toggleSnowPolicyAdmin('${e.county_fips}', this.checked, '${escapeHtmlAdmin(e.county_name)}')">
                            <label class="form-check-label" for="snow-policy-${e.county_fips}">Issues snow emergencies</label>
                        </div>
                        ${isOptOut ? '<div class="snow-policy-note mb-2">Marked as opting out. Levels remain at None.</div>' : ''}
                        <div class="btn-group w-100" role="group">
                            ${[0, 1, 2, 3].map(level => {
                                const lvlInfo = levels[level] || SNOW_LEVELS[level];
                                const isActive = e.level === level;
                                let btnClass = 'btn-outline-secondary';
                                let btnStyle = '';
                                if (level === 0) btnClass = isActive ? 'btn-success' : 'btn-outline-success';
                                else if (level === 1) btnClass = isActive ? 'btn-warning' : 'btn-outline-warning';
                                else if (level === 2) {
                                    btnClass = isActive ? 'btn-secondary' : 'btn-outline-secondary';
                                    btnStyle = isActive ? 'background-color: #fd7e14; border-color: #fd7e14; color: white;' : 'color: #fd7e14; border-color: #fd7e14;';
                                }
                                else if (level === 3) btnClass = isActive ? 'btn-danger' : 'btn-outline-danger';
                                return `
                                    <button type="button"
                                        class="btn btn-sm ${btnClass} ${isActive ? 'active' : ''}"
                                        onclick="updateSnowLevelAdmin('${e.county_fips}', ${level}, '${escapeHtmlAdmin(e.county_name)}')"
                                        ${isActive || isOptOut ? 'disabled' : ''}
                                        style="${btnStyle}"
                                        title="${lvlInfo.name}">
                                        ${level === 0 ? '✓' : level}
                                    </button>
                                `;
                            }).join('')}
                        </div>
                        <details class="snow-history mt-3">
                            <summary class="small text-muted">Change history (${history.length})</summary>
                            <div class="small mt-2">${historyHtml}</div>
                        </details>
                    </div>
                </div>
            </div>
        `;
    });
    html += '</div>';

    const activeCount = emergencies.filter(e => e.level > 0 && e.issues_emergencies !== false).length;
    const optOutCount = emergencies.filter(e => e.issues_emergencies === false).length;
    html += `
        <div class="mt-3 text-muted small">
            <i class="fas fa-info-circle me-1"></i>
            ${activeCount} of ${emergencies.length} counties have active snow emergencies.
            ${optOutCount > 0 ? `${optOutCount} marked as not issuing snow emergencies.` : ''}
        </div>
    `;

    container.innerHTML = html;
}

async function updateSnowLevelAdmin(fips, level, countyName) {
    try {
        const response = await fetch(`/api/snow_emergencies/${fips}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify({ level: level, issues_emergencies: true })
        });

        const result = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(result.error || result.message || 'Failed to update');
        }

        showStatus(`✓ ${countyName} County updated to ${result.emergency.level_name}`, 'success', 3000);
        refreshSnowEmergencyAdmin();
    } catch (error) {
        console.error('Failed to update snow emergency:', error);
        showStatus(`✗ Failed to update ${countyName} County: ${error.message}`, 'danger', 5000);
    }
}

async function toggleSnowPolicyAdmin(fips, allow, countyName) {
    try {
        const payload = { issues_emergencies: allow };
        if (!allow) {
            payload.level = 0;
        }

        const response = await fetch(`/api/snow_emergencies/${fips}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(result.error || result.message || 'Failed to update policy');
        }

        const label = allow ? 'now issuing snow emergencies' : 'does not issue snow emergencies';
        showStatus(`✓ ${countyName} County ${label}`, 'success', 3000);
        refreshSnowEmergencyAdmin();
    } catch (error) {
        console.error('Failed to update snow emergency policy:', error);
        showStatus(`✗ Failed to update ${countyName} County: ${error.message}`, 'danger', 5000);
    }
}

function formatSnowTimestamp(timestamp) {
    if (!timestamp) return 'Unknown time';
    try {
        return new Date(timestamp).toLocaleString();
    } catch (err) {
        return timestamp;
    }
}

// Initialize snow emergency editor when the tab is shown
document.addEventListener('DOMContentLoaded', function() {
    initializeSnowMermaid();
    const snowTab = document.getElementById('snow-subtab');
    if (snowTab) {
        snowTab.addEventListener('shown.bs.tab', function() {
            initializeSnowMermaid();
            refreshSnowEmergencyAdmin();
        });
    }
});
