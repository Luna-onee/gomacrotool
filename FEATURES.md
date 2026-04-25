# GoMacroTool - Feature Specification

## Overview
A high-performance Windows macro automation tool written in Go. Replaces Python/PyQt6 implementation with native Go + WASM-based GUI for better performance, single-binary distribution, and reduced runtime dependencies.

## Core Functionality

### 1. Macro Engine
- **Hold Mode**: Repeatedly send a sequence of keys while hotkey is held
  - Configurable repeat delay (ms)
  - Optional inter-key delay between key presses
  - Suppression of original keypress to prevent game input conflict

- **Press Mode**: Single trigger - send key sequence once on hotkey press

- **Hotkey Support**:
  - Keyboard: A-Z, 0-9, F1-F12, Tab, Enter, Escape, Space, Arrow keys
  - Modifiers: Ctrl (^), Alt (!), Shift (+), Windows (#)
  - Mouse buttons: Left, Right, Middle, XButton1, XButton2

- **Macro State**:
  - Per-macro enabled/disabled flag
  - Global pause/resume (all macros)
  - Running status tracking per macro

- **Thread Management**:
  - Dedicated goroutine per hold-mode macro
  - Thread affinity: last 25% of CPU cores (to minimize game impact)
  - High-resolution timer for precise delays

### 2. Pixel Triggers (Procs)
- **Polling-based screen detection**:
  - Configurable check rate (10-1000 Hz, default 250 Hz)
  - High-priority thread for minimal latency
  - Numba/SIMD-optimized color matching (or Go equivalent)

- **Pixel Matching**:
  - Check multiple pixels with color variation tolerance
  - Match modes: "all" (AND) or "any" (OR)
  - Resolution scaling: pixels stored at capture resolution, scaled to current screen

- **Advanced Conditions**:
  - **Anchor pixels**: Must match before trigger pixels are checked
  - **Blocker pixels**: If matched, trigger is blocked
  - **Inverse mode**: Trigger when pixels do NOT match

- **Trigger Modes**:
  - **"macro"**: Only when specific macro is running (or any macro)
  - **"always"**: Always check when game is active

- **Cooldown**: Minimum time between trigger activations (ms)

- **Actions**:
  - Send action key
  - Check and activate buff timers

### 3. Buff Timers
- **Key-triggered timers**:
  - Triggered by specific key presses (watchKeys)
  - Duration in milliseconds
  - Action key to send when timer expires

- **Pixel-triggered timers**:
  - Auto-activate when trigger pixels match
  - Auto-expire when pixels no longer match

- **Refresh behavior**:
  - **reset**: Start fresh timer from activation time
  - **extend**: Add extendMs to remaining time
  - **ignore**: Do nothing if timer already active

- **Timer Management**:
  - Min-heap based timer tracking for O(log n) operations
  - Callback system for UI updates
  - Progress tracking (elapsed, remaining, % complete)

### 4. Game Detection
- **Foreground window tracking**:
  - Poll at 150ms intervals
  - Match by game executable path
  - Cache process paths to reduce handle churn (2s TTL, 128 entry LRU)

- **Active state flags**:
  - `onlyInGame`: Only enable macros when game is active
  - `autoDetectGame`: Auto-switch active game by foreground window

- **Spec Detection** (automatic):
  - Pixel-based detection for game specs/classes
  - Auto-switch to matching spec on detection

### 5. Input System
- **Windows API Integration**:
  - `SendInput()` for synthetic keyboard/mouse events
  - `PostMessage()` for window-targeted input (buff refresh while tabbed out)
  - `SetWindowsHookEx(WH_MOUSE_LL)` for low-level mouse hook
  - `RegisterHotKey()` for global hotkey registration

- **Key Mapping**:
  - Virtual key codes (VK) to key name mapping
  - Extended key flag handling (Insert, Delete, Home, End, Numpad keys)
  - Scan code generation via MapVirtualKey()

- **Mouse Support**:
  - Left, Right, Middle, XButton1, XButton2
  - Separate down/up events for hold mode

- **Native Performance**:
  - C extension or Go assembly for critical paths
  - Batch key sending

### 6. Global Toggle
- **System-wide enable/disable**:
  - Default: ScrollLock LED state (lock key)
  - Also supports: F1-F12, Pause, PrintScreen, Insert (toggle state)
  - Mouse buttons: any mouse button can toggle

- **Toggle Methods**:
  - Lock keys: read LED state (ScrollLock, CapsLock, NumLock)
  - Other keys: toggle state on press
  - Mouse buttons: low-level mouse hook (suppress input to game)

- **Status Indication**:
  - LED on lock keys reflects toggle state
  - Overlay shows on/off status
  - Tray icon shows status

### 7. Overlay UI
- **Floating Material Design 3 window**:
  - Always on top, frameless
  - Transparent background
  - Click-through (except toggle switch)
  - Draggable via drag handle or Shift+drag

- **Display Sections**:
  - Header: status dot, toggle switch, game indicator, profile label
  - Macros: list with running status (filled/empty circle)
  - Procs (pixel triggers): list
  - Buffs: list with countdown and progress bar

- **Visual Feedback**:
  - Color coding based on toggle state (green=on, red=off)
  - Real-time buff timer updates (10ms interval)
  - Debounced content updates (50ms)

- **Customization**:
  - Position (top-left preset + X/Y offset)
  - Width, opacity

### 8. Pixel Picker Tool
- **Zoom overlay**:
  - 20x20 screen capture zoomed 10x
  - Crosshair with yellow center pixel box
  - Live color swatch display

- **Controls**:
  - Mouse: follow cursor
  - Space: freeze/unfreeze cursor position
  - Arrow keys: move 1px (continuous when held)
  - Click/Enter: select pixel
  - Escape: cancel

- **Output**:
  - X, Y coordinates
  - Hex color value
  - Screen resolution at time of capture

### 9. Configuration System
- **Hierarchical KDL format**:
  ```
  settings { }
  active game="" class="" spec=""
  game "name" path="" {
      class "name" {
          spec "name" {
              macro { }
              proc { }
              buff { }
              detect { }
          }
      }
  }
  ```

- **Settings**:
  - defaultDelay, autoDetectGame, onlyInGame, toggleKey
  - pixelCheckRate (Hz)
  - overlayPosition, overlayWidth, overlayOpacity, overlayX, overlayY

- **Storage**:
  - `%LOCALAPPDATA%/Jaides_Macro_Tool/config.kdl`
  - Atomic writes with backup
  - Auto-migration from legacy path

### 10. Performance Optimizations
- **Native Code Paths**:
  - C or Go assembly for pixel matching (SIMD)
  - Native hold loop with high-resolution sleep
  - Batch pixel checking

- **Threading**:
  - Separate goroutines for:
    - Macro hold loops
    - Pixel trigger polling
    - Buff timer worker
    - Mouse hook message pump
  - Thread affinity for macro threads

- **Precision Timing**:
  - QueryPerformanceCounter for sub-ms timing
  - High-resolution timer (timeBeginPeriod(1)) for delays >5ms
  - Busy-wait hybrid for <2ms delays

- **Process Path Cache**:
  - LRU cache of PID->path mappings
  - Reduces OpenProcess/GetModuleFileNameEx calls

### 11. System Integration
- **Admin Requirements**:
  - Elevate on startup if not running as admin
  - Required for global input hooks

- **Single Instance**:
  - Mutex-based singleton enforcement
  - Exit if another instance running

- **System Tray**:
  - Icon: rounded square with inner circle
  - Menu: Show/Hide, Reload, Quit
  - Click to toggle window visibility

- **Debug Server** (optional):
  - HTTP server for real-time inspection
  - Performance stats (loop timings, poll rates)
  - State inspection (running macros, active timers)

## Configuration Structures

### Macro
```json
{
  "name": "Rotation",
  "hotkey": "RButton",
  "delay": 1,
  "holdMode": true,
  "interKeyDelay": 0,
  "enabled": true,
  "keys": ["v", "g", "t"]
}
```

### Pixel Trigger (Proc)
```json
{
  "name": "Skill Off Cooldown",
  "actionKey": "1",
  "pixels": [{"x": 100, "y": 100, "color": "0xFF0000", "variation": 10}],
  "matchMode": "all",
  "triggerMode": "macro",
  "macroHotkey": "RButton",
  "enabled": true,
  "cooldown": 1000,
  "anchor": { "pixels": [...], "matchMode": "all" },
  "blocker": { "pixels": [...], "matchMode": "all" },
  "captureRes": {"w": 1920, "h": 1080}
}
```

### Buff Timer
```json
{
  "name": "Sanctum",
  "duration": 28800,
  "actionKey": "c",
  "onRefresh": "reset",
  "extendMs": 0,
  "enabled": true,
  "triggerType": "keys",
  "watchKeys": ["c"],
  "triggerPixels": [...],
  "triggerMatchMode": "all",
  "captureRes": {"w": 1920, "h": 1080}
}
```

### Spec Detection
```json
{
  "pixels": [{"x": 500, "y": 500, "color": "0x00FF00", "variation": 15}],
  "matchMode": "all",
  "captureRes": {"w": 1920, "h": 1080}
}
```

## Implementation Notes for Go Rewrite

### Key Libraries to Consider
- **GUI**: Fyne or Wails (WebAssembly-based)
- **Windows API**: `syscall` or `github.com/lxn/win` (or direct syscall)
- **Pixel Access**: `github.com/disintegration/imaging` or direct GDI32 calls
- **Threading**: Native goroutines + `runtime.LockOSThread()`
- **Timing**: `time.Sleep()` + busy-wait for precision
- **Config**: KDL parser (may need to port Python ckdl lib)

### Performance-Critical Paths
1. Pixel trigger polling loop
2. Hold loop key sending
3. Mouse hook callback
4. Color matching (SIMD optimization)

### Cross-Platform Considerations
- Primary target: Windows
- Game detection: Windows-specific APIs
- Input injection: Windows-specific
- Could potentially abstract for Linux (X11/Wayland) later

### Single Binary Distribution
- Use Go's static linking
- Embed config template and icon
- WASM UI bundled as assets
- No Python runtime required

## Non-Features (Explicitly Out of Scope)
- Scripting beyond KDL config (no Python/Lua plugins)
- Network features (no remote control)
- Cloud sync (local config only)
- Machine learning (pixel matching is exact/variation-based)
- Anti-cheat evasion (this is a legitimate accessibility tool)
