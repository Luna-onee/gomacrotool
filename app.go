package main

import (
	"context"
	"fmt"

	"github.com/wailsapp/wails/v2/pkg/runtime"

	"github.com/Luna-onee/gomacrotool/internal/config"
	"github.com/Luna-onee/gomacrotool/internal/engine"
	"github.com/Luna-onee/gomacrotool/internal/input"
	"github.com/Luna-onee/gomacrotool/internal/windowsapi"
)

// App struct
type App struct {
	ctx      context.Context
	runtime  *runtime.Runtime
}

// NewApp creates a new App application struct
func NewApp() *App {
	return &App{}
}

// OnStartup is called when the app starts
func (a *App) OnStartup(ctx context.Context) {
	a.ctx = ctx

	// Initialize config
	if err := config.Init(); err != nil {
		fmt.Printf("Failed to init config: %v\n", err)
		return
	}

	// Setup engines
	spec := config.GetActiveSpec()
	if spec != nil {
		engine.MacroEngine.Setup(spec.Macros)
		engine.PixelEngine.Setup(spec.PixelTriggers)
		engine.BuffEngine.RegisterCallback(a.onBuffEvent)
	}

	engine.MacroEngine.RegisterCallback(a.onMacroState)
	engine.GameDetector.RegisterCallback(a.onGameActive)
	engine.GameDetector.Setup()
	engine.GameDetector.Start()
	engine.PixelEngine.Start()

	// Start buff engine worker
	go engine.BuffEngine.Worker()
}

// OnShutdown is called when the app shuts down
func (a *App) OnShutdown(ctx context.Context) {
	engine.MacroEngine.Cleanup()
	engine.PixelEngine.Stop()
	engine.GameDetector.Stop()
	engine.BuffEngine.Stop()
}

// Greet returns a greeting (for testing)
func (a *App) Greet(name string) string {
	return fmt.Sprintf("Hello %s!", name)
}

// GetConfig returns current configuration
func (a *App) GetConfig() config.Config {
	return config.Get()
}

// SaveConfig saves the provided configuration
func (a *App) SaveConfig(cfg config.Config) error {
	// TODO: Implement config update
	return config.Save()
}

// SetToggle enables or disables macros
func (a *App) SetToggle(enabled bool) {
	engine.MacroEngine.SetEnabled(enabled)
}

// GetToggle returns current toggle state
func (a *App) GetToggle() bool {
	return engine.MacroEngine.IsEnabled()
}

// SetPause pauses or resumes all macros
func (a *App) SetPause(paused bool) {
	engine.MacroEngine.SetPause(paused)
}

// GetPause returns current pause state
func (a *App) GetPause() bool {
	engine.MacroEngine.mu.RLock()
	defer engine.MacroEngine.mu.RUnlock()
	return engine.MacroEngine.macrosPaused
}

// GetRunningMacros returns list of running macros
func (a *App) GetRunningMacros() []string {
	running := engine.MacroEngine.GetRunning()
	result := make([]string, 0, len(running))
	for name, isRunning := range running {
		if isRunning {
			result = append(result, name)
		}
	}
	return result
}

// GetBuffTimers returns buff timer information
func (a *App) GetBuffTimers() map[string]engine.TimerInfo {
	return engine.BuffEngine.GetTimerInfo()
}

// ActivateBuff manually activates a buff timer
func (a *App) ActivateBuff(buffName string) error {
	spec := config.GetActiveSpec()
	if spec == nil {
		return fmt.Errorf("no active spec")
	}

	for _, buff := range spec.BuffTimers {
		if buff.Name == buffName {
			engine.BuffEngine.Activate(&buff)
			return nil
		}
	}
	return fmt.Errorf("buff not found: %s", buffName)
}

// ClearAllBuffs removes all active buff timers
func (a *App) ClearAllBuffs() {
	engine.BuffEngine.ClearAll()
}

// GetGameActive returns if game window is active
func (a *App) GetGameActive() bool {
	return engine.GameDetector.IsActive()
}

// SetActiveGame sets the active game
func (a *App) SetActiveGame(name string) error {
	// TODO: Find game and set it
	return config.SetActive(name, config.Get().ActiveClass, config.Get().ActiveSpec)
}

// PickPixel captures pixel at coordinates (for pixel picker)
func (a *App) PickPixel() map[string]interface{} {
	x, y := windowsapi.GetCursorPos()
	hdc := windowsapi.GetDC()
	defer windowsapi.ReleaseDC(hdc)

	color := windowsapi.GetPixel(hdc, x, y)
	resW, resH := windowsapi.GetScreenResolution()

	return map[string]interface{}{
		"x":          x,
		"y":          y,
		"color":       fmt.Sprintf("0x%06X", color),
		"screenWidth":  resW,
		"screenHeight": resH,
	}
}

func (a *App) onBuffEvent(event string, buffName string, detail map[string]interface{}) {
	// Notify frontend via runtime events
	if a.runtime != nil {
		a.runtime.EventsEmit("buffEvent", map[string]interface{}{
			"event":     event,
			"buffName":  buffName,
			"detail":     detail,
		})
	}
}

func (a *App) onMacroState() {
	// Notify frontend via runtime events
	if a.runtime != nil {
		a.runtime.EventsEmit("macroState", map[string]interface{}{
			"running": engine.MacroEngine.GetRunning(),
		})
	}
}

func (a *App) onGameActive(active bool) {
	// Notify frontend via runtime events
	if a.runtime != nil {
		a.runtime.EventsEmit("gameActive", map[string]interface{}{
			"active": active,
		})
	}
}
