/**
 * Boundary Management Module
 * Handles boundary upload, preview, deletion, and GeoJSON/Shapefile operations
 * 
 * Dependencies:
 * - BOUNDARY_TYPE_CONFIG (from window)
 * - DEFAULT_BOUNDARY_TYPES (from window)
 * - sanitizeBoundaryTypeInput() (from core.js)
 * - showToast() (from utilities.js)
 * - showConfirmation() (from utilities.js)
 * - showMultiStepConfirmation() (from utilities.js)
 * - showStatus() (from utilities.js)
 * - escapeHtml() (from utilities.js)
 * - boundaryCache (global variable)
 */

// Format boundary type for display
function formatBoundaryLabel(type) {
    const sanitized = sanitizeBoundaryTypeInput(type);
    const config = BOUNDARY_TYPE_CONFIG[sanitized];
    if (config && config.label) {
        return config.label;
    }
    if (!sanitized) {
        return 'Custom Layer';
    }
    return sanitized.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase());
}

// Initialize custom type input controls
function initializeCustomTypeControls() {
    const controls = [
        { selectId: 'boundaryType', wrapperId: 'customBoundaryTypeWrapper', inputId: 'customBoundaryType' },
        { selectId: 'previewBoundaryType', wrapperId: 'customPreviewBoundaryTypeWrapper', inputId: 'customPreviewBoundaryType' },
        { selectId: 'deleteType', wrapperId: 'customDeleteBoundaryTypeWrapper', inputId: 'customDeleteBoundaryType' }
    ];
    controls.forEach(({ selectId, wrapperId, inputId }) => {
        const select = document.getElementById(selectId);
        const wrapper = document.getElementById(wrapperId);
        const input = document.getElementById(inputId);
        if (!select || !wrapper) {
            return;
        }
        const updateVisibility = () => {
            if (select.value === 'custom') {
                wrapper.style.display = 'block';
                if (input) {
                    input.focus();
                }
            } else {
                wrapper.style.display = 'none';
                if (input) {
                    input.value = '';
                }
            }
        };
        if (!select.dataset.customTypeBound) {
            select.addEventListener('change', updateVisibility);
            select.dataset.customTypeBound = 'true';
        }
        updateVisibility();
    });
}

// Get selected boundary type from dropdown or custom input
function getSelectedBoundaryType(selectId, inputId) {
    const select = document.getElementById(selectId);
    if (!select) {
        return { type: null, label: null };
    }
    if (select.value === 'custom') {
        const input = document.getElementById(inputId);
        const rawValue = input ? input.value.trim() : '';
        if (!rawValue) {
            throw new Error('Please provide a custom type name.');
        }
        const sanitized = sanitizeBoundaryTypeInput(rawValue);
        if (!sanitized) {
            throw new Error('Custom type name must include at least one letter or number.');
        }
        return { type: sanitized, label: rawValue };
    }
    if (!select.value) {
        return { type: null, label: null };
    }
    const sanitized = sanitizeBoundaryTypeInput(select.value);
    if (!sanitized) {
        return { type: null, label: null };
    }
    return { type: sanitized, label: formatBoundaryLabel(sanitized) };
}

// Add option to select if missing
function addOptionIfMissing(select, value, label) {
    if (!select || !value || select.querySelector(`option[value="${value}"]`)) {
        return;
    }
    const option = document.createElement('option');
    option.value = value;
    option.textContent = label;
    const customOption = select.querySelector('option[value="custom"]');
    if (customOption) {
        select.insertBefore(option, customOption);
    } else {
        select.appendChild(option);
    }
}

// Ensure dynamic boundary options in dropdowns
function ensureDynamicBoundaryOptions(typeEntries) {
    const typeSet = new Set((typeEntries || []).map(entry => entry.key));
    const selects = [
        document.getElementById('boundaryType'),
        document.getElementById('previewBoundaryType'),
        document.getElementById('deleteType'),
        document.getElementById('boundaryFilterSelect')
    ].filter(Boolean);
    selects.forEach(select => {
        Array.from(select.options).forEach(option => {
            const value = option.value;
            if (!value || value === 'custom' || DEFAULT_BOUNDARY_TYPES.has(value)) {
                return;
            }
            if (!typeSet.has(value)) {
                option.remove();
            }
        });
    });
    (typeEntries || []).forEach(entry => {
        if (!entry || !entry.key || DEFAULT_BOUNDARY_TYPES.has(entry.key)) {
            return;
        }
        const label = entry.label || formatBoundaryLabel(entry.key);
        addOptionIfMissing(document.getElementById('boundaryType'), entry.key, label);
        addOptionIfMissing(document.getElementById('previewBoundaryType'), entry.key, label);
        addOptionIfMissing(document.getElementById('deleteType'), entry.key, label);
    });
}

// Load server shapefiles
async function loadServerShapefiles() {
    const listDiv = document.getElementById('serverShapefilesList');
    listDiv.innerHTML = '<div class="text-center py-3"><span class="loading-spinner"></span> Loading...</div>';

    try {
        const response = await fetch('/admin/list_shapefiles');
        const result = await response.json();

        if (!response.ok) {
            listDiv.innerHTML = `<div class="alert alert-danger">${result.error}</div>`;
            return;
        }

        if (!result.shapefiles || result.shapefiles.length === 0) {
            listDiv.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle"></i> No shapefiles found in: ${result.directory || '/streams and ponds'}
                </div>`;
            return;
        }

        let html = `<div class="table-responsive"><table class="table table-hover">
            <thead>
                <tr>
                    <th>Filename</th>
                    <th>Size</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>`;

        result.shapefiles.forEach(shp => {
            const statusBadge = shp.complete
                ? '<span class="badge bg-success">Complete</span>'
                : '<span class="badge bg-warning">Missing files</span>';

            const actionBtn = shp.complete
                ? `<button class="btn btn-sm btn-primary" onclick="convertServerShapefile('${shp.path}', '${shp.suggested_type}')">
                       <i class="fas fa-download"></i> Import
                   </button>`
                : '<button class="btn btn-sm btn-secondary" disabled>Incomplete</button>';

            html += `
                <tr>
                    <td><small class="font-monospace">${shp.filename}</small></td>
                    <td>${shp.size_mb.toFixed(2)} MB</td>
                    <td><span class="badge bg-info">${shp.suggested_label}</span></td>
                    <td>${statusBadge}</td>
                    <td>${actionBtn}</td>
                </tr>`;
        });

        html += '</tbody></table></div>';
        listDiv.innerHTML = html;

    } catch (error) {
        listDiv.innerHTML = `<div class="alert alert-danger">Error loading shapefiles: ${error.message}</div>`;
    }
}

// Convert and import a shapefile from the server
async function convertServerShapefile(path, suggestedType) {
    if (!confirm(`Import shapefile as '${formatBoundaryLabel(suggestedType)}' boundaries?`)) {
        return;
    }

    const listDiv = document.getElementById('serverShapefilesList');
    const originalHTML = listDiv.innerHTML;
    listDiv.innerHTML = '<div class="text-center py-3"><span class="loading-spinner"></span> Converting and importing...</div>';

    try {
        const formData = new FormData();
        formData.append('shapefile_path', path);
        formData.append('boundary_type', suggestedType);

        const response = await fetch('/admin/upload_shapefile', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        if (response.ok) {
            showShapefileStatus(
                `✅ ${result.success}<br>` +
                `<small>Imported ${result.boundaries_added} features</small>`,
                'success'
            );
            loadBoundaries();
            loadServerShapefiles(); // Refresh the list
        } else {
            showShapefileStatus(`❌ ${result.error}`, 'danger');
            listDiv.innerHTML = originalHTML; // Restore list
        }
    } catch (error) {
        showShapefileStatus(`❌ Import error: ${error.message}`, 'danger');
        listDiv.innerHTML = originalHTML; // Restore list
    }
}

// Show status for shapefile operations
function showShapefileStatus(message, type) {
    const statusDiv = document.getElementById('shapefileUploadStatus');
    const alertClass = `alert-${type === 'success' ? 'success-custom' :
                                type === 'danger' ? 'danger-custom' :
                                'warning-custom'}`;
    statusDiv.innerHTML = `<div class="alert-custom ${alertClass}">${message}</div>`;
    setTimeout(() => {
        statusDiv.innerHTML = '';
    }, 8000);
}

// Preview extraction
async function previewExtraction() {
    const form = document.getElementById('previewForm');
    const resultsDiv = document.getElementById('previewResults');
    let selection;
    try {
        selection = getSelectedBoundaryType('previewBoundaryType', 'customPreviewBoundaryType');
    } catch (error) {
        showStatus(error.message, 'warning');
        if (resultsDiv) {
            resultsDiv.innerHTML = '';
        }
        return;
    }
    if (!selection.type) {
        showStatus('Please select a boundary type to preview.', 'warning');
        if (resultsDiv) {
            resultsDiv.innerHTML = '';
        }
        return;
    }
    const formData = new FormData(form);
    formData.set('boundary_type', selection.type);
    resultsDiv.innerHTML = '<div class="text-center py-3"><div class="loading-spinner"></div><span class="ms-2">Analyzing file...</span></div>';
    try {
        const response = await fetch('/admin/preview_geojson', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        if (response.ok) {
            const allFields = (result.all_fields || []).map(escapeHtml);
            const ownerFields = (result.owner_fields || []).map(escapeHtml);
            const lineIdFields = (result.line_id_fields || []).map(escapeHtml);
            const recommendedFields = (result.recommended_additional_fields || []).map(escapeHtml);
            let html = `
                <div class="preview-container">
                    <h5>📋 Preview Results</h5>
                    <p><strong>Total Features:</strong> ${escapeHtml(String(result.total_features))}</p>
                    <p><strong>Boundary Type:</strong> ${escapeHtml(result.boundary_type || 'Unknown')}</p>
                    <p><strong>Available Fields:</strong> ${allFields.length ? allFields.join(', ') : 'None detected'}</p>
            `;
            if (ownerFields.length) {
                html += `<p><strong>Owner Fields Detected:</strong> ${ownerFields.join(', ')}</p>`;
            }
            if (lineIdFields.length) {
                html += `<p><strong>Identifier Fields Detected:</strong> ${lineIdFields.join(', ')}</p>`;
            }
            if (recommendedFields.length) {
                html += `<p><strong>Suggested Metadata:</strong> ${recommendedFields.join(', ')}</p>`;
            }
            html += `<h6 class="mt-3">🔍 Sample Extractions (first ${escapeHtml(String(result.preview_count))}):</h6>`;
            result.previews.forEach((preview, index) => {
                const nameLabel = escapeHtml(preview.name || 'Unknown');
                const ownerLabel = preview.owner ? escapeHtml(preview.owner) : 'Unknown';
                const descriptionLabel = preview.description ? escapeHtml(preview.description) : 'No description';
                const classificationLabel = preview.classification ? escapeHtml(preview.classification) : '';
                const mtfccLabel = preview.mtfcc ? escapeHtml(preview.mtfcc) : '';
                const lengthLabel = preview.length_label ? escapeHtml(preview.length_label) : '';
                const lineIdLabel = preview.line_id ? escapeHtml(preview.line_id) : '';
                html += `
                    <div class="preview-item">
                        <strong>Feature ${index + 1}:</strong><br>
                        <strong>📝 Name:</strong> ${nameLabel}<br>
                        <strong>👤 Owner:</strong> ${ownerLabel}<br>
                        <strong>📄 Description:</strong> ${descriptionLabel}<br>
                `;
                if (classificationLabel || mtfccLabel) {
                    const classificationText = classificationLabel
                        ? (mtfccLabel ? `${classificationLabel} (${mtfccLabel})` : classificationLabel)
                        : mtfccLabel;
                    html += `<strong>🏷 Classification:</strong> ${classificationText}<br>`;
                }
                if (lengthLabel) {
                    html += `<strong>📏 Length:</strong> ${lengthLabel}<br>`;
                }
                if (lineIdLabel) {
                    html += `<strong>🆔 Identifier:</strong> ${lineIdLabel}<br>`;
                }
                if (Array.isArray(preview.additional_details) && preview.additional_details.length) {
                    html += '<ul class="mb-0 mt-1">';
                    preview.additional_details.forEach(detail => {
                        html += `<li>${escapeHtml(detail)}</li>`;
                    });
                    html += '</ul>';
                }
                html += '</div>';
            });
            if (result.field_mappings && Object.keys(result.field_mappings).length > 0) {
                const nameFields = result.field_mappings.name_fields || [];
                const descriptionFields = result.field_mappings.description_fields || [];
                html += `
                    <h6 class="mt-3">🗺️ Field Mappings for ${escapeHtml(result.boundary_type || 'Unknown')}:</h6>
                    <p><strong>Name Fields:</strong> ${nameFields.length ? nameFields.map(escapeHtml).join(', ') : 'None configured'}</p>
                    <p><strong>Description Fields:</strong> ${descriptionFields.length ? descriptionFields.map(escapeHtml).join(', ') : 'None configured'}</p>
                `;
            }
            html += '</div>';
            resultsDiv.innerHTML = html;
        } else {
            resultsDiv.innerHTML = `<div class="alert alert-danger">❌ ${result.error}</div>`;
        }
    } catch (error) {
        resultsDiv.innerHTML = `<div class="alert alert-danger">❌ Error: ${error.message}</div>`;
    }
}

// Set loading state for boundaries
function setBoundaryLoadingState() {
    const listDiv = document.getElementById('boundariesList');
    if (listDiv) {
        listDiv.innerHTML = `
            <div class="text-center py-4">
                <div class="loading-spinner"></div>
                <span class="ms-2">Refreshing boundaries...</span>
            </div>
        `;
    }
}

// Update boundary statistics display
function updateBoundaryStats() {
    const totalEl = document.getElementById('boundaryTotalCount');
    const typeEl = document.getElementById('boundaryTypeCount');
    const updatedEl = document.getElementById('boundaryLastUpdated');
    if (totalEl) {
        totalEl.textContent = boundaryCache.stats.total.toLocaleString();
    }
    if (typeEl) {
        typeEl.textContent = boundaryCache.stats.types.toLocaleString();
    }
    if (updatedEl) {
        updatedEl.textContent = boundaryCache.lastLoaded
            ? `Last refreshed: ${boundaryCache.lastLoaded.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
            : 'Last refreshed: --';
    }
}

// Render boundaries list with filters
function renderBoundariesList() {
    const listDiv = document.getElementById('boundariesList');
    if (!listDiv) {
        return;
    }
    const searchTerm = (document.getElementById('boundarySearchInput')?.value || '').toLowerCase().trim();
    const selectedType = sanitizeBoundaryTypeInput((document.getElementById('boundaryFilterSelect')?.value || '').trim());
    const groups = boundaryCache.grouped || {};
    const entries = Object.entries(groups).sort((a, b) => {
        const labelA = (a[1]?.label || formatBoundaryLabel(a[0] || '')).toLowerCase();
        const labelB = (b[1]?.label || formatBoundaryLabel(b[0] || '')).toLowerCase();
        return labelA.localeCompare(labelB);
    });
    if (!entries.length) {
        listDiv.innerHTML = `
            <div class="boundary-empty-state">
                <i class="fas fa-map-marked-alt mb-2"></i>
                <h6 class="fw-bold">No boundary data found</h6>
                <p class="mb-2">Upload GeoJSON, then refresh to see organized cards by type.</p>
                <div class="small text-muted">Preview uploads first to validate metadata.</div>
            </div>
        `;
        return;
    }
    let html = '<div class="row g-3">';
    let hasResults = false;
    entries.forEach(([typeKey, group]) => {
        const boundaries = Array.isArray(group.items) ? group.items : [];
        const displayLabel = group.label || formatBoundaryLabel(typeKey);
        const filtered = boundaries.filter(boundary => {
            const boundaryType = sanitizeBoundaryTypeInput(boundary.canonical_type || boundary.type || boundary.raw_type || typeKey);
            if (selectedType && boundaryType !== selectedType) {
                return false;
            }
            if (!searchTerm) {
                return true;
            }
            const name = (boundary.name || '').toLowerCase();
            const description = (boundary.description || '').toLowerCase();
            const owner = (boundary.owner || '').toLowerCase();
            return name.includes(searchTerm) || description.includes(searchTerm) || owner.includes(searchTerm);
        });
        if (!filtered.length) {
            return;
        }
        hasResults = true;
        html += `
            <div class="col-md-6 col-xl-4">
                <div class="card shadow-sm h-100 border-0 manage-card">
                    <div class="card-body d-flex flex-column gap-2">
                        <div class="d-flex justify-content-between align-items-start gap-2">
                            <div>
                                <h6 class="mb-0">${escapeHtml(displayLabel)}</h6>
                                <small class="text-muted">${filtered.length} entr${filtered.length === 1 ? 'y' : 'ies'}</small>
                            </div>
                            <span class="badge bg-primary-subtle text-primary">${boundaries.length} total</span>
                        </div>
                        <div class="d-flex flex-column gap-2 boundary-scroll">
        `;
        filtered.slice(0, 12).forEach(boundary => {
            const safeName = escapeHtml(boundary.name || 'Unnamed boundary');
            const safeDesc = escapeHtml(boundary.description || boundary.owner || 'No description');
            html += `
                <div class="boundary-chip d-flex justify-content-between align-items-start gap-2">
                    <div class="flex-grow-1">
                        <div class="fw-semibold text-truncate" title="${safeName}">${safeName}</div>
                        <div class="text-muted small text-truncate" title="${safeDesc}">${safeDesc}</div>
                    </div>
                    <button onclick="deleteBoundary(${boundary.id}, '${(boundary.name || 'this boundary').replace(/'/g, "\\'")}')" class="btn btn-outline-danger btn-sm" title="Delete boundary">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
        });
        if (filtered.length > 12) {
            html += `<small class="text-muted">…and ${filtered.length - 12} more matches</small>`;
        }
        html += `
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    html += '</div>';
    listDiv.innerHTML = hasResults ? html : `
        <div class="boundary-empty-state">
            <i class="fas fa-search mb-2"></i>
            <h6 class="fw-bold">No boundaries match your filters</h6>
            <p class="mb-0">Try clearing the search or choosing a different type.</p>
        </div>
    `;
}

// Load boundaries from API
async function loadBoundaries() {
    try {
        setBoundaryLoadingState();
        const response = await fetch('/api/boundaries');
        const data = await response.json();
        if (data.features && data.features.length > 0) {
            const boundariesByType = {};
            data.features.forEach(feature => {
                const props = feature.properties || {};
                const typeKey = sanitizeBoundaryTypeInput(props.canonical_type || props.type || props.raw_type || 'unknown');
                const displayLabel = props.display_type || formatBoundaryLabel(typeKey);
                if (!boundariesByType[typeKey]) {
                    boundariesByType[typeKey] = {
                        label: displayLabel,
                        items: []
                    };
                }
                boundariesByType[typeKey].items.push(props);
            });
            const dynamicTypes = Object.entries(boundariesByType).map(([key, group]) => ({
                key,
                label: group.label || formatBoundaryLabel(key)
            }));
            ensureDynamicBoundaryOptions(dynamicTypes);
            boundaryCache = {
                features: data.features,
                grouped: boundariesByType,
                stats: {
                    total: data.features.length,
                    types: Object.keys(boundariesByType).length
                },
                lastLoaded: new Date()
            };
            updateBoundaryStats();
            renderBoundariesList();
        } else {
            boundaryCache = {
                features: [],
                grouped: {},
                stats: { total: 0, types: 0 },
                lastLoaded: new Date()
            };
            updateBoundaryStats();
            renderBoundariesList();
            const listDiv = document.getElementById('boundariesList');
            if (listDiv) {
                listDiv.innerHTML = `
                    <div class="boundary-empty-state">
                        <i class="fas fa-cloud-upload-alt mb-2"></i>
                        <h6 class="fw-bold">No boundaries found</h6>
                        <p class="mb-0">Upload GeoJSON files to start managing your boundary data.</p>
                    </div>
                `;
            }
        }
        initializeCustomTypeControls();
    } catch (error) {
        document.getElementById('boundariesList').innerHTML = `<div class="alert alert-danger">Error loading boundaries: ${error.message}</div>`;
    }
}

// Delete a single boundary
async function deleteBoundary(boundaryId, boundaryName) {
    showConfirmation({
        title: 'Delete Boundary',
        message: `Delete boundary "${boundaryName}"?`,
        warning: 'This will remove the boundary from all maps and alerts.',
        type: 'warning',
        confirmText: 'Delete',
        onConfirm: async () => {
            try {
                const response = await fetch(`/admin/delete_boundary/${boundaryId}`, { method: 'DELETE' });
                const result = await response.json();
                if (response.ok) {
                    showStatus(`✅ ${result.success}`, 'success');
                    loadBoundaries();
                } else {
                    showStatus(`❌ ${result.error}`, 'danger');
                }
            } catch (error) {
                showStatus(`❌ Error: ${error.message}`, 'danger');
            }
        }
    });
}

// Delete all boundaries of a specific type
async function deleteBoundariesByType() {
    let selection;
    try {
        selection = getSelectedBoundaryType('deleteType', 'customDeleteBoundaryType');
    } catch (error) {
        showStatus(error.message, 'warning');
        return;
    }
    if (!selection.type) {
        showStatus('Please select a boundary type to delete', 'warning');
        return;
    }
    const displayLabel = selection.label || formatBoundaryLabel(selection.type);
    showConfirmation({
        title: 'Delete Boundary Type',
        message: `Delete all ${escapeHtml(displayLabel)} boundaries?`,
        warning: 'This action cannot be undone.',
        type: 'danger',
        confirmText: 'Delete',
        onConfirm: async () => {
            try {
                const response = await fetch(`/admin/clear_boundaries/${encodeURIComponent(selection.type)}`, {
                    method: 'DELETE'
                });
                const result = await response.json();
                if (response.ok) {
                    showStatus(`✅ ${result.success}`, 'success');
                    const select = document.getElementById('deleteType');
                    if (select) {
                        select.value = '';
                    }
                    const customInput = document.getElementById('customDeleteBoundaryType');
                    if (customInput) {
                        customInput.value = '';
                    }
                    initializeCustomTypeControls();
                    await loadBoundaries();
                } else {
                    showStatus(`❌ ${result.error}`, 'danger');
                }
            } catch (error) {
                showStatus(`❌ ${error.message}`, 'danger');
            }
        }
    });
}

// Clear all boundaries with multi-step confirmation
async function clearAllBoundaries() {
    const steps = [
        {
            message: '⚠️ WARNING: This will permanently delete ALL boundaries from the system.',
            warning: 'This will affect all alerts and intersections. This action cannot be undone.'
        },
        {
            message: '🚨 FINAL WARNING: You are about to permanently delete all boundaries.',
            warning: 'Type "DELETE ALL BOUNDARIES" to confirm this irreversible action.',
            textConfirmation: 'DELETE ALL BOUNDARIES'
        }
    ];
    showMultiStepConfirmation({
        steps: steps,
        onComplete: async () => {
            try {
                const response = await fetch('/admin/clear_all_boundaries', {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        confirmation_level: 2,
                        text_confirmation: 'DELETE ALL BOUNDARIES'
                    })
                });
                const result = await response.json();
                if (response.ok) {
                    showStatus(`✅ ${result.success}`, 'success');
                    loadBoundaries();
                } else {
                    showStatus(`❌ ${result.error}`, 'danger');
                }
            } catch (error) {
                showStatus(`❌ Error: ${error.message}`, 'danger');
            }
        }
    });
}

// Export functions to window object for use in other modules and inline code
window.formatBoundaryLabel = formatBoundaryLabel;
window.initializeCustomTypeControls = initializeCustomTypeControls;
window.getSelectedBoundaryType = getSelectedBoundaryType;
window.addOptionIfMissing = addOptionIfMissing;
window.ensureDynamicBoundaryOptions = ensureDynamicBoundaryOptions;
window.loadServerShapefiles = loadServerShapefiles;
window.convertServerShapefile = convertServerShapefile;
window.showShapefileStatus = showShapefileStatus;
window.previewExtraction = previewExtraction;
window.setBoundaryLoadingState = setBoundaryLoadingState;
window.updateBoundaryStats = updateBoundaryStats;
window.renderBoundariesList = renderBoundariesList;
window.loadBoundaries = loadBoundaries;
window.deleteBoundary = deleteBoundary;
window.deleteBoundariesByType = deleteBoundariesByType;
window.clearAllBoundaries = clearAllBoundaries;

// Initialize boundary management event listeners on DOM load
document.addEventListener('DOMContentLoaded', function() {
    if (typeof ADMIN_SETUP_MODE !== 'undefined' && ADMIN_SETUP_MODE) {
        return;
    }

    // Setup boundary search and filter event listeners
    const searchInput = document.getElementById('boundarySearchInput');
    const filterSelect = document.getElementById('boundaryFilterSelect');
    const refreshButton = document.getElementById('refreshBoundariesBtn');
    
    if (searchInput) {
        searchInput.addEventListener('input', renderBoundariesList);
    }
    if (filterSelect) {
        filterSelect.addEventListener('change', renderBoundariesList);
    }
    if (refreshButton) {
        refreshButton.addEventListener('click', () => {
            setBoundaryLoadingState();
            loadBoundaries();
        });
    }

    // Load boundaries on page load
    loadBoundaries();
});
