/**
 * Admin Panel - Hardware Settings Module
 * Handles LED sign configuration, GPIO controls, and hardware diagnostics
 */

/**
 * Save LED adapter configuration
 */
async function saveLedAdapterConfig() {
    const serialMode = document.getElementById('ledSerialMode')?.value || 'RS232';
    const baudRate = parseInt(document.getElementById('ledBaudRate')?.value || '9600');

    try {
        const response = await fetch('/api/led/serial_config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                serial_mode: serialMode,
                baud_rate: baudRate
            })
        });

        const result = await response.json();
        if (!response.ok || !result.success) {
            console.warn('LED adapter config save failed:', result.error);
        }
    } catch (error) {
        console.warn('Failed to save LED adapter configuration:', error);
    }
}

/**
 * Load LED adapter configuration
 */
async function loadLedAdapterConfig() {
    try {
        const response = await fetch('/api/led/serial_config');
        const result = await response.json();

        if (result.success && result.config) {
            const serialModeSelect = document.getElementById('ledSerialMode');
            const baudRateSelect = document.getElementById('ledBaudRate');

            if (serialModeSelect && result.config.serial_mode) {
                serialModeSelect.value = result.config.serial_mode;
            }

            if (baudRateSelect && result.config.baud_rate) {
                baudRateSelect.value = result.config.baud_rate.toString();
            }
        }
    } catch (error) {
        console.warn('Failed to load LED adapter configuration:', error);
    }
}

/**
 * Initialize hardware settings
 */
window.initializeHardwareSettings = function() {
    loadLedAdapterConfig();
    loadHardwareLedAdapterConfig();
};

/**
 * Save LED sign settings
 * @param {Event} event - Form submit event
 */
window.saveLedSignSettings = async function(event) {
    event.preventDefault();
    
    const enabledCheckbox = document.getElementById('ledSignEnabled');
    const addressInput = document.getElementById('ledSignAddress');
    
    const payload = {
        enabled: enabledCheckbox ? enabledCheckbox.checked : false,
        address: addressInput ? addressInput.value : '01'
    };

    try {
        showStatus('Saving LED sign settings...', 'info');
        const response = await fetch('/api/led/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await response.json();
        
        if (response.ok && result.success) {
            showStatus('LED sign settings saved successfully.', 'success');
            await saveLedAdapterConfig();
        } else {
            showStatus(result.error || 'Failed to save LED sign settings.', 'danger');
        }
    } catch (error) {
        console.error('Error saving LED sign settings:', error);
        showStatus('Failed to save LED sign settings.', 'danger');
    }
};

/**
 * Save hardware LED adapter configuration
 */
async function saveHardwareLedAdapterConfig() {
    const serialMode = document.getElementById('hardwareLedSerialMode')?.value || 'RS232';
    const baudRate = parseInt(document.getElementById('hardwareLedBaudRate')?.value || '9600');

    try {
        const response = await fetch('/api/led/serial_config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                serial_mode: serialMode,
                baud_rate: baudRate
            })
        });

        const result = await response.json();
        if (!response.ok || !result.success) {
            console.warn('Hardware LED adapter config save failed:', result.error);
        }
    } catch (error) {
        console.warn('Failed to save hardware LED adapter configuration:', error);
    }
}

/**
 * Load hardware LED adapter configuration
 */
async function loadHardwareLedAdapterConfig() {
    try {
        const response = await fetch('/api/led/serial_config');
        const result = await response.json();

        if (result.success && result.config) {
            const serialModeSelect = document.getElementById('hardwareLedSerialMode');
            const baudRateSelect = document.getElementById('hardwareLedBaudRate');

            if (serialModeSelect && result.config.serial_mode) {
                serialModeSelect.value = result.config.serial_mode;
            }

            if (baudRateSelect && result.config.baud_rate) {
                baudRateSelect.value = result.config.baud_rate.toString();
            }
        }
    } catch (error) {
        console.warn('Failed to load hardware LED adapter configuration:', error);
    }
}

// Export internal functions to window for testing/debugging
window.HardwareSettings = {
    saveLedAdapterConfig,
    loadLedAdapterConfig,
    saveHardwareLedAdapterConfig,
    loadHardwareLedAdapterConfig
};
