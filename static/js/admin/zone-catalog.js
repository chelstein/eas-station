/**
 * Zone Catalog Management Module
 * Handles zone catalog upload, search, and information display
 * 
 * Dependencies: showToast(), escapeHtmlAdmin() from core or global scope
 */

// ==================== Zone Catalog Management ====================

// Load zone info when zone catalog sub-tab is shown
const zoneTab = document.getElementById('zones-subtab');
if (zoneTab) {
    zoneTab.addEventListener('shown.bs.tab', function() {
        refreshZoneInfo();
    });
}

// Upload form handler
const zoneUploadForm = document.getElementById('zone-upload-form');
if (zoneUploadForm) {
    zoneUploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const fileInput = document.getElementById('zone-file-input');
        
        if (!fileInput.files.length) {
            showToast('Please select a file', 'warning');
            return;
        }
        
        try {
            const response = await fetch('/admin/zones/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                showToast(data.message, 'success');
                e.target.reset();
                refreshZoneInfo();
            } else {
                showToast(data.error || 'Upload failed', 'danger');
            }
        } catch (error) {
            console.error('Zone upload error:', error);
            showToast('Error uploading file', 'danger');
        }
    });
}

// Reload button handler
const zoneReloadBtn = document.getElementById('zone-reload-btn');
if (zoneReloadBtn) {
    zoneReloadBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/admin/zones/reload', {
                method: 'POST'
            });
            const data = await response.json();
            
            if (response.ok && data.success) {
                showToast(data.message, 'success');
                refreshZoneInfo();
            } else {
                showToast(data.error || 'Reload failed', 'danger');
            }
        } catch (error) {
            console.error('Zone reload error:', error);
            showToast('Error reloading zones', 'danger');
        }
    });
}

async function refreshZoneInfo() {
    try {
        const response = await fetch('/admin/zones/info');
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Update zone count displays
            const dbCountEl = document.getElementById('zone-db-count');
            if (dbCountEl) {
                dbCountEl.textContent = data.db_count || 0;
            }
            
            const cacheCountEl = document.getElementById('zone-cache-count');
            if (cacheCountEl) {
                cacheCountEl.textContent = data.cache_count || 0;
            }
            
            // Update file size
            const sizeEl = document.getElementById('zone-file-size');
            if (sizeEl) {
                if (data.file_size_mb) {
                    sizeEl.textContent = data.file_size_mb + ' MB';
                } else {
                    sizeEl.textContent = '--';
                }
            }
            
            // Enable/disable reload button
            if (zoneReloadBtn) {
                zoneReloadBtn.disabled = !data.exists;
            }
        } else {
            // Handle error response
            console.error('Zone info request failed:', response.status, data.error || data.message);
            if (data.error === 'authentication_required') {
                showToast('Please log in to continue', 'warning');
            } else if (data.error === 'permission_denied') {
                showToast('Permission denied: ' + (data.message || 'admin.settings required'), 'danger');
            } else {
                showToast('Failed to load zone info: ' + (data.error || 'Unknown error'), 'danger');
            }
        }
    } catch (error) {
        console.error('Error refreshing zone info:', error);
        showToast('Error loading zone information. Check console for details.', 'danger');
    }
}

// Zone search with debouncing
let zoneSearchTimeout;
const zoneSearchInput = document.getElementById('zone-search-input');
if (zoneSearchInput) {
    zoneSearchInput.addEventListener('input', (e) => {
        clearTimeout(zoneSearchTimeout);
        const query = e.target.value.trim();
        
        if (query.length < 2) {
            document.getElementById('zone-search-results').innerHTML = '<p class="text-muted">Enter at least 2 characters to search</p>';
            return;
        }
        
        zoneSearchTimeout = setTimeout(() => searchZones(query), 300);
    });
}

async function searchZones(query) {
    const resultsDiv = document.getElementById('zone-search-results');
    if (!resultsDiv) return;
    
    resultsDiv.innerHTML = '<p class="text-muted"><i class="fas fa-spinner fa-spin"></i> Searching...</p>';
    
    try {
        const response = await fetch(`/admin/zones/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (response.ok && data.zones) {
            if (data.zones.length === 0) {
                resultsDiv.innerHTML = '<p class="text-muted">No zones found</p>';
            } else {
                let html = '<div class="list-group">';
                data.zones.forEach(zone => {
                    html += `
                        <div class="list-group-item">
                            <div class="d-flex w-100 justify-content-between">
                                <h6 class="mb-1"><span class="badge bg-primary">${zone.zone_code}</span> ${zone.name}, ${zone.state_code}</h6>
                            </div>
                            <small class="text-muted">
                                CWA: ${zone.cwa || 'N/A'} | 
                                Timezone: ${zone.time_zone || 'N/A'} | 
                                Coords: ${zone.latitude ? zone.latitude.toFixed(4) : 'N/A'}, ${zone.longitude ? zone.longitude.toFixed(4) : 'N/A'}
                            </small>
                        </div>
                    `;
                });
                html += '</div>';
                resultsDiv.innerHTML = html;
            }
        } else {
            resultsDiv.innerHTML = '<p class="text-danger">Error loading results</p>';
        }
    } catch (error) {
        resultsDiv.innerHTML = '<p class="text-danger">Error: ' + escapeHtmlAdmin(error.message) + '</p>';
    }
}

// ==================== End Zone Catalog Management ====================
