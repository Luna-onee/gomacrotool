package engine

import (
	"container/lru"
	"sync"
	"time"

	"github.com/Luna-onee/gomacrotool/internal/config"
	"github.com/Luna-onee/gomacrotool/internal/windowsapi"
)

// GameDetectorImpl tracks active game window
type GameDetectorImpl struct {
	active       bool
	foregroundPID uint32
	mu           sync.RWMutex
	stopChan     chan struct{}
	procCache    *lru.Cache
}

var (
	gameCallbacks []func(bool)
	gameMu       sync.RWMutex
)

// Setup initializes game detector
func (g *GameDetectorImpl) Setup() {
	g.mu.Lock()
	g.procCache = lru.New(128, nil)
	g.mu.Unlock()
}

// Start begins window checking
func (g *GameDetectorImpl) Start() {
	g.mu.Lock()
	g.stopChan = make(chan struct{})
	g.mu.Unlock()

	go g.checkLoop()
}

// Stop halts window checking
func (g *GameDetectorImpl) Stop() {
	g.mu.Lock()
	defer g.mu.Unlock()

	if g.stopChan != nil {
		close(g.stopChan)
		g.stopChan = nil
	}
}

// RegisterCallback adds a game active change callback
func (g *GameDetectorImpl) RegisterCallback(cb func(bool)) {
	gameMu.Lock()
	defer gameMu.Unlock()
	gameCallbacks = append(gameCallbacks, cb)
}

// IsActive returns if configured game is active
func (g *GameDetectorImpl) IsActive() bool {
	g.mu.RLock()
	defer g.mu.RUnlock()

	settings := config.Get().Settings
	if !settings.OnlyInGame {
		return true
	}
	return g.active
}

// GetForegroundPID returns PID of foreground window
func (g *GameDetectorImpl) GetForegroundPID() uint32 {
	g.mu.RLock()
	defer g.mu.RUnlock()
	return g.foregroundPID
}

func (g *GameDetectorImpl) checkLoop() {
	ticker := time.NewTicker(150 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-g.stopChan:
			return
		case <-ticker.C:
			g.checkForeground()
		}
	}
}

func (g *GameDetectorImpl) checkForeground() {
	g.mu.RLock()
	oldActive := g.active
	oldPID := g.foregroundPID
	g.mu.RUnlock()

	settings := config.Get().Settings
	gameName := settings.ActiveGame
	gameData := config.Get().Games[gameName]

	if gameName == "" || gameData.Path == "" {
		g.mu.Lock()
		g.active = false
		g.foregroundPID = 0
		g.mu.Unlock()

		if oldActive {
			g.notify(false)
		}
		return
	}

	gameExe := extractExeName(gameData.Path)
	fgWindow := windowsapi.GetForegroundWindow()
	fgPID := getWindowPID(fgWindow)

	g.mu.Lock()
	g.foregroundPID = fgPID
	if fgWindow == 0 || fgPID == 0 {
		g.active = false
	} else if fgPID == oldPID {
		// Same process, assume same state
		g.active = oldActive
	} else {
		procPath := g.getProcessPath(fgPID)
		if procPath != "" && extractExeName(procPath) == gameExe {
			g.active = true
		} else {
			g.active = false
		}
	}
	g.mu.Unlock()

	if g.active != oldActive {
		g.notify(g.active)
	}
}

func (g *GameDetectorImpl) getProcessPath(pid uint32) string {
	g.mu.RLock()
	cache := g.procCache
	g.mu.RUnlock()

	// Check cache
	if path, ok := cache.Get(pid); ok {
		if pathStr, ok := path.(string); ok {
			return pathStr
		}
	}

	// TODO: Query actual process path via Windows API
	// For now, return empty to simplify
	return ""
}

func (g *GameDetectorImpl) notify(active bool) {
	gameMu.RLock()
	defer gameMu.RUnlock()

	for _, cb := range gameCallbacks {
		cb(active)
	}
}

func extractExeName(path string) string {
	if len(path) == 0 {
		return ""
	}

	// Get filename from path
	for i := len(path) - 1; i >= 0; i-- {
		if path[i] == '/' || path[i] == '\\' {
			name := path[i+1:]
			// Remove extension
			for j := len(name) - 1; j >= 0; j-- {
				if name[j] == '.' {
					return name[:j]
				}
			}
			return name
		}
	}

	return path
}

func getWindowPID(hwnd uintptr) uint32 {
	// TODO: Implement via GetWindowThreadProcessId
	return 0
}
