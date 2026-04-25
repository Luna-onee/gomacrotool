package engine

import (
	"fmt"
	"sync"
	"time"

	"github.com/Luna-onee/gomacrotool/internal/config"
	"github.com/Luna-onee/gomacrotool/internal/input"
	"github.com/Luna-onee/gomacrotool/internal/windowsapi"
)

// MacroEngineImpl manages key macros
type MacroEngineImpl struct {
	running      map[string]bool
	stopFlags    map[string]*StopFlag
	holdThreads  map[string]*HoldThread
	macrosPaused bool
	enabled      bool
	gameActive   bool
	mu           sync.RWMutex
	sendLock     sync.Mutex
	sendingCount int
}

// HoldThread represents a macro hold loop goroutine
type HoldThread struct {
	Macro   *config.Macro
	StopFlag *StopFlag
	Done     chan struct{}
}

// MacroCallback is called when macro state changes
type MacroCallback func()

var (
	macroCallbacks []MacroCallback
)

// RegisterCallback adds a macro state change callback
func (m *MacroEngineImpl) RegisterCallback(cb MacroCallback) {
	m.mu.Lock()
	defer m.mu.Unlock()
	macroCallbacks = append(macroCallbacks, cb)
}

// Setup initializes macro engine with active macros
func (m *MacroEngineImpl) Setup(macros []config.Macro) {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.running = make(map[string]bool)
	m.stopFlags = make(map[string]*StopFlag)
	m.holdThreads = make(map[string]*HoldThread)

	for _, macro := range macros {
		if macro.Hotkey == "" || !macro.Enabled {
			continue
		}

		m.running[macro.Hotkey] = false
		m.stopFlags[macro.Hotkey] = &StopFlag{flag: 0}
		// TODO: Register hotkey here (needs hotkey system)
	}
}

// Cleanup stops all running macros
func (m *MacroEngineImpl) Cleanup() {
	m.mu.Lock()
	defer m.mu.Unlock()

	// Signal all stops
	for _, flag := range m.stopFlags {
		flag.mu.Lock()
		flag.flag = 1
		flag.mu.Unlock()
	}

	// Wait for all threads
	for _, ht := range m.holdThreads {
		if ht != nil && ht.Done != nil {
			close(ht.Done)
		}
	}

	m.running = make(map[string]bool)
	m.stopFlags = make(map[string]*StopFlag)
	m.holdThreads = make(map[string]*HoldThread)
}

// OnKeyDown handles key down event for macro hotkeys
func (m *MacroEngineImpl) OnKeyDown(hotkey string) {
	if !m.IsEnabled() || m.macrosPaused || m.isSending() {
		return
	}

	m.mu.RLock()
	macro := m.getMacroByHotkey(hotkey)
	m.mu.RUnlock()

	if macro == nil {
		return
	}

	if macro.HoldMode {
		m.startHoldLoop(hotkey, macro)
	} else {
		m.sendKeysOnce(macro)
	}
}

// OnKeyUp handles key up event for hold mode macros
func (m *MacroEngineImpl) OnKeyUp(hotkey string) {
	if !m.IsEnabled() || m.macrosPaused {
		// Still send key up to pass through
		input.SendKeyUp(input.VKToKeyName(windowsapi.MapVirtualKey(m.getVKByName(hotkey))))
		return
	}

	m.mu.RLock()
	macro := m.getMacroByHotkey(hotkey)
	m.mu.RUnlock()

	if macro == nil || !macro.HoldMode {
		return
	}

	m.stopHoldLoop(hotkey)
}

// SetPause pauses or resumes all macros
func (m *MacroEngineImpl) SetPause(paused bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.macrosPaused = paused
	m.notify()
}

// SetEnabled enables or disables macro engine
func (m *MacroEngineImpl) SetEnabled(enabled bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.enabled = enabled
	m.notify()
}

// SetGameActive updates game active state
func (m *MacroEngineImpl) SetGameActive(active bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.gameActive = active
	m.notify()
}

// IsEnabled returns if macros are enabled
func (m *MacroEngineImpl) IsEnabled() bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.enabled && (m.gameActive || !config.Get().Settings.OnlyInGame)
}

// GetRunning returns copy of running state
func (m *MacroEngineImpl) GetRunning() map[string]bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	result := make(map[string]bool)
	for k, v := range m.running {
		result[k] = v
	}
	return result
}

// IsSending returns if currently sending keys
func (m *MacroEngineImpl) isSending() bool {
	m.sendLock.Lock()
	defer m.sendLock.Unlock()
	return m.sendingCount > 0
}

func (m *MacroEngineImpl) startHoldLoop(hotkey string, macro *config.Macro) {
	m.mu.Lock()
	if m.running[hotkey] {
		m.mu.Unlock()
		return
	}
	m.running[hotkey] = true

	stopFlag := m.stopFlags[hotkey]
	stopFlag.mu.Lock()
	stopFlag.flag = 0
	stopFlag.mu.Unlock()

	done := make(chan struct{})
	m.holdThreads[hotkey] = &HoldThread{
		Macro:   macro,
		StopFlag: stopFlag,
		Done:     done,
	}
	m.mu.Unlock()

	go func() {
		m.runHoldLoop(macro, stopFlag)
		close(done)
	}()

	m.notify()
}

func (m *MacroEngineImpl) stopHoldLoop(hotkey string) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if ht, ok := m.holdThreads[hotkey]; ok && ht != nil {
		ht.StopFlag.mu.Lock()
		ht.StopFlag.flag = 1
		ht.StopFlag.mu.Unlock()
	}
	m.running[hotkey] = false
	m.notify()
}

func (m *MacroEngineImpl) runHoldLoop(macro *config.Macro, stopFlag *StopFlag) {
	// Thread affinity for last 25% of cores
	setMacroThreadAffinity()

	delay := macro.Delay
	if delay < 1 {
		delay = 1
	}

	ikd := macro.InterKeyDelay

	for {
		stopFlag.mu.RLock()
		shouldStop := stopFlag.flag != 0
		stopFlag.mu.RUnlock()

		if shouldStop {
			break
		}

		// Send key sequence
		m.acquireSending()
		for _, key := range macro.Keys {
			input.SendKey(key)
			if ikd > 0 {
				preciseSleep(time.Duration(ikd) * time.Millisecond)
			}
		}
		m.releaseSending()

		// Delay between sequences
		preciseSleep(time.Duration(delay) * time.Millisecond)
	}
}

func (m *MacroEngineImpl) sendKeysOnce(macro *config.Macro) {
	m.acquireSending()
	defer m.releaseSending()

	for _, key := range macro.Keys {
		input.SendKey(key)
		if macro.InterKeyDelay > 0 {
			preciseSleep(time.Duration(macro.InterKeyDelay) * time.Millisecond)
		}
	}
}

func (m *MacroEngineImpl) acquireSending() {
	m.sendLock.Lock()
	m.sendingCount++
	m.sendLock.Unlock()
}

func (m *MacroEngineImpl) releaseSending() {
	m.sendLock.Lock()
	m.sendingCount--
	if m.sendingCount < 0 {
		m.sendingCount = 0
	}
	m.sendLock.Unlock()
}

func (m *MacroEngineImpl) getMacroByHotkey(hotkey string) *config.Macro {
	spec := config.GetActiveSpec()
	if spec == nil {
		return nil
	}

	for _, macro := range spec.Macros {
		if macro.Hotkey == hotkey {
			return &macro
		}
	}
	return nil
}

func (m *MacroEngineImpl) getVKByName(name string) uint32 {
	for n, vk := range input.KeyNameToVK {
		if n == name {
			return vk
		}
	}
	return 0
}

func (m *MacroEngineImpl) notify() {
	for _, cb := range macroCallbacks {
		cb()
	}
}

// TODO: Add thread affinity function
func setMacroThreadAffinity() {
	// Will implement using runtime.LockOSThread()
}
