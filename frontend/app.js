// GoMacroTool - Wails Frontend Application

// State
const state = {
    enabled: false,
    pinned: false,
    macrosPaused: false,
    gameActive: false,
    macros: [],
    buffs: {},
    triggers: [],
    settings: {}
};

// Initialize
async function init() {
    console.log('GoMacroTool initializing...');
    
    // Load initial state
    await loadState();
    
    // Set up event listeners
    setupEventListeners();
    
    // Set up Wails events
    setupWailsEvents();
    
    // Start polling for buff timers
    startBuffTimerPoll();
    
    console.log('GoMacroTool initialized');
}

// Load state from backend
async function loadState() {
    try {
        // Get config
        const config = await window.go.main.App.GetConfig();
        state.settings = config.settings;
        
        // Get toggle state
        state.enabled = await window.go.main.App.GetToggle();
        state.gameActive = await window.go.main.App.GetGameActive();
        state.macrosPaused = await window.go.main.App.GetPause();
        
        // Load macros from config
        state.macros = [];
        if (config.games && config.activeGame) {
            const game = config.games[config.activeGame];
            if (game && game.classes && config.activeClass) {
                const classSpec = game.classes[config.activeClass];
                if (classSpec && classSpec.specs && config.activeSpec) {
                    const spec = classSpec.specs[config.activeSpec];
                    if (spec) {
                        state.macros = spec.macros || [];
                        state.triggers = spec.pixelTriggers || [];
                    }
                }
            }
        }
        
        updateUI();
    } catch (err) {
        console.error('Failed to load state:', err);
    }
}

// Set up DOM event listeners
function setupEventListeners() {
    // Toggle button
    document.getElementById('toggleBtn').addEventListener('click', toggleMacros);
    
    // Pin button
    document.getElementById('pinBtn').addEventListener('click', togglePin);
    
    // Clear buffs button
    document.getElementById('clearBuffsBtn').addEventListener('click', clearAllBuffs);
    
    // Settings modal
    document.getElementById('cancelSettingsBtn').addEventListener('click', () => {
        document.getElementById('settingsModal').classList.remove('active');
    });
    
    document.getElementById('settingsForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveSettings();
    });
    
    // Pixel picker modal
    document.getElementById('cancelPickerBtn').addEventListener('click', () => {
        document.getElementById('pixelPickerModal').classList.remove('active');
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyDown);
}

// Set up Wails event handlers
function setupWailsEvents() {
    if (window.runtime) {
        // Listen for buff events
        window.runtime.on('buffEvent', (event, data) => {
            console.log('Buff event:', data);
            if (data.event === 'expired') {
                // Refresh buff display
                updateBuffs();
            }
        });
        
        // Listen for macro state changes
        window.runtime.on('macroState', (event, data) => {
            console.log('Macro state:', data);
            updateMacroDisplay(data.running);
        });
        
        // Listen for game active changes
        window.runtime.on('gameActive', (event, data) => {
            console.log('Game active:', data);
            state.gameActive = data.active;
            updateGameStatus();
        });
    }
}

// Toggle macros enabled/disabled
async function toggleMacros() {
    state.enabled = !state.enabled;
    
    try {
        await window.go.main.App.SetToggle(state.enabled);
        updateToggleButton();
    } catch (err) {
        console.error('Failed to toggle:', err);
        state.enabled = !state.enabled;
    }
}

// Toggle overlay pinned state
function togglePin() {
    state.pinned = !state.pinned;
    document.getElementById('pinBtn').classList.toggle('pinned', state.pinned);
    
    // Notify backend (for window behavior)
    // This would require additional Wails bindings
}

// Clear all buff timers
async function clearAllBuffs() {
    try {
        await window.go.main.App.ClearAllBuffs();
        state.buffs = {};
        updateBuffs();
    } catch (err) {
        console.error('Failed to clear buffs:', err);
    }
}

// Activate a buff timer
async function activateBuff(buffName) {
    try {
        await window.go.main.App.ActivateBuff(buffName);
        updateBuffs();
    } catch (err) {
        console.error('Failed to activate buff:', err);
    }
}

// Update UI based on state
function updateUI() {
    updateToggleButton();
    updateGameStatus();
    updateMacroDisplay();
    updateMacrosList();
    updateTriggersList();
    updateBuffs();
}

// Update toggle button state
function updateToggleButton() {
    const btn = document.getElementById('toggleBtn');
    const indicator = btn.querySelector('.toggle-indicator');
    const text = btn.querySelector('.toggle-text');
    
    btn.classList.toggle('active', state.enabled);
    text.textContent = state.enabled ? 'Enabled' : 'Disabled';
}

// Update game status display
function updateGameStatus() {
    const statusDot = document.querySelector('#gameStatus .status-dot');
    const statusText = document.querySelector('#gameStatus .status-text');
    
    statusDot.classList.toggle('active', state.gameActive);
    statusDot.classList.toggle('inactive', !state.gameActive);
    statusText.textContent = state.gameActive ? 'Game: Active' : 'Game: Inactive';
}

// Update macro display
function updateMacroDisplay(runningMacros = {}) {
    const running = runningMacros || {};
    
    document.querySelectorAll('.macro-item').forEach(item => {
        const hotkey = item.dataset.hotkey;
        const statusEl = item.querySelector('.macro-status');
        
        if (running[hotkey]) {
            item.classList.add('running');
            statusEl.classList.remove('ready');
            statusEl.classList.add('running');
            statusEl.textContent = 'Running';
        } else {
            item.classList.remove('running');
            statusEl.classList.remove('running');
            statusEl.classList.add('ready');
            statusEl.textContent = 'Ready';
        }
    });
}

// Update macros list
function updateMacrosList() {
    const list = document.getElementById('macroList');
    
    if (state.macros.length === 0) {
        list.innerHTML = '<div class="empty-state">No macros configured</div>';
        return;
    }
    
    list.innerHTML = state.macros.map(macro => `
        <div class="macro-item" data-hotkey="${escapeHtml(macro.hotkey)}">
            <span class="macro-hotkey">${escapeHtml(macro.hotkey)}</span>
            <div class="macro-info">
                <div class="macro-name">${escapeHtml(macro.name)}</div>
                <div class="macro-keys">${escapeHtml(macro.keys?.join(' + ') || '')}</div>
            </div>
            <span class="macro-status ready">Ready</span>
        </div>
    `).join('');
    
    // Add click handlers for buff activation
    list.querySelectorAll('.macro-item').forEach(item => {
        item.addEventListener('click', () => {
            const name = item.querySelector('.macro-name').textContent;
            const macro = state.macros.find(m => m.name === name);
            if (macro && macro.buffTrigger) {
                activateBuff(name);
            }
        });
    });
}

// Update triggers list
function updateTriggersList() {
    const list = document.getElementById('triggerList');
    
    if (state.triggers.length === 0) {
        list.innerHTML = '<div class="empty-state">No triggers active</div>';
        return;
    }
    
    list.innerHTML = state.triggers.map(trigger => `
        <div class="trigger-item">
            <span class="trigger-indicator ${trigger.enabled ? '' : 'inactive'}"></span>
            <span class="trigger-name">${escapeHtml(trigger.name)}</span>
        </div>
    `).join('');
}

// Update buffs display
function updateBuffs() {
    const list = document.getElementById('buffList');
    
    // Get buff timers from backend
    window.go.main.App.GetBuffTimers().then(buffs => {
        state.buffs = buffs;
        
        if (Object.keys(buffs).length === 0) {
            list.innerHTML = '<div class="empty-state">No active buffs</div>';
            return;
        }
        
        list.innerHTML = Object.entries(buffs).map(([name, info]) => {
            const percent = Math.min(100, (info.elapsed / info.duration) * 100);
            const isExpiring = info.remaining < 5000; // Last 5 seconds
            
            return `
                <div class="buff-item">
                    <div class="buff-header">
                        <span class="buff-name">${escapeHtml(name)}</span>
                        <span class="buff-time">${formatTime(info.remaining)}</span>
                    </div>
                    <div class="buff-progress">
                        <div class="buff-progress-bar ${isExpiring ? 'expiring' : ''}" 
                             style="width: ${100 - percent}%"></div>
                    </div>
                </div>
            `;
        }).join('');
    }).catch(err => {
        console.error('Failed to get buffs:', err);
    });
}

// Poll for buff timer updates
function startBuffTimerPoll() {
    setInterval(() => {
        if (state.enabled && Object.keys(state.buffs).length > 0) {
            updateBuffs();
        }
    }, 100);
}

// Save settings
async function saveSettings() {
    const settings = {
        toggleKey: document.getElementById('toggleKeySelect').value,
        pixelCheckRate: parseInt(document.getElementById('pixelRateInput').value),
        overlayWidth: parseInt(document.getElementById('overlayWidthInput').value),
        onlyInGame: document.getElementById('onlyInGameCheck').checked,
        autoDetectGame: document.getElementById('autoDetectCheck').checked
    };
    
    try {
        await window.go.main.App.SaveConfig({ settings });
        document.getElementById('settingsModal').classList.remove('active');
        state.settings = settings;
    } catch (err) {
        console.error('Failed to save settings:', err);
    }
}

// Handle keyboard input
function handleKeyDown(e) {
    // Escape closes modals
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal.active').forEach(modal => {
            modal.classList.remove('active');
        });
    }
}

// Utility: Format milliseconds to MM:SS
function formatTime(ms) {
    if (ms < 0) ms = 0;
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

// Utility: Escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
