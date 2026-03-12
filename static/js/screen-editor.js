/**
 * Visual Screen Editor for OLED/VFD/LED Displays
 * Phase 1 + 2: Full WYSIWYG editor with element management
 * Supports text elements and bar graph elements.
 */

const ScreenEditor = (function() {
    'use strict';

    // Editor state
    const state = {
        displayType: 'oled',
        canvasWidth: 128,
        canvasHeight: 64,
        zoom: 1,
        elements: [],
        selectedElement: null,
        dataSources: [],
        isDragging: false,
        dragElement: null,
        dragStartX: 0,
        dragStartY: 0,
        screenId: null
    };

    // Display dimensions by type
    const DISPLAY_DIMS = {
        oled: { width: 128, height: 64 },
        vfd: { width: 140, height: 32 },
        led: { width: 80, height: 32 }  // Virtual dimensions for LED (4 lines x 20 chars)
    };

    // Font sizes (actual pixel heights)
    const FONT_SIZES = {
        small: 11,
        medium: 14,
        large: 18,
        xlarge: 28,
        huge: 36
    };

    // Bar graph element constraints and defaults
    const BAR_MIN_WIDTH = 4;
    const BAR_MIN_HEIGHT = 3;
    const BAR_DEFAULT_VALUE = '50';
    const BAR_DEFAULT_PREVIEW = 60;

    // Canvas and context
    let canvas, ctx;

    // Initialize editor
    function init() {
        canvas = document.getElementById('display-canvas');
        ctx = canvas.getContext('2d');

        // Get screen ID if editing existing
        const screenIdInput = document.getElementById('screen-id');
        if (screenIdInput && screenIdInput.value) {
            state.screenId = parseInt(screenIdInput.value);
        }

        setupEventListeners();
        updateCanvasDimensions();
        render();
    }

    // Setup all event listeners
    function setupEventListeners() {
        // Display type change
        document.getElementById('display-type').addEventListener('change', function() {
            state.displayType = this.value;
            updateCanvasDimensions();
            updateEffectsPanel();
            render();
        });

        // Add text element
        document.getElementById('btn-add-text').addEventListener('click', addTextElement);

        // Add bar graph element
        document.getElementById('btn-add-bar').addEventListener('click', addBarElement);

        // Clear canvas
        document.getElementById('btn-clear-canvas').addEventListener('click', () => {
            if (confirm('Clear all elements?')) {
                state.elements = [];
                state.selectedElement = null;
                render();
                updateLayers();
                hideElementProps();
            }
        });

        // Zoom controls
        document.getElementById('btn-zoom-in').addEventListener('click', () => changeZoom(0.25));
        document.getElementById('btn-zoom-out').addEventListener('click', () => changeZoom(-0.25));

        // Text element property changes
        document.getElementById('elem-text').addEventListener('input', updateSelectedElement);
        document.getElementById('elem-font').addEventListener('change', updateSelectedElement);
        document.getElementById('elem-x').addEventListener('input', updateSelectedElement);
        document.getElementById('elem-y').addEventListener('input', updateSelectedElement);
        document.getElementById('elem-max-width').addEventListener('input', updateSelectedElement);
        document.getElementById('elem-wrap').addEventListener('change', updateSelectedElement);
        document.getElementById('elem-invert').addEventListener('change', updateSelectedElement);
        document.getElementById('elem-allow-empty').addEventListener('change', updateSelectedElement);

        // Text element actions
        document.getElementById('btn-delete-element').addEventListener('click', deleteSelectedElement);
        document.getElementById('btn-duplicate-element').addEventListener('click', duplicateSelectedElement);

        // Bar element property changes
        document.getElementById('elem-bar-value').addEventListener('input', updateSelectedElement);
        document.getElementById('elem-bar-x').addEventListener('input', updateSelectedElement);
        document.getElementById('elem-bar-y').addEventListener('input', updateSelectedElement);
        document.getElementById('elem-bar-width').addEventListener('input', updateSelectedElement);
        document.getElementById('elem-bar-height').addEventListener('input', updateSelectedElement);
        document.getElementById('elem-bar-border').addEventListener('change', updateSelectedElement);
        document.getElementById('elem-bar-preview').addEventListener('input', function() {
            document.getElementById('elem-bar-preview-value').textContent = this.value;
            updateSelectedElement();
        });

        // Bar element actions
        document.getElementById('btn-delete-bar').addEventListener('click', deleteSelectedElement);
        document.getElementById('btn-duplicate-bar').addEventListener('click', duplicateSelectedElement);

        // Scroll effect controls
        document.getElementById('scroll-effect').addEventListener('change', function() {
            const needsSpeed = !['static', 'fade_in'].includes(this.value);
            document.getElementById('scroll-speed-group').style.display = needsSpeed ? 'block' : 'none';
            document.getElementById('scroll-fps-group').style.display = needsSpeed ? 'block' : 'none';
        });

        document.getElementById('scroll-speed').addEventListener('input', function() {
            document.getElementById('scroll-speed-value').textContent = this.value;
        });

        document.getElementById('scroll-fps').addEventListener('input', function() {
            document.getElementById('scroll-fps-value').textContent = this.value;
        });

        // Canvas mouse events
        const canvasContainer = document.getElementById('canvas-container');
        canvasContainer.addEventListener('mousedown', handleCanvasMouseDown);
        canvasContainer.addEventListener('mousemove', handleCanvasMouseMove);
        canvasContainer.addEventListener('mouseup', handleCanvasMouseUp);
        canvas.addEventListener('mousemove', updateMousePosition);

        // Data source modal
        const dataSourceModal = document.getElementById('dataSourceModal');
        const addDataSourceBtn = document.getElementById('btn-add-data-source');
        if (dataSourceModal && addDataSourceBtn) {
            addDataSourceBtn.addEventListener('click', () => {
                new bootstrap.Modal(dataSourceModal).show();
            });
        }

        const testDataSourceBtn = document.getElementById('btn-test-data-source');
        if (testDataSourceBtn) testDataSourceBtn.addEventListener('click', testDataSource);
        const addDataSourceConfirmBtn = document.getElementById('btn-add-data-source-confirm');
        if (addDataSourceConfirmBtn) addDataSourceConfirmBtn.addEventListener('click', confirmAddDataSource);

        // Preview
        document.getElementById('btn-preview').addEventListener('click', showPreview);

        // Save
        document.getElementById('btn-save').addEventListener('click', saveScreen);

        // Keyboard shortcuts
        document.addEventListener('keydown', handleKeyDown);

        // Variable helper - click to insert into focused text input
        document.querySelectorAll('.variable-item').forEach(item => {
            item.addEventListener('click', function() {
                const variable = this.dataset.var;
                // Insert into whichever text input is active
                const barValueInput = document.getElementById('elem-bar-value');
                const textInput = document.getElementById('elem-text');
                const activeInput = document.activeElement;
                if (activeInput === barValueInput || activeInput === textInput) {
                    activeInput.value += variable;
                    activeInput.dispatchEvent(new Event('input'));
                } else if (textInput) {
                    textInput.value += variable;
                    textInput.dispatchEvent(new Event('input'));
                }
            });
        });
    }

    // Update canvas dimensions based on display type
    function updateCanvasDimensions() {
        const dims = DISPLAY_DIMS[state.displayType];
        state.canvasWidth = dims.width;
        state.canvasHeight = dims.height;

        canvas.width = dims.width;
        canvas.height = dims.height;

        document.getElementById('canvas-dimensions').textContent = `${dims.width} x ${dims.height} pixels`;
    }

    // Update effects panel visibility
    function updateEffectsPanel() {
        const effectsPanel = document.getElementById('effects-panel');
        effectsPanel.style.display = state.displayType === 'led' ? 'none' : 'block';
    }

    // Add new text element
    function addTextElement() {
        const element = {
            id: Date.now(),
            type: 'text',
            text: 'New Text',
            x: 10,
            y: 10,
            font: 'small',
            maxWidth: null,
            wrap: true,
            invert: false,
            allowEmpty: false
        };

        state.elements.push(element);
        selectElement(element.id);
        updateLayers();
        render();
    }

    // Add new bar graph element
    function addBarElement() {
        const element = {
            id: Date.now(),
            type: 'bar',
            x: 26,
            y: 10,
            barWidth: 75,
            barHeight: 9,
            value: BAR_DEFAULT_VALUE,
            border: true,
            barPreview: BAR_DEFAULT_PREVIEW
        };

        state.elements.push(element);
        selectElement(element.id);
        updateLayers();
        render();
    }

    // Select element
    function selectElement(elementId) {
        state.selectedElement = elementId;
        const element = getElementById(elementId);

        if (element) {
            showElementProps(element);
            updateLayers();
            render();
        }
    }

    // Show element properties panel (text or bar)
    function showElementProps(element) {
        if (element.type === 'bar') {
            document.getElementById('element-props-panel').style.display = 'none';
            document.getElementById('bar-props-panel').style.display = 'block';

            document.getElementById('elem-bar-value').value = element.value || '50';
            document.getElementById('elem-bar-x').value = element.x;
            document.getElementById('elem-bar-y').value = element.y;
            document.getElementById('elem-bar-width').value = element.barWidth || 75;
            document.getElementById('elem-bar-height').value = element.barHeight || 9;
            document.getElementById('elem-bar-border').checked = element.border !== false;
            const preview = element.barPreview != null ? element.barPreview : 60;
            document.getElementById('elem-bar-preview').value = preview;
            document.getElementById('elem-bar-preview-value').textContent = preview;
        } else {
            document.getElementById('bar-props-panel').style.display = 'none';
            document.getElementById('element-props-panel').style.display = 'block';

            document.getElementById('elem-text').value = element.text;
            document.getElementById('elem-font').value = element.font;
            document.getElementById('elem-x').value = element.x;
            document.getElementById('elem-y').value = element.y;
            document.getElementById('elem-max-width').value = element.maxWidth || '';
            document.getElementById('elem-wrap').checked = element.wrap;
            document.getElementById('elem-invert').checked = element.invert || false;
            document.getElementById('elem-allow-empty').checked = element.allowEmpty || false;
        }
    }

    // Hide element properties panels
    function hideElementProps() {
        document.getElementById('element-props-panel').style.display = 'none';
        document.getElementById('bar-props-panel').style.display = 'none';
    }

    // Update selected element from form inputs
    function updateSelectedElement() {
        if (!state.selectedElement) return;

        const element = getElementById(state.selectedElement);
        if (!element) return;

        if (element.type === 'bar') {
            element.value = document.getElementById('elem-bar-value').value;
            element.x = parseInt(document.getElementById('elem-bar-x').value) || 0;
            element.y = parseInt(document.getElementById('elem-bar-y').value) || 0;
            element.barWidth = Math.max(BAR_MIN_WIDTH, parseInt(document.getElementById('elem-bar-width').value) || 75);
            element.barHeight = Math.max(BAR_MIN_HEIGHT, parseInt(document.getElementById('elem-bar-height').value) || 9);
            element.border = document.getElementById('elem-bar-border').checked;
            element.barPreview = parseInt(document.getElementById('elem-bar-preview').value) || 60;
        } else {
            element.text = document.getElementById('elem-text').value;
            element.font = document.getElementById('elem-font').value;
            element.x = parseInt(document.getElementById('elem-x').value) || 0;
            element.y = parseInt(document.getElementById('elem-y').value) || 0;

            const maxWidthVal = document.getElementById('elem-max-width').value;
            element.maxWidth = maxWidthVal ? parseInt(maxWidthVal) : null;

            element.wrap = document.getElementById('elem-wrap').checked;
            element.invert = document.getElementById('elem-invert').checked;
            element.allowEmpty = document.getElementById('elem-allow-empty').checked;
        }

        updateLayers();
        render();
    }

    // Delete selected element
    function deleteSelectedElement() {
        if (!state.selectedElement) return;

        state.elements = state.elements.filter(e => e.id !== state.selectedElement);
        state.selectedElement = null;
        hideElementProps();
        updateLayers();
        render();
    }

    // Duplicate selected element
    function duplicateSelectedElement() {
        if (!state.selectedElement) return;

        const element = getElementById(state.selectedElement);
        if (!element) return;

        const newElement = {
            ...element,
            id: Date.now(),
            x: element.x + 10,
            y: element.y + 10
        };

        state.elements.push(newElement);
        selectElement(newElement.id);
        updateLayers();
        render();
    }

    // Get element by ID
    function getElementById(id) {
        return state.elements.find(e => e.id === id);
    }

    // Update layers list
    function updateLayers() {
        const layersList = document.getElementById('layers-list');
        const layerCount = document.getElementById('layer-count');

        layerCount.textContent = state.elements.length;

        if (state.elements.length === 0) {
            layersList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>No elements yet</p>
                    <small>Click "Add Text" or "Add Bar Graph"</small>
                </div>
            `;
            return;
        }

        layersList.innerHTML = state.elements.map((element, index) => {
            const isBar = element.type === 'bar';
            const icon = isBar ? 'fa-chart-bar' : 'fa-font';
            const label = isBar
                ? `Bar ${element.barWidth}×${element.barHeight}`
                : escapeHtml(element.text);
            const meta = `(${element.x}, ${element.y})`;

            return `
            <div class="layer-item ${state.selectedElement === element.id ? 'selected' : ''}"
                 data-element-id="${element.id}">
                <div class="layer-icon">
                    <i class="fas ${icon}"></i>
                </div>
                <div class="layer-content">
                    <div class="layer-text">${label}</div>
                    <div class="layer-meta">${isBar ? '' : element.font + ' • '}${meta}</div>
                </div>
                <div class="layer-actions">
                    <button class="layer-action-btn layer-move-up" ${index === 0 ? 'disabled' : ''}>
                        <i class="fas fa-arrow-up"></i>
                    </button>
                    <button class="layer-action-btn layer-move-down" ${index === state.elements.length - 1 ? 'disabled' : ''}>
                        <i class="fas fa-arrow-down"></i>
                    </button>
                </div>
            </div>`;
        }).join('');

        // Add layer click handlers
        layersList.querySelectorAll('.layer-item').forEach(item => {
            const elementId = parseInt(item.dataset.elementId);

            item.addEventListener('click', (e) => {
                if (!e.target.closest('.layer-action-btn')) {
                    selectElement(elementId);
                }
            });

            // Move layer up/down
            item.querySelector('.layer-move-up')?.addEventListener('click', (e) => {
                e.stopPropagation();
                moveLayer(elementId, -1);
            });

            item.querySelector('.layer-move-down')?.addEventListener('click', (e) => {
                e.stopPropagation();
                moveLayer(elementId, 1);
            });
        });
    }

    // Move layer in z-order
    function moveLayer(elementId, direction) {
        const index = state.elements.findIndex(e => e.id === elementId);
        if (index === -1) return;

        const newIndex = index + direction;
        if (newIndex < 0 || newIndex >= state.elements.length) return;

        // Swap elements
        [state.elements[index], state.elements[newIndex]] = [state.elements[newIndex], state.elements[index]];

        updateLayers();
        render();
    }

    // Render canvas
    function render() {
        // Clear canvas (black background mimics OLED)
        ctx.fillStyle = '#000';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Render each element
        state.elements.forEach(element => {
            renderElement(element);
        });

        // Update overlays
        updateOverlays();
    }

    // Render single element on canvas
    function renderElement(element) {
        if (element.type === 'bar') {
            renderBarElement(element);
        } else {
            renderTextElement(element);
        }
    }

    // Render a text element on the canvas preview
    function renderTextElement(element) {
        const fontSize = FONT_SIZES[element.font] || 11;
        ctx.fillStyle = element.invert ? '#000' : '#fff';
        ctx.font = `${fontSize}px monospace`;
        ctx.textBaseline = 'top';
        ctx.fillText(element.text, element.x, element.y);
    }

    // Render a bar graph element on the canvas preview
    function renderBarElement(element) {
        const x = Math.max(0, element.x);
        const y = Math.max(0, element.y);
        const w = Math.max(BAR_MIN_WIDTH, element.barWidth || 75);
        const h = Math.max(BAR_MIN_HEIGHT, element.barHeight || 9);
        const pct = Math.max(0, Math.min(100, element.barPreview != null ? element.barPreview : 60));
        const showBorder = element.border !== false;

        ctx.strokeStyle = '#fff';
        ctx.fillStyle = '#fff';
        ctx.lineWidth = 1;

        if (showBorder) {
            ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
            const inner = Math.max(0, Math.floor((pct / 100) * (w - 2)));
            if (inner > 0) {
                ctx.fillRect(x + 1, y + 1, inner, h - 2);
            }
        } else {
            const filled = Math.max(0, Math.floor((pct / 100) * w));
            if (filled > 0) {
                ctx.fillRect(x, y, filled, h);
            }
        }
    }

    // Update element overlays for drag handles
    function updateOverlays() {
        const overlaysContainer = document.getElementById('element-overlays');
        overlaysContainer.innerHTML = '';

        state.elements.forEach(element => {
            let elemW, elemH;
            if (element.type === 'bar') {
                elemW = element.barWidth || 75;
                elemH = element.barHeight || 9;
            } else {
                const fontSize = FONT_SIZES[element.font] || 11;
                ctx.font = `${fontSize}px monospace`;
                elemW = Math.max(10, ctx.measureText(element.text).width);
                elemH = fontSize;
            }

            const overlay = document.createElement('div');
            overlay.className = 'element-overlay';
            if (state.selectedElement === element.id) {
                overlay.classList.add('selected');
            }

            overlay.style.left = `${element.x}px`;
            overlay.style.top = `${element.y}px`;
            overlay.style.width = `${elemW}px`;
            overlay.style.height = `${elemH}px`;
            overlay.dataset.elementId = element.id;

            const label = document.createElement('div');
            label.className = 'element-overlay-label';
            if (element.type === 'bar') {
                label.textContent = `bar ${element.barWidth}px`;
            } else {
                label.textContent = element.text.substring(0, 20);
            }
            overlay.appendChild(label);

            overlaysContainer.appendChild(overlay);
        });
    }

    // Canvas mouse handlers
    function handleCanvasMouseDown(e) {
        const rect = canvas.getBoundingClientRect();
        const x = Math.floor((e.clientX - rect.left) / state.zoom);
        const y = Math.floor((e.clientY - rect.top) / state.zoom);

        // Check if clicking on an overlay
        const overlay = e.target.closest('.element-overlay');
        if (overlay) {
            const elementId = parseInt(overlay.dataset.elementId);
            selectElement(elementId);

            state.isDragging = true;
            state.dragElement = elementId;
            state.dragStartX = x;
            state.dragStartY = y;

            e.preventDefault();
        }
    }

    function handleCanvasMouseMove(e) {
        if (!state.isDragging || !state.dragElement) return;

        const rect = canvas.getBoundingClientRect();
        const x = Math.floor((e.clientX - rect.left) / state.zoom);
        const y = Math.floor((e.clientY - rect.top) / state.zoom);

        const element = getElementById(state.dragElement);
        if (!element) return;

        const deltaX = x - state.dragStartX;
        const deltaY = y - state.dragStartY;

        element.x += deltaX;
        element.y += deltaY;

        // Clamp to canvas bounds
        element.x = Math.max(0, Math.min(state.canvasWidth - 10, element.x));
        element.y = Math.max(0, Math.min(state.canvasHeight - 10, element.y));

        state.dragStartX = x;
        state.dragStartY = y;

        // Sync position back to the active props form
        if (element.type === 'bar') {
            document.getElementById('elem-bar-x').value = element.x;
            document.getElementById('elem-bar-y').value = element.y;
        } else {
            document.getElementById('elem-x').value = element.x;
            document.getElementById('elem-y').value = element.y;
        }

        updateLayers();
        render();
    }

    function handleCanvasMouseUp() {
        state.isDragging = false;
        state.dragElement = null;
    }

    function updateMousePosition(e) {
        const rect = canvas.getBoundingClientRect();
        const x = Math.floor((e.clientX - rect.left) / state.zoom);
        const y = Math.floor((e.clientY - rect.top) / state.zoom);

        document.getElementById('mouse-position').textContent = `X: ${x}, Y: ${y}`;
    }

    // Zoom
    function changeZoom(delta) {
        state.zoom = Math.max(0.5, Math.min(3, state.zoom + delta));

        const container = document.getElementById('canvas-container');
        container.style.transform = `scale(${state.zoom})`;

        document.getElementById('zoom-level').textContent = `${Math.round(state.zoom * 100)}%`;
    }

    // Keyboard shortcuts
    function handleKeyDown(e) {
        // Delete
        if ((e.key === 'Delete' || e.key === 'Backspace') && state.selectedElement) {
            if (!['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
                deleteSelectedElement();
                e.preventDefault();
            }
        }

        // Duplicate (Ctrl/Cmd + D)
        if ((e.ctrlKey || e.metaKey) && e.key === 'd' && state.selectedElement) {
            duplicateSelectedElement();
            e.preventDefault();
        }

        // Deselect (Esc)
        if (e.key === 'Escape' && state.selectedElement) {
            state.selectedElement = null;
            hideElementProps();
            updateLayers();
            render();
        }
    }

    // Data sources
    function testDataSource() {
        const endpoint = document.getElementById('data-source-endpoint').value;
        if (!endpoint) {
            alert('Please select an endpoint');
            return;
        }

        const preview = document.getElementById('data-source-preview');
        preview.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';
        preview.style.display = 'block';

        fetch(endpoint)
            .then(response => response.json())
            .then(data => {
                preview.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            })
            .catch(error => {
                preview.innerHTML = `<div class="text-danger">Error: ${error.message}</div>`;
            });
    }

    function confirmAddDataSource() {
        const endpoint = document.getElementById('data-source-endpoint').value;
        const varName = document.getElementById('data-source-var-name').value;

        if (!endpoint || !varName) {
            alert('Please fill in all fields');
            return;
        }

        state.dataSources.push({ endpoint, var_name: varName });
        updateDataSourcesList();

        // Close modal
        bootstrap.Modal.getInstance(document.getElementById('dataSourceModal')).hide();

        // Clear form
        document.getElementById('data-source-endpoint').value = '';
        document.getElementById('data-source-var-name').value = '';
        document.getElementById('data-source-preview').style.display = 'none';
    }

    function updateDataSourcesList() {
        const list = document.getElementById('data-sources-list');

        if (state.dataSources.length === 0) {
            list.innerHTML = '';
            return;
        }

        list.innerHTML = state.dataSources.map((source, index) => `
            <div class="data-source-item">
                <strong>${source.var_name}</strong>
                <code>${source.endpoint}</code>
                <button class="btn btn-sm btn-danger" onclick="ScreenEditor.removeDataSource(${index})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `).join('');

        // Update variable helper
        updateDynamicVariables();
    }

    function removeDataSource(index) {
        state.dataSources.splice(index, 1);
        updateDataSourcesList();
    }

    function updateDynamicVariables() {
        const container = document.getElementById('dynamic-variables');

        if (state.dataSources.length === 0) {
            container.innerHTML = '';
            return;
        }

        container.innerHTML = '<strong>From Data Sources:</strong>';

        state.dataSources.forEach(source => {
            const div = document.createElement('div');
            div.className = 'variable-item';
            div.dataset.var = `{${source.var_name}}`;
            div.innerHTML = `
                <code>{${source.var_name}.*}</code>
                <small>Access properties from ${source.endpoint}</small>
            `;
            div.addEventListener('click', function() {
                const barValueInput = document.getElementById('elem-bar-value');
                const textInput = document.getElementById('elem-text');
                const activeInput = document.activeElement;
                const target = (activeInput === barValueInput || activeInput === textInput)
                    ? activeInput : textInput;
                if (target) {
                    target.value += `{${source.var_name}.`;
                    target.focus();
                }
            });
            container.appendChild(div);
        });
    }

    // Preview
    function showPreview() {
        const previewCanvas = document.getElementById('preview-canvas');
        const previewCtx = previewCanvas.getContext('2d');

        // Copy current canvas to preview
        previewCanvas.width = canvas.width;
        previewCanvas.height = canvas.height;
        previewCtx.drawImage(canvas, 0, 0);

        // Show modal
        const previewModal = document.getElementById('previewModal');
        if (previewModal) {
            new bootstrap.Modal(previewModal).show();
        } else {
            console.error('Preview modal element not found');
        }
    }

    // Save screen
    function saveScreen() {
        const screenData = {
            name: document.getElementById('screen-name').value,
            description: document.getElementById('screen-description').value,
            display_type: state.displayType,
            enabled: document.getElementById('screen-enabled').checked,
            duration: parseInt(document.getElementById('screen-duration').value) || 10,
            template_data: buildTemplateData(),
            data_sources: state.dataSources
        };

        if (!screenData.name) {
            alert('Please enter a screen name');
            return;
        }

        const url = state.screenId ? `/api/screens/${state.screenId}` : '/api/screens';
        const method = state.screenId ? 'PUT' : 'POST';

        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': window.CSRF_TOKEN
            },
            body: JSON.stringify(screenData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error saving screen: ' + data.error);
            } else {
                alert('Screen saved successfully!');
                window.location.href = '/screens';
            }
        })
        .catch(error => {
            alert('Error saving screen: ' + error.message);
        });
    }

    // Build template data from editor state.
    // Always uses the 'elements' format so bar graphs and other graphics types
    // are preserved correctly.  The server-side renderer supports both 'elements'
    // and the legacy 'lines' format.
    function buildTemplateData() {
        const elements = state.elements.map(e => {
            if (e.type === 'bar') {
                return {
                    type: 'bar',
                    x: e.x,
                    y: e.y,
                    width: e.barWidth || 75,
                    height: e.barHeight || 9,
                    value: e.value || '0',
                    border: e.border !== false
                };
            } else {
                return {
                    type: 'text',
                    text: e.text,
                    x: e.x,
                    y: e.y,
                    font: e.font,
                    max_width: e.maxWidth || null,
                    wrap: e.wrap,
                    invert: e.invert || null,
                    allow_empty: e.allowEmpty || false
                };
            }
        });

        const template = {
            elements: elements,
            clear: true
        };

        // Add scroll effect if not static (only meaningful for pure-text screens)
        const scrollEffect = document.getElementById('scroll-effect').value;
        if (scrollEffect && scrollEffect !== 'static') {
            template.scroll_effect = scrollEffect;
            template.scroll_speed = parseInt(document.getElementById('scroll-speed').value);
            template.scroll_fps = parseInt(document.getElementById('scroll-fps').value);
        }

        return template;
    }

    // Load existing screen data
    function loadScreen(screenData) {
        document.getElementById('screen-name').value = screenData.name || '';
        document.getElementById('screen-description').value = screenData.description || '';
        document.getElementById('display-type').value = screenData.display_type || 'oled';
        document.getElementById('screen-enabled').checked = screenData.enabled !== false;
        document.getElementById('screen-duration').value = screenData.duration || 10;

        state.displayType = screenData.display_type || 'oled';
        updateCanvasDimensions();
        updateEffectsPanel();

        // Load elements: prefer 'elements' format, fall back to legacy 'lines'
        if (screenData.template_data && screenData.template_data.elements) {
            state.elements = screenData.template_data.elements.map((elem, index) => {
                if (elem.type === 'bar') {
                    return {
                        id: Date.now() + index,
                        type: 'bar',
                        x: elem.x || 0,
                        y: elem.y || 0,
                        barWidth: elem.width || 75,
                        barHeight: elem.height || 9,
                        value: elem.value != null ? String(elem.value) : BAR_DEFAULT_VALUE,
                        border: elem.border !== false,
                        barPreview: BAR_DEFAULT_PREVIEW
                    };
                } else {
                    // 'text' type or any unknown element — treat as text
                    return {
                        id: Date.now() + index,
                        type: 'text',
                        text: elem.text || '',
                        x: elem.x || 0,
                        y: elem.y || 0,
                        font: elem.font || 'small',
                        maxWidth: elem.max_width || null,
                        wrap: elem.wrap !== false,
                        invert: elem.invert || false,
                        allowEmpty: elem.allow_empty || false
                    };
                }
            });
        } else if (screenData.template_data && screenData.template_data.lines) {
            // Legacy lines format — all treated as text elements
            state.elements = screenData.template_data.lines.map((line, index) => ({
                id: Date.now() + index,
                type: 'text',
                text: line.text || '',
                x: line.x || 0,
                y: line.y || 0,
                font: line.font || 'small',
                maxWidth: line.max_width || null,
                wrap: line.wrap !== false,
                invert: line.invert || false,
                allowEmpty: line.allow_empty || false
            }));
        }

        // Load scroll effects
        if (screenData.template_data) {
            const scrollEffect = screenData.template_data.scroll_effect || 'static';
            document.getElementById('scroll-effect').value = scrollEffect;

            if (scrollEffect && scrollEffect !== 'static') {
                document.getElementById('scroll-speed').value = screenData.template_data.scroll_speed || 4;
                document.getElementById('scroll-fps').value = screenData.template_data.scroll_fps || 60;
                document.getElementById('scroll-speed-value').textContent = screenData.template_data.scroll_speed || 4;
                document.getElementById('scroll-fps-value').textContent = screenData.template_data.scroll_fps || 60;
                document.getElementById('scroll-speed-group').style.display = 'block';
                document.getElementById('scroll-fps-group').style.display = 'block';
            }
        }

        // Load data sources
        if (screenData.data_sources) {
            state.dataSources = screenData.data_sources;
            updateDataSourcesList();
        }

        document.getElementById('screen-name-display').textContent = screenData.name || 'New Screen';

        updateLayers();
        render();
    }

    // Utility: Escape HTML
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Public API
    return {
        init,
        loadScreen,
        removeDataSource
    };
})();

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    ScreenEditor.init();
});
