package config

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
)

// Config represents the application configuration
type Config struct {
	Games      map[string]Game `json:"games"`
	Settings   Settings      `json:"settings"`
	ActiveGame string       `json:"activeGame"`
	ActiveClass string       `json:"activeClass"`
	ActiveSpec  string       `json:"activeSpec"`
	mu         sync.RWMutex `json:"-"`
}

// Settings represents global application settings
type Settings struct {
	DefaultDelay      int     `json:"defaultDelay"`
	AutoDetectGame    bool    `json:"autoDetectGame"`
	OnlyInGame       bool    `json:"onlyInGame"`
	DarkMode         bool    `json:"darkMode"`
	ToggleKey        string   `json:"toggleKey"`
	PixelCheckRate   int      `json:"pixelCheckRate"`
	OverlayPosition  string   `json:"overlayPosition"`
	OverlayWidth     int      `json:"overlayWidth"`
	OverlayOpacity   float64  `json:"overlayOpacity"`
	OverlayX         int      `json:"overlayX"`
	OverlayY         int      `json:"overlayY"`
}

// Game represents a game configuration
type Game struct {
	Path    string             `json:"path"`
	Classes  map[string]Class   `json:"classes"`
}

// Class represents a game class/job
type Class struct {
	Specs map[string]Spec `json:"specs"`
}

// Spec represents a game specialization/build
type Spec struct {
	Macros        []Macro        `json:"macros"`
	PixelTriggers []PixelTrigger `json:"pixelTriggers"`
	BuffTimers    []BuffTimer    `json:"buffTimers"`
	Detect        *SpecDetect    `json:"detect,omitempty"`
}

// Macro represents a key macro
type Macro struct {
	Name           string   `json:"name"`
	Hotkey         string   `json:"hotkey"`
	Delay          int      `json:"delay"`
	HoldMode       bool     `json:"holdMode"`
	InterKeyDelay  int      `json:"interKeyDelay"`
	Keys           []string `json:"keys"`
	Enabled        bool     `json:"enabled"`
}

// PixelTrigger represents a pixel-based trigger
type PixelTrigger struct {
	Name         string         `json:"name"`
	ActionKey     string         `json:"actionKey"`
	Pixels        []Pixel        `json:"pixels"`
	MatchMode     string         `json:"matchMode"` // "all" or "any"
	TriggerMode   string         `json:"triggerMode"` // "macro" or "always"
	MacroHotkey   string         `json:"macroHotkey"`
	Inverse       bool           `json:"inverse"`
	Enabled       bool           `json:"enabled"`
	Cooldown      int            `json:"cooldown"`
	LastFired     int64          `json:"lastFired"`
	CaptureRes    *Resolution    `json:"captureRes,omitempty"`
	Anchor        *AnchorBlocker `json:"anchor,omitempty"`
	Blocker       *AnchorBlocker `json:"blocker,omitempty"`
}

// Pixel represents a single pixel coordinate with color
type Pixel struct {
	X          int32  `json:"x"`
	Y          int32  `json:"y"`
	Color       string `json:"color"` // Hex format "0xRRGGBB"
	Variation  int32  `json:"variation"`
}

// AnchorBlocker represents anchor or blocker pixel sets
type AnchorBlocker struct {
	Pixels    []Pixel `json:"pixels"`
	MatchMode string  `json:"matchMode"`
}

// BuffTimer represents a buff countdown timer
type BuffTimer struct {
	Name             string         `json:"name"`
	WatchKeys        []string       `json:"watchKeys"`
	Duration         int64          `json:"duration"`
	ActionKey        string         `json:"actionKey"`
	OnRefresh        string         `json:"onRefresh"` // "reset", "extend", "ignore"
	ExtendMs         int64          `json:"extendMs"`
	Enabled          bool           `json:"enabled"`
	TriggerType      string         `json:"triggerType"` // "keys" or "pixel"
	TriggerPixels    []Pixel        `json:"triggerPixels"`
	TriggerMatchMode string         `json:"triggerMatchMode"`
	CaptureRes       *Resolution    `json:"captureRes,omitempty"`
	RemainingMs      int64          `json:"-"` // Runtime state
	PxMatched        bool           `json:"-"` // Runtime state
}

// SpecDetect represents auto-detection for specs
type SpecDetect struct {
	Pixels     []Pixel    `json:"pixels"`
	MatchMode  string     `json:"matchMode"`
	CaptureRes *Resolution `json:"captureRes,omitempty"`
}

// Resolution represents screen resolution
type Resolution struct {
	W int32 `json:"w"`
	H int32 `json:"h"`
}

var (
	cfg   Config
	cfgMu sync.RWMutex
	configPath string
)

// Init initializes the config system
func Init() error {
	// Get config directory
	localAppData := os.Getenv("LOCALAPPDATA")
	if localAppData == "" {
		home, _ := os.UserHomeDir()
		localAppData = filepath.Join(home, ".config", "gomacrotool")
	} else {
		localAppData = filepath.Join(localAppData, "gomacrotool")
	}

	configPath = filepath.Join(localAppData, "config.json")

	// Create directory if needed
	if err := os.MkdirAll(filepath.Dir(configPath), 0755); err != nil {
		return err
	}

	// Load or create default config
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		cfg = DefaultConfig()
		return Save()
	}

	return Load()
}

// DefaultConfig returns the default configuration
func DefaultConfig() Config {
	return Config{
		Games: make(map[string]Game),
		Settings: Settings{
			DefaultDelay:     50,
			AutoDetectGame:   true,
			OnlyInGame:      true,
			DarkMode:        true,
			ToggleKey:       "scrolllock",
			PixelCheckRate:  250,
			OverlayPosition:  "top-left",
			OverlayWidth:    230,
			OverlayOpacity:  0.92,
			OverlayX:        10,
			OverlayY:        10,
		},
		ActiveGame:  "",
		ActiveClass: "",
		ActiveSpec:  "",
	}
}

// Load reads config from disk
func Load() error {
	cfgMu.Lock()
	defer cfgMu.Unlock()

	data, err := os.ReadFile(configPath)
	if err != nil {
		cfg = DefaultConfig()
		return err
	}

	if err := json.Unmarshal(data, &cfg); err != nil {
		cfg = DefaultConfig()
		return err
	}

	// Validate and fill defaults
	validate()
	return nil
}

// Save writes config to disk
func Save() error {
	cfgMu.RLock()
	defer cfgMu.RUnlock()

	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}

	// Atomic write
	tmpPath := configPath + ".tmp"
	if err := os.WriteFile(tmpPath, data, 0644); err != nil {
		return err
	}
	return os.Rename(tmpPath, configPath)
}

// Get returns a copy of the current config
func Get() Config {
	cfgMu.RLock()
	defer cfgMu.RUnlock()
	return cfg
}

// UpdateSettings updates global settings
func UpdateSettings(newSettings Settings) error {
	cfgMu.Lock()
	defer cfgMu.Unlock()
	cfg.Settings = newSettings
	return Save()
}

// SetActive sets the active game/class/spec
func SetActive(game, class, spec string) error {
	cfgMu.Lock()
	defer cfgMu.Unlock()
	cfg.ActiveGame = game
	cfg.ActiveClass = class
	cfg.ActiveSpec = spec
	return Save()
}

// GetActiveSpec returns the currently active spec
func GetActiveSpec() *Spec {
	cfgMu.RLock()
	defer cfgMu.RUnlock()

	game, ok := cfg.Games[cfg.ActiveGame]
	if !ok || cfg.ActiveGame == "" {
		return nil
	}

	class, ok := game.Classes[cfg.ActiveClass]
	if !ok || cfg.ActiveClass == "" {
		return nil
	}

	spec, ok := class.Specs[cfg.ActiveSpec]
	if !ok || cfg.ActiveSpec == "" {
		return nil
	}

	return &spec
}

// GetActiveMacros returns macros from active spec
func GetActiveMacros() []Macro {
	spec := GetActiveSpec()
	if spec == nil {
		return []Macro{}
	}
	return spec.Macros
}

// GetActivePixelTriggers returns pixel triggers from active spec
func GetActivePixelTriggers() []PixelTrigger {
	spec := GetActiveSpec()
	if spec == nil {
		return []PixelTrigger{}
	}
	return spec.PixelTriggers
}

// GetActiveBuffTimers returns buff timers from active spec
func GetActiveBuffTimers() []BuffTimer {
	spec := GetActiveSpec()
	if spec == nil {
		return []BuffTimer{}
	}
	return spec.BuffTimers
}

// validate ensures config has all required fields
func validate() {
	if cfg.Games == nil {
		cfg.Games = make(map[string]Game)
	}

	defaults := DefaultConfig().Settings
	for key, val := range defaults {
		if _, ok := cfg.Settings[key]; !ok {
			cfg.Settings[key] = val
		}
	}

	// Ensure each game/class/spec has proper structure
	for name, game := range cfg.Games {
		if game.Classes == nil {
			game.Classes = make(map[string]Class)
		}
		for cname, class := range game.Classes {
			if class.Specs == nil {
				class.Specs = make(map[string]Spec)
			}
			for sname, spec := range class.Specs {
				if spec.Macros == nil {
					spec.Macros = []Macro{}
				}
				if spec.PixelTriggers == nil {
					spec.PixelTriggers = []PixelTrigger{}
				}
				if spec.BuffTimers == nil {
					spec.BuffTimers = []BuffTimer{}
				}
				class.Specs[sname] = spec
			}
			game.Classes[cname] = class
		}
		cfg.Games[name] = game
	}
}
