package input

import (
	"fmt"

	"github.com/Luna-onee/gomacrotool/internal/windowsapi"
)

// KeyNameToVK maps key names to virtual key codes
var KeyNameToVK = map[string]uint32{
	// Numbers
	"0": windowsapi.VK_0, "1": windowsapi.VK_1, "2": windowsapi.VK_2, "3": windowsapi.VK_3,
	"4": windowsapi.VK_4, "5": windowsapi.VK_5, "6": windowsapi.VK_6, "7": windowsapi.VK_7,
	"8": windowsapi.VK_8, "9": windowsapi.VK_9,
	// Letters
	"a": windowsapi.VK_A, "b": windowsapi.VK_B, "c": windowsapi.VK_C, "d": windowsapi.VK_D,
	"e": windowsapi.VK_E, "f": windowsapi.VK_F, "g": windowsapi.VK_G, "h": windowsapi.VK_H,
	"i": windowsapi.VK_I, "j": windowsapi.VK_J, "k": windowsapi.VK_K, "l": windowsapi.VK_L,
	"m": windowsapi.VK_M, "n": windowsapi.VK_N, "o": windowsapi.VK_O, "p": windowsapi.VK_P,
	"q": windowsapi.VK_Q, "r": windowsapi.VK_R, "s": windowsapi.VK_S, "t": windowsapi.VK_T,
	"u": windowsapi.VK_U, "v": windowsapi.VK_V, "w": windowsapi.VK_W, "x": windowsapi.VK_X,
	"y": windowsapi.VK_Y, "z": windowsapi.VK_Z,
	// F keys
	"f1": windowsapi.VK_F1, "f2": windowsapi.VK_F2, "f3": windowsapi.VK_F3, "f4": windowsapi.VK_F4,
	"f5": windowsapi.VK_F5, "f6": windowsapi.VK_F6, "f7": windowsapi.VK_F7, "f8": windowsapi.VK_F8,
	"f9": windowsapi.VK_F9, "f10": windowsapi.VK_F10, "f11": windowsapi.VK_F11, "f12": windowsapi.VK_F12,
	// Special keys
	"tab": windowsapi.VK_TAB, "enter": windowsapi.VK_RETURN, "escape": windowsapi.VK_ESCAPE,
	"backspace": windowsapi.VK_BACK, "space": windowsapi.VK_SPACE,
	"delete": windowsapi.VK_DELETE, "insert": windowsapi.VK_INSERT,
	"home": windowsapi.VK_HOME, "end": windowsapi.VK_END,
	"pgup": windowsapi.VK_PRIOR, "pgdn": windowsapi.VK_NEXT,
	"up": windowsapi.VK_UP, "down": windowsapi.VK_DOWN,
	"left": windowsapi.VK_LEFT, "right": windowsapi.VK_RIGHT,
	"shift": windowsapi.VK_SHIFT, "ctrl": windowsapi.VK_CONTROL, "alt": windowsapi.VK_MENU,
	"capslock": windowsapi.VK_CAPITAL, "numlock": windowsapi.VK_NUMLOCK, "scrolllock": windowsapi.VK_SCROLL,
	"pause": windowsapi.VK_PAUSE, "printscreen": windowsapi.VK_PRINT,
	// Numpad
	"numpad0": windowsapi.VK_NUMPAD0, "numpad1": windowsapi.VK_NUMPAD1, "numpad2": windowsapi.VK_NUMPAD2,
	"numpad3": windowsapi.VK_NUMPAD3, "numpad4": windowsapi.VK_NUMPAD4, "numpad5": windowsapi.VK_NUMPAD5,
	"numpad6": windowsapi.VK_NUMPAD6, "numpad7": windowsapi.VK_NUMPAD7, "numpad8": windowsapi.VK_NUMPAD8,
	"numpad9": windowsapi.VK_NUMPAD9, "numpadadd": windowsapi.VK_ADD,
	"numpadsub": windowsapi.VK_SUBTRACT, "numpadmult": windowsapi.VK_MULTIPLY,
	"numpaddiv": windowsapi.VK_DIVIDE, "numpadenter": windowsapi.VK_RETURN,
	// Mouse
	"lbutton": windowsapi.VK_LBUTTON, "rbutton": windowsapi.VK_RBUTTON,
	"mbutton": windowsapi.VK_MBUTTON, "xbutton1": windowsapi.VK_XBUTTON1, "xbutton2": windowsapi.VK_XBUTTON2,
}

// SendKey sends a key press (down + up)
func SendKey(keyName string) {
	vk, ok := KeyNameToVK[keyName]
	if !ok {
		return
	}

	if IsMouseButton(keyName) {
		inputs := []windowsapi.INPUT{
			windowsapi.MakeMouseInput(keyName, false),
			windowsapi.MakeMouseInput(keyName, true),
		}
		windowsapi.SendInput(inputs)
		return
	}

	inputs := []windowsapi.INPUT{
		windowsapi.MakeKeyInput(vk, false),
		windowsapi.MakeKeyInput(vk, true),
	}
	windowsapi.SendInput(inputs)
}

// SendKeyDown sends just the key down event
func SendKeyDown(keyName string) {
	vk, ok := KeyNameToVK[keyName]
	if !ok {
		return
	}

	if IsMouseButton(keyName) {
		windowsapi.SendInput([]windowsapi.INPUT{windowsapi.MakeMouseInput(keyName, false)})
		return
	}

	windowsapi.SendInput([]windowsapi.INPUT{windowsapi.MakeKeyInput(vk, false)})
}

// SendKeyUp sends just the key up event
func SendKeyUp(keyName string) {
	vk, ok := KeyNameToVK[keyName]
	if !ok {
		return
	}

	if IsMouseButton(keyName) {
		windowsapi.SendInput([]windowsapi.INPUT{windowsapi.MakeMouseInput(keyName, true)})
		return
	}

	windowsapi.SendInput([]windowsapi.INPUT{windowsapi.MakeKeyInput(vk, true)})
}

// SendKeyBatch sends multiple keys in sequence
func SendKeyBatch(keys []string) {
	inputs := make([]windowsapi.INPUT, 0, len(keys)*2)

	for i, key := range keys {
		vk, ok := KeyNameToVK[key]
		if !ok {
			continue
		}

		if IsMouseButton(key) {
			inputs = append(inputs,
				windowsapi.MakeMouseInput(key, false),
				windowsapi.MakeMouseInput(key, true),
			)
		} else {
			inputs = append(inputs,
				windowsapi.MakeKeyInput(vk, false),
				windowsapi.MakeKeyInput(vk, true),
			)
		}
	}

	if len(inputs) > 0 {
		windowsapi.SendInput(inputs)
	}
}

// ParseHotkey parses AHK-style hotkey (e.g., "^+a" for Ctrl+Shift+A)
func ParseHotkey(hotkey string) []string {
	mods := ""
	key := ""

	for i := 0; i < len(hotkey); i++ {
		ch := hotkey[i]
		if ch == '^' || ch == '!' || ch == '+' || ch == '#' {
			mods += string(ch)
		} else {
			key = hotkey[i:]
			break
		}
	}

	// Convert modifiers to key names
	result := []string{}
	for _, m := range mods {
		switch m {
		case '^':
			result = append(result, "ctrl")
		case '!':
			result = append(result, "alt")
		case '+':
			result = append(result, "shift")
		case '#':
			result = append(result, "windows")
		}
	}

	if key != "" {
		result = append(result, key)
	}

	return result
}

// IsMouseButton checks if a key name is a mouse button
func IsMouseButton(keyName string) bool {
	mouseButtons := []string{"lbutton", "rbutton", "mbutton", "xbutton1", "xbutton2"}
	for _, mb := range mouseButtons {
		if keyName == mb {
			return true
		}
	}
	return false
}

// VKToKeyName maps virtual key codes back to key names
func VKToKeyName(vk uint32) string {
	for name, code := range KeyNameToVK {
		if code == vk {
			return name
		}
	}
	return fmt.Sprintf("0x%02X", vk)
}
