package engine

import (
	"container/heap"
	"sync"
	"time"

	"github.com/Luna-onee/gomacrotool/internal/config"
)

var (
	// BuffEngine singleton
	BuffEngine = &BuffEngineImpl{
		entries: make(map[string]*BuffEntry),
		heap:     make([]*BuffEntry, 0),
	}

	// MacroEngine singleton
	MacroEngine = &MacroEngineImpl{
		running:      make(map[string]bool),
		stopFlags:    make(map[string]*StopFlag),
		macrosPaused: true,
		enabled:      true,
		gameActive:   true,
		sendLock:     &sync.Mutex{},
	}

	// PixelEngine singleton
	PixelEngine = &PixelEngineImpl{
		stopChan:     make(chan struct{}),
		checkRate:    250, // Hz
		lastCheck:    time.Now(),
	}

	// GameDetector singleton
	GameDetector = &GameDetectorImpl{
		active:       false,
		foregroundPID: 0,
		stopChan:     make(chan struct{}),
	}
)

// BuffEntry represents a buff timer entry
type BuffEntry struct {
	Name       string
	Gen        int64
	ExpireTime time.Time
	StartTime  time.Time
	Duration   time.Duration
	Buff       *config.BuffTimer
	Cancelled  bool
	Index      int // Heap index
}

// StopFlag is a thread-safe stop flag
type StopFlag struct {
	flag int32
	mu   sync.RWMutex
}

// BuffEngineImpl manages buff countdown timers
type BuffEngineImpl struct {
	mu         sync.RWMutex
	heap       []*BuffEntry
	entries    map[string]*BuffEntry
	heapMu     sync.Mutex
	genCounter int64
	callbacks   []BuffCallback
	workerChan chan struct{}
	stopChan   chan struct{}
}

// BuffCallback is called when buff state changes
type BuffCallback func(event string, buffName string, detail map[string]interface{})

// RegisterCallback adds a buff event callback
func (b *BuffEngineImpl) RegisterCallback(cb BuffCallback) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.callbacks = append(b.callbacks, cb)
}

// Activate starts or refreshes a buff timer
func (b *BuffEngineImpl) Activate(buff *config.BuffTimer) {
	b.mu.Lock()
	defer b.mu.Unlock()

	name := buff.Name
	now := time.Now()
	duration := time.Duration(buff.Duration) * time.Millisecond
	expireTime := now.Add(duration)

	b.genCounter++
	gen := b.genCounter

	// Check for existing entry
	existing, ok := b.entries[name]
	if ok {
		switch buff.OnRefresh {
		case "ignore":
			return
		case "extend":
			remaining := existing.ExpireTime.Sub(now)
			if remaining < 0 {
				remaining = 0
			}
			extendMs := time.Duration(buff.ExtendMs) * time.Millisecond
			expireTime = now.Add(remaining + extendMs)
		default: // "reset"
			// Just overwrite
		}

		existing.Cancelled = true
	}

	b.entries[name] = &BuffEntry{
		Name:       name,
		Gen:        gen,
		ExpireTime: expireTime,
		StartTime:  now,
		Duration:   duration,
		Buff:       buff,
		Cancelled:  false,
	}

	// Push to heap
	b.heapMu.Lock()
	heap.Push(b, &BuffEntry{
		Name:       name,
		Gen:        gen,
		ExpireTime: expireTime,
		StartTime:  now,
		Duration:   duration,
		Buff:       buff,
		Cancelled:  false,
	})
	b.heapMu.Unlock()

	// Notify worker
	select {
	case b.workerChan <- struct{}{}:
	default:
	}
}

// GetTimerInfo returns timer information for all active buffs
func (b *BuffEngineImpl) GetTimerInfo() map[string]TimerInfo {
	b.mu.RLock()
	defer b.mu.RUnlock()

	result := make(map[string]TimerInfo)
	for name, entry := range b.entries {
		if entry.Cancelled {
			continue
		}

		now := time.Now()
		elapsed := now.Sub(entry.StartTime)
		remaining := entry.ExpireTime.Sub(now)
		if remaining < 0 {
			remaining = 0
		}

		var progress float64
		if entry.Duration > 0 {
			progress = float64(elapsed) / float64(entry.Duration)
		}

		result[name] = TimerInfo{
			Remaining: int64(remaining / time.Millisecond),
			Duration:  int64(entry.Duration / time.Millisecond),
			Elapsed:   int64(elapsed / time.Millisecond),
			Progress:  progress,
		}
	}

	return result
}

// ClearAll removes all active timers
func (b *BuffEngineImpl) ClearAll() {
	b.mu.Lock()
	defer b.mu.Unlock()

	for name, entry := range b.entries {
		entry.Cancelled = true
	}

	b.entries = make(map[string]*BuffEntry)
	b.heapMu.Lock()
	b.heap = make([]*BuffEntry, 0)
	b.heapMu.Unlock()
}

// Stop shuts down the buff engine
func (b *BuffEngineImpl) Stop() {
	close(b.stopChan)
}

// Worker runs timer expiration loop
func (b *BuffEngineImpl) Worker() {
	for {
		select {
		case <-b.stopChan:
			return
		case <-b.workerChan:
			b.processExpired()
		case <-time.After(time.Second):
			b.processExpired()
		}
	}
}

func (b *BuffEngineImpl) processExpired() {
	b.heapMu.Lock()
	defer b.heapMu.Unlock()

	now := time.Now()
	for len(b.heap) > 0 {
		entry := b.heap[0]
		if entry.ExpireTime.After(now) {
			break
		}

		// Pop from heap
		heap.Pop(b)

		b.mu.RLock()
		dbEntry, ok := b.entries[entry.Name]
		b.mu.RUnlock()

		if ok && dbEntry.Gen == entry.Gen && !dbEntry.Cancelled {
			delete(b.entries, entry.Name)
			b.notify("expired", entry.Name, map[string]interface{}{
				"actionKey": entry.Buff.ActionKey,
			})
		}
	}
}

func (b *BuffEngineImpl) notify(event string, buffName string, detail map[string]interface{}) {
	for _, cb := range b.callbacks {
		cb(event, buffName, detail)
	}
}

// TimerInfo holds timer state
type TimerInfo struct {
	Remaining int64   `json:"remaining"`
	Duration  int64   `json:"duration"`
	Elapsed   int64   `json:"elapsed"`
	Progress  float64 `json:"progress"`
}

// Heap implementation
func (b *BuffEngineImpl) Len() int {
	return len(b.heap)
}

func (b *BuffEngineImpl) Less(i, j int) bool {
	return b.heap[i].ExpireTime.Before(b.heap[j].ExpireTime)
}

func (b *BuffEngineImpl) Swap(i, j int) {
	b.heap[i], b.heap[j] = b.heap[j], b.heap[i]
	b.heap[i].Index = i
	b.heap[j].Index = j
}

func (b *BuffEngineImpl) Push(x interface{}) {
	n := len(b.heap)
	entry := x.(*BuffEntry)
	entry.Index = n
	b.heap = append(b.heap, entry)
	b.up(n)
}

func (b *BuffEngineImpl) Pop() interface{} {
	n := len(b.heap) - 1
	entry := b.heap[n]
	b.heap[n] = nil // avoid memory leak
	b.heap = b.heap[:n]

	if n > 0 {
		b.heap[0].Index = 0
		b.down(0)
	}

	return entry
}

func (b *BuffEngineImpl) up(j int) {
	for {
		i := (j - 1) / 2
		if i == j || b.Less(i, j) {
			break
		}
		b.Swap(i, j)
		j = i
	}
}

func (b *BuffEngineImpl) down(j int) {
	n := len(b.heap)
	for {
		i1 := 2*j + 1
		if i1 >= n || i1 < 0 {
			i1 = -1
		}
		i2 := i1 + 1
		if i2 >= n || i2 < 0 {
			i2 = -1
		}

		if i1 >= 0 && b.Less(i1, j) {
			// j -> i1
			b.Swap(i1, j)
			j = i1
		} else if i2 >= 0 && b.Less(i2, j) {
			// j -> i2
			b.Swap(i2, j)
			j = i2
		} else {
			return
		}
	}
}
