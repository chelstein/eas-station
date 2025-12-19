/**
 * Admin Panel - Location Settings Module
 * Handles location settings form submission, FIPS code selection, and zone code management
 */

/**
 * Parse newline-separated values into an array
 * @param {string} value - Raw textarea value
 * @returns {string[]} - Array of non-empty trimmed values
 */
function parseNewlineValues(value) {
    if (!value || typeof value !== 'string') {
        return [];
    }
    return value
        .split(/[\r\n]+/)
        .map(line => line.trim().toUpperCase())
        .filter(line => line.length > 0);
}

/**
 * Initialize location settings form handlers
 */
function initLocationSettings() {
    const form = document.getElementById('locationSettingsForm');
    if (!form) {
        return;
    }

    // Initialize FIPS state dropdown
    initFipsStateDropdown();

    // Initialize FIPS county dropdown event handlers
    initFipsCountyDropdown();

    // Initialize add FIPS button
    initAddFipsButton();

    // Initialize location reference refresh button
    initLocationReferenceRefresh();

    // Initialize reset button
    initResetButton();

    // Form submission handler
    form.addEventListener('submit', handleLocationSettingsSubmit);

    // Load initial FIPS codes from hidden input
    loadInitialFipsCodes();

    // Load location reference data
    loadLocationReference();
}

/**
 * Handle location settings form submission
 * @param {Event} e - Submit event
 */
async function handleLocationSettingsSubmit(e) {
    e.preventDefault();

    const form = e.target;
    const statusEl = document.getElementById('locationSettingsStatus');
    const submitBtn = form.querySelector('button[type="submit"]');

    // Disable submit button during request
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    }

    if (statusEl) {
        statusEl.textContent = 'Saving...';
        statusEl.className = 'text-muted small ms-3';
    }

    // Collect form data
    const countyName = document.getElementById('locationCountyName')?.value?.trim() || '';
    const stateCode = document.getElementById('locationStateCode')?.value?.trim().toUpperCase() || '';
    const timezone = document.getElementById('locationTimezone')?.value?.trim() || '';
    const fipsCodesHidden = document.getElementById('locationFipsCodes')?.value || '';
    const zoneCodesText = document.getElementById('locationZoneCodes')?.value || '';
    const storageZoneCodesText = document.getElementById('locationStorageZoneCodes')?.value || '';
    const mapCenterLat = parseFloat(document.getElementById('locationMapLat')?.value) || 0;
    const mapCenterLng = parseFloat(document.getElementById('locationMapLng')?.value) || 0;
    const mapDefaultZoom = parseInt(document.getElementById('locationMapZoom')?.value, 10) || 9;

    // Parse FIPS codes from hidden input (comma-separated)
    const fipsCodes = fipsCodesHidden
        .split(',')
        .map(code => code.trim())
        .filter(code => code.length > 0);

    // Parse zone codes from textareas (newline-separated)
    const zoneCodes = parseNewlineValues(zoneCodesText);
    const storageZoneCodes = parseNewlineValues(storageZoneCodesText);

    const payload = {
        county_name: countyName,
        state_code: stateCode,
        timezone: timezone,
        fips_codes: fipsCodes,
        zone_codes: zoneCodes,
        storage_zone_codes: storageZoneCodes,
        map_center_lat: mapCenterLat,
        map_center_lng: mapCenterLng,
        map_default_zoom: mapDefaultZoom
    };

    try {
        const response = await fetch('/admin/location_settings', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': window.CSRF_TOKEN || ''
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (response.ok && result.success) {
            if (statusEl) {
                statusEl.textContent = '✓ Location settings saved successfully';
                statusEl.className = 'text-success small ms-3';
            }
            if (typeof showToast === 'function') {
                showToast('Location settings saved successfully', 'success');
            }
            // Reload location reference after save
            loadLocationReference();
            // Update cache
            if (result.settings) {
                window.locationSettingsCache = result.settings;
            }
        } else {
            const errorMsg = result.error || 'Failed to save location settings';
            if (statusEl) {
                statusEl.textContent = '✗ ' + errorMsg;
                statusEl.className = 'text-danger small ms-3';
            }
            if (typeof showToast === 'function') {
                showToast(errorMsg, 'danger');
            }
        }
    } catch (error) {
        console.error('Error saving location settings:', error);
        if (statusEl) {
            statusEl.textContent = '✗ Network error: ' + error.message;
            statusEl.className = 'text-danger small ms-3';
        }
        if (typeof showToast === 'function') {
            showToast('Network error: ' + error.message, 'danger');
        }
    } finally {
        // Re-enable submit button
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-save"></i> Save Location Settings';
        }
    }
}

/**
 * Initialize FIPS state dropdown with states from EAS_FIPS_TREE
 */
function initFipsStateDropdown() {
    const stateSelect = document.getElementById('locationFipsState');
    if (!stateSelect) {
        return;
    }

    // Clear existing options except the first placeholder
    while (stateSelect.options.length > 1) {
        stateSelect.remove(1);
    }

    // Add state options from EAS_FIPS_TREE
    const states = window.EAS_FIPS_TREE || [];
    states.forEach(state => {
        if (!state || !state.abbr || !state.name) {
            return;
        }
        const option = document.createElement('option');
        option.value = state.abbr;
        option.textContent = `${state.name} (${state.abbr})`;
        stateSelect.appendChild(option);
    });

    // Handle state selection change
    stateSelect.addEventListener('change', function() {
        populateCountyDropdown(this.value);
    });
}

/**
 * Initialize FIPS county dropdown event handlers
 */
function initFipsCountyDropdown() {
    const countySelect = document.getElementById('locationFipsCounty');
    if (!countySelect) {
        return;
    }
    // Enable/disable based on state selection is handled in populateCountyDropdown
}

/**
 * Populate county dropdown based on selected state
 * @param {string} stateAbbr - State abbreviation
 */
function populateCountyDropdown(stateAbbr) {
    const countySelect = document.getElementById('locationFipsCounty');
    if (!countySelect) {
        return;
    }

    // Clear existing options
    countySelect.innerHTML = '';

    if (!stateAbbr) {
        countySelect.innerHTML = '<option value="">Select a state first…</option>';
        countySelect.disabled = true;
        return;
    }

    // Find state data
    const states = window.EAS_FIPS_TREE || [];
    const stateData = states.find(s => s && s.abbr === stateAbbr);

    if (!stateData || !stateData.counties || stateData.counties.length === 0) {
        countySelect.innerHTML = '<option value="">No counties found</option>';
        countySelect.disabled = true;
        return;
    }

    // Add placeholder option
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = 'Select a county…';
    countySelect.appendChild(placeholder);

    // Add county options
    stateData.counties.forEach(county => {
        if (!county || !county.same || !county.name) {
            return;
        }
        const option = document.createElement('option');
        option.value = county.same;
        option.textContent = `${county.name} (${county.same})`;
        countySelect.appendChild(option);
    });

    countySelect.disabled = false;
}

/**
 * Initialize add FIPS button handler
 */
function initAddFipsButton() {
    const addBtn = document.getElementById('locationAddFipsBtn');
    if (!addBtn) {
        return;
    }

    addBtn.addEventListener('click', function() {
        const countySelect = document.getElementById('locationFipsCounty');
        const selectedCode = countySelect?.value;
        const selectedText = countySelect?.options[countySelect.selectedIndex]?.textContent;

        if (!selectedCode) {
            if (typeof showToast === 'function') {
                showToast('Please select a county to add', 'warning');
            }
            return;
        }

        addFipsCode(selectedCode, selectedText);

        // Reset the county dropdown to placeholder
        if (countySelect) {
            countySelect.value = '';
        }
    });
}

/**
 * Add a FIPS code to the selection
 * @param {string} code - FIPS code
 * @param {string} label - Display label
 */
function addFipsCode(code, label) {
    // Check for duplicates
    if (window.locationFipsSelection.some(item => item.code === code)) {
        if (typeof showToast === 'function') {
            showToast('This county is already selected', 'warning');
        }
        return;
    }

    // Check max limit
    const maxCodes = window.LOCATION_FIPS_MAX || 31;
    if (window.locationFipsSelection.length >= maxCodes) {
        if (typeof showToast === 'function') {
            showToast(`Maximum of ${maxCodes} FIPS codes allowed`, 'warning');
        }
        return;
    }

    // Add to selection
    window.locationFipsSelection.push({ code, label });

    // Update UI and hidden input
    renderFipsSelection();
    updateFipsHiddenInput();
}

/**
 * Remove a FIPS code from the selection
 * @param {string} code - FIPS code to remove
 */
function removeFipsCode(code) {
    window.locationFipsSelection = window.locationFipsSelection.filter(item => item.code !== code);
    renderFipsSelection();
    updateFipsHiddenInput();
}

/**
 * Render the FIPS selection chips
 */
function renderFipsSelection() {
    const container = document.getElementById('locationSelectedFips');
    if (!container) {
        return;
    }

    if (window.locationFipsSelection.length === 0) {
        container.innerHTML = '<p class="text-muted small mb-0">No SAME / FIPS counties selected yet.</p>';
        return;
    }

    let html = '<div class="d-flex flex-wrap gap-2">';
    window.locationFipsSelection.forEach(item => {
        const lookup = window.EAS_FIPS_LOOKUP || {};
        const countyName = lookup[item.code] || item.label || item.code;
        html += `
            <span class="badge bg-primary d-flex align-items-center gap-2">
                <code>${item.code}</code>
                <span>${countyName}</span>
                <button type="button" class="btn-close btn-close-white" style="font-size: 0.6em;" onclick="removeFipsCode('${item.code}')" title="Remove"></button>
            </span>
        `;
    });
    html += '</div>';
    container.innerHTML = html;
}

/**
 * Update the hidden FIPS codes input
 */
function updateFipsHiddenInput() {
    const hiddenInput = document.getElementById('locationFipsCodes');
    if (hiddenInput) {
        hiddenInput.value = window.locationFipsSelection.map(item => item.code).join(',');
    }
}

/**
 * Load initial FIPS codes from the settings
 */
function loadInitialFipsCodes() {
    // Initialize the selection array if not exists
    if (!window.locationFipsSelection) {
        window.locationFipsSelection = [];
    }

    const hiddenInput = document.getElementById('locationFipsCodes');
    if (!hiddenInput || !hiddenInput.value) {
        // Try to load from cache
        const cache = window.locationSettingsCache || window.APP_LOCATION;
        if (cache && cache.fips_codes && Array.isArray(cache.fips_codes)) {
            const lookup = window.EAS_FIPS_LOOKUP || {};
            cache.fips_codes.forEach(code => {
                if (code) {
                    window.locationFipsSelection.push({
                        code: code,
                        label: lookup[code] || code
                    });
                }
            });
            renderFipsSelection();
            updateFipsHiddenInput();
        }
        return;
    }

    // Parse existing value
    const codes = hiddenInput.value.split(',').map(c => c.trim()).filter(c => c);
    const lookup = window.EAS_FIPS_LOOKUP || {};

    codes.forEach(code => {
        window.locationFipsSelection.push({
            code: code,
            label: lookup[code] || code
        });
    });

    renderFipsSelection();
}

/**
 * Initialize location reference refresh button
 */
function initLocationReferenceRefresh() {
    const refreshBtn = document.getElementById('refreshLocationReference');
    if (!refreshBtn) {
        return;
    }

    refreshBtn.addEventListener('click', function() {
        loadLocationReference(true);
    });
}

/**
 * Load location reference data from API
 * @param {boolean} showMessage - Whether to show a status message
 */
async function loadLocationReference(showMessage = false) {
    const statusEl = document.getElementById('locationReferenceStatus');
    const contentEl = document.getElementById('locationReferenceContent');

    if (statusEl && showMessage) {
        statusEl.textContent = 'Loading...';
    }

    try {
        const response = await fetch('/admin/location_reference', {
            headers: {
                'X-CSRF-Token': window.CSRF_TOKEN || ''
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        window.locationReferenceCache = data;

        if (contentEl) {
            renderLocationReference(data, contentEl);
        }

        if (statusEl) {
            statusEl.textContent = showMessage ? '✓ Reference data refreshed' : '';
        }
    } catch (error) {
        console.error('Error loading location reference:', error);
        if (statusEl) {
            statusEl.textContent = '✗ Failed to load reference data';
        }
        if (contentEl) {
            contentEl.innerHTML = '<p class="text-danger small mb-0">Failed to load location reference data.</p>';
        }
    }
}

/**
 * Render location reference data
 * @param {Object} data - Reference data from API
 * @param {HTMLElement} container - Container element
 */
function renderLocationReference(data, container) {
    if (!data) {
        container.innerHTML = '<p class="text-muted small mb-0">No reference data available.</p>';
        return;
    }

    let html = '<div class="row g-3">';

    // Location summary
    if (data.location) {
        html += `
            <div class="col-12">
                <div class="d-flex flex-wrap gap-3">
                    <span class="badge bg-secondary">
                        <i class="fas fa-map-marker-alt me-1"></i>
                        ${escapeHtml(data.location.county_name || 'Unknown')}, ${escapeHtml(data.location.state_code || '??')}
                    </span>
                    <span class="badge bg-info">
                        <i class="fas fa-clock me-1"></i>
                        ${escapeHtml(data.location.timezone || 'Unknown timezone')}
                    </span>
                </div>
            </div>
        `;
    }

    // FIPS codes summary
    if (data.fips) {
        const knownCount = data.fips.known?.length || 0;
        const missingCount = data.fips.missing?.length || 0;
        html += `
            <div class="col-md-6">
                <h6 class="fw-bold small mb-2">
                    <i class="fas fa-hashtag text-primary me-1"></i>
                    SAME / FIPS Codes (${knownCount} configured)
                </h6>
        `;
        if (knownCount > 0) {
            html += '<div class="d-flex flex-wrap gap-1">';
            data.fips.known.forEach(item => {
                const badge = item.is_statewide ? 'bg-warning text-dark' : 'bg-light text-dark border';
                html += `<span class="badge ${badge}" title="${escapeHtml(item.label || '')}">${escapeHtml(item.code)}</span>`;
            });
            html += '</div>';
        }
        if (missingCount > 0) {
            html += `<p class="text-warning small mt-2 mb-0"><i class="fas fa-exclamation-triangle me-1"></i> ${missingCount} code(s) not found in catalog</p>`;
        }
        html += '</div>';
    }

    // Zone codes summary
    if (data.zones) {
        const knownCount = data.zones.known?.length || 0;
        const missingCount = data.zones.missing?.length || 0;
        html += `
            <div class="col-md-6">
                <h6 class="fw-bold small mb-2">
                    <i class="fas fa-map me-1 text-success"></i>
                    NOAA Zone Codes (${knownCount} configured)
                </h6>
        `;
        if (knownCount > 0) {
            html += '<div class="d-flex flex-wrap gap-1">';
            data.zones.known.slice(0, 20).forEach(item => {
                const typeClass = item.zone_type === 'Z' ? 'bg-success' : 'bg-info';
                html += `<span class="badge ${typeClass}" title="${escapeHtml(item.label || '')}">${escapeHtml(item.code)}</span>`;
            });
            if (knownCount > 20) {
                html += `<span class="badge bg-secondary">+${knownCount - 20} more</span>`;
            }
            html += '</div>';
        }
        if (missingCount > 0) {
            html += `<p class="text-warning small mt-2 mb-0"><i class="fas fa-exclamation-triangle me-1"></i> ${missingCount} code(s) not found in zone catalog</p>`;
        }
        html += '</div>';
    }

    html += '</div>';
    container.innerHTML = html;
}

/**
 * Initialize reset button handler
 */
function initResetButton() {
    const resetBtn = document.getElementById('resetLocationSettings');
    if (!resetBtn) {
        return;
    }

    resetBtn.addEventListener('click', function() {
        const cache = window.locationSettingsCache || window.APP_LOCATION;
        if (!cache) {
            if (typeof showToast === 'function') {
                showToast('No cached settings to restore', 'warning');
            }
            return;
        }

        // Reset form fields
        const countyNameInput = document.getElementById('locationCountyName');
        const stateCodeInput = document.getElementById('locationStateCode');
        const timezoneInput = document.getElementById('locationTimezone');
        const zoneCodesTextarea = document.getElementById('locationZoneCodes');
        const storageZoneCodesTextarea = document.getElementById('locationStorageZoneCodes');
        const mapLatInput = document.getElementById('locationMapLat');
        const mapLngInput = document.getElementById('locationMapLng');
        const mapZoomInput = document.getElementById('locationMapZoom');

        if (countyNameInput) countyNameInput.value = cache.county_name || '';
        if (stateCodeInput) stateCodeInput.value = cache.state_code || '';
        if (timezoneInput) timezoneInput.value = cache.timezone || 'America/New_York';
        if (zoneCodesTextarea) zoneCodesTextarea.value = (cache.zone_codes || []).join('\n');
        if (storageZoneCodesTextarea) storageZoneCodesTextarea.value = (cache.storage_zone_codes || []).join('\n');
        if (mapLatInput) mapLatInput.value = cache.map_center_lat || 0;
        if (mapLngInput) mapLngInput.value = cache.map_center_lng || 0;
        if (mapZoomInput) mapZoomInput.value = cache.map_default_zoom || 9;

        // Reset FIPS selection
        window.locationFipsSelection = [];
        const lookup = window.EAS_FIPS_LOOKUP || {};
        if (cache.fips_codes && Array.isArray(cache.fips_codes)) {
            cache.fips_codes.forEach(code => {
                if (code) {
                    window.locationFipsSelection.push({
                        code: code,
                        label: lookup[code] || code
                    });
                }
            });
        }
        renderFipsSelection();
        updateFipsHiddenInput();

        // Clear status
        const statusEl = document.getElementById('locationSettingsStatus');
        if (statusEl) {
            statusEl.textContent = '';
        }

        if (typeof showToast === 'function') {
            showToast('Form reset to saved values', 'info');
        }
    });
}

/**
 * Escape HTML special characters
 * @param {string} str - String to escape
 * @returns {string} - Escaped string
 */
function escapeHtml(str) {
    if (!str || typeof str !== 'string') {
        return '';
    }
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Export functions to window for global access
window.handleLocationSettingsSubmit = handleLocationSettingsSubmit;
window.addFipsCode = addFipsCode;
window.removeFipsCode = removeFipsCode;
window.loadLocationReference = loadLocationReference;
window.initLocationSettings = initLocationSettings;

// Initialize on DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if not in setup mode
    if (typeof ADMIN_SETUP_MODE !== 'undefined' && ADMIN_SETUP_MODE) {
        return;
    }
    initLocationSettings();
});
