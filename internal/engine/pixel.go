package engine

import (
	"runtime"
	"sync"
	"time"

	"github.com/Luna-onee/gomacrotool/internal/config"
	"github.com/Luna-onee/gomacrotool/internal/windowsapi"
)

// PixelEngineImpl manages pixel trigger polling
type PixelEngineImpl struct {
	stopChan  chan struct{}
	mu        sync.RWMutex
	triggers  []*PixelTriggerState
	checkRate time.Duration
	lastCheck time.Time
}

// PixelTriggerState tracks runtime state for a pixel trigger
type PixelTriggerState struct {
	Trigger     *config.PixelTrigger
	LastFired   time.Time
	Scaled      []config.Pixel
	CachedSpec  string // Resolution cache key
}

var (
	running       bool
	sendingGuard  bool // Guard: skip pixel checks during key sends
	pixelMu      sync.RWMutex
)

// Setup initializes pixel engine with triggers from active spec
func (p *PixelEngineImpl) Setup(triggers []config.PixelTrigger) {
	p.mu.Lock()
	defer p.mu.Unlock()

	states := make([]*PixelTriggerState, 0, len(triggers))
	for _, t := range triggers {
		states = append(states, &PixelTriggerState{
			Trigger:   &t,
			LastFired: time.Time{},
			Scaled:    nil,
			CachedSpec: "",
		})
	}

	p.triggers = states

	checkRateMs := config.Get().Settings.PixelCheckRate
	if checkRateMs < 10 {
		checkRateMs = 10
	} else if checkRateMs > 1000 {
		checkRateMs = 1000
	}
	p.checkRate = time.Duration(1000/checkRateMs) * time.Millisecond
}

// Start begins pixel polling loop
func (p *PixelEngineImpl) Start() {
	p.mu.RLock()
	hasTriggers := len(p.triggers) > 0
	p.mu.RUnlock()

	if !hasTriggers {
		return
	}

	pixelMu.Lock()
	running = true
	pixelMu.Unlock()

	go p.pollLoop()
}

// Stop halts pixel polling
func (p *PixelEngineImpl) Stop() {
	close(p.stopChan)

	pixelMu.Lock()
	running = false
	pixelMu.Unlock()
}

// SetSendingGuard sets the guard flag
func (p *PixelEngineImpl) SetSendingGuard(sending bool) {
	pixelMu.Lock()
	defer pixelMu.Unlock()
	sendingGuard = sending
}

// IsRunning returns if pixel engine is active
func (p *PixelEngineImpl) IsRunning() bool {
	pixelMu.RLock()
	defer pixelMu.RUnlock()
	return running
}

func (p *PixelEngineImpl) pollLoop() {
	// Lock thread for Windows calls
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()

	ticker := time.NewTicker(p.checkRate)
	defer ticker.Stop()

	for {
		select {
		case <-p.stopChan:
			return
		case <-ticker.C:
			p.check()
		}
	}
}

func (p *PixelEngineImpl) check() {
	// Guard: skip during input sends
	pixelMu.RLock()
	if sendingGuard {
		pixelMu.RUnlock()
		return
	}

	// Check game active
	if !GameDetector.IsActive() {
		pixelMu.RUnlock()
		return
	}
	pixelMu.RUnlock()

	// Get screen DC
	hdc := windowsapi.GetDC()
	if hdc == 0 {
		return
	}
	defer windowsapi.ReleaseDC(hdc)

	// Get current resolution
	resW, resH := windowsapi.GetScreenResolution()
	currentRes := config.Resolution{W: resW, H: resH}

	now := time.Now().UnixMilli()

	p.mu.RLock()
	triggers := make([]*PixelTriggerState, len(p.triggers))
	copy(triggers, p.triggers)
	p.mu.RUnlock()

	for _, state := range triggers {
		t := state.Trigger
		if !t.Enabled {
			continue
		}

		// Cooldown check
		if now-state.LastFired.UnixMilli() < int64(t.Cooldown) {
			continue
		}

		// Trigger mode: "macro" or "always"
		if t.TriggerMode == "macro" {
			mhk := t.MacroHotkey
			anyRunning := MacroEngine.IsAnyRunning()
			if mhk == "" && !anyRunning {
				continue
			}
			if mhk != "" && !MacroEngine.IsRunning(mhk) {
				continue
			}
		}

		// Scale pixels if resolution changed
		if state.CachedSpec != currentRes.String() || state.Scaled == nil {
			state.Scaled = scalePixels(t.Pixels, t.CaptureRes, currentRes)
			state.CachedSpec = currentRes.String()
		}

		// Check anchor first
		if t.Anchor != nil {
			scaledAnchor := scalePixels(t.Anchor.Pixels, t.CaptureRes, currentRes)
			if !checkPixels(hdc, scaledAnchor, t.Anchor.MatchMode) {
				continue // Anchor not matched
			}
		}

		// Check blocker
		if t.Blocker != nil {
			scaledBlocker := scalePixels(t.Blocker.Pixels, t.CaptureRes, currentRes)
			if checkPixels(hdc, scaledBlocker, t.Blocker.MatchMode) {
				continue // Blocker matched, skip trigger
			}
		}

		// Check trigger pixels
		matched := checkPixels(hdc, state.Scaled, t.MatchMode)
		if t.Inverse {
			matched = !matched
		}

		if matched {
			state.LastFired = time.Now()
			if t.ActionKey != "" {
				input.SendKey(t.ActionKey)
			}
		}
	}
}

func checkPixels(hdc uintptr, pixels []config.Pixel, matchMode string) bool {
	if len(pixels) == 0 {
		return false
	}

	if matchMode == "all" {
		for _, px := range pixels {
			color := windowsapi.GetPixel(hdc, px.X, px.Y)
			if !colorMatch(color, px.Color, px.Variation) {
				return false
			}
		}
		return true
	} else { // "any"
		for _, px := range pixels {
			color := windowsapi.GetPixel(hdc, px.X, px.Y)
			if colorMatch(color, px.Color, px.Variation) {
				return true
			}
		}
		return false
	}
}

func colorMatch(found uint32, expected string, variation int32) bool {
	// Parse hex color to RGB
	exp := parseHexColor(expected)

	r := found & 0xFF
	g := (found >> 8) & 0xFF
	b := (found >> 16) & 0xFF

	return (abs(int(r)-exp.R) <= variation) &&
		abs(int(g)-exp.G) <= variation) &&
		abs(int(b)-exp.B) <= variation)
}

func parseHexColor(hexStr string) RGB {
	if len(hexStr) < 3 {
		return RGB{0, 0, 0}
	}

	// Remove 0x prefix
	if len(hexStr) >= 2 && hexStr[0:2] == "0x" {
		hexStr = hexStr[2:]
	}

	// Parse as integer
	var val int32
	if len(hexStr) <= 2 {
		fmt.Sscanf(hexStr, "%x", &val)
	} else if len(hexStr) <= 4 {
		fmt.Sscanf(hexStr, "%x", &val)
	} else {
		fmt.Sscanf(hexStr, "%x", &val)
	}

	return RGB{
		R: int32((val >> 16) & 0xFF),
		G: int32((val >> 8) & 0xFF),
		B: int32(val & 0xFF),
	}
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

func scalePixels(pixels []config.Pixel, captureRes, currentRes *config.Resolution) []config.Pixel {
	if captureRes == nil || currentRes == nil {
		return pixels
	}

	if captureRes.W == 0 || captureRes.H == 0 ||
		currentRes.W == 0 || currentRes.H == 0 {
		return pixels
	}

	if captureRes.W == currentRes.W && captureRes.H == currentRes.H {
		return pixels
	}

	rx := float64(currentRes.W) / float64(captureRes.W)
	ry := float64(currentRes.H) / float64(captureRes.H)

	scaled := make([]config.Pixel, len(pixels))
	for i, px := range pixels {
		scaled[i] = config.Pixel{
			X:         int32(float64(px.X) * rx + 0.5),
			Y:         int32(float64(px.Y) * ry + 0.5),
			Color:      px.Color,
			Variation:  px.Variation,
		}
	}

	return scaled
}

// String returns string representation of resolution
func (r *config.Resolution) String() string {
	return fmt.Sprintf("%dx%d", r.W, r.H)
}
