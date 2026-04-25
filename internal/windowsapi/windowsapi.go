//go:build windows

package windowsapi

import (
	"syscall"
	"unsafe"
)

// Virtual Key Codes
const (
	VK_LBUTTON    = 0x01
	VK_RBUTTON    = 0x02
	VK_CANCEL     = 0x03
	VK_MBUTTON    = 0x04
	VK_XBUTTON1   = 0x05
	VK_XBUTTON2   = 0x06
	VK_BACK       = 0x08
	VK_TAB        = 0x09
	VK_CLEAR      = 0x0C
	VK_RETURN     = 0x0D
	VK_SHIFT      = 0x10
	VK_CONTROL    = 0x11
	VK_MENU       = 0x12
	VK_PAUSE      = 0x13
	VK_CAPITAL    = 0x14
	VK_ESCAPE     = 0x1B
	VK_SPACE      = 0x20
	VK_PRIOR      = 0x21
	VK_NEXT       = 0x22
	VK_END        = 0x23
	VK_HOME       = 0x24
	VK_LEFT       = 0x25
	VK_UP         = 0x26
	VK_RIGHT      = 0x27
	VK_DOWN       = 0x28
	VK_SELECT     = 0x29
	VK_PRINT      = 0x2A
	VK_EXECUTE    = 0x2B
	VK_SNAPSHOT   = 0x2C
	VK_INSERT     = 0x2D
	VK_DELETE     = 0x2E
	VK_HELP       = 0x2F
	VK_0          = 0x30
	VK_1          = 0x31
	VK_2          = 0x32
	VK_3          = 0x33
	VK_4          = 0x34
	VK_5          = 0x35
	VK_6          = 0x36
	VK_7          = 0x37
	VK_8          = 0x38
	VK_9          = 0x39
	VK_A          = 0x41
	VK_B          = 0x42
	VK_C          = 0x43
	VK_D          = 0x44
	VK_E          = 0x45
	VK_F          = 0x46
	VK_G          = 0x47
	VK_H          = 0x48
	VK_I          = 0x49
	VK_J          = 0x4A
	VK_K          = 0x4B
	VK_L          = 0x4C
	VK_M          = 0x4D
	VK_N          = 0x4E
	VK_O          = 0x4F
	VK_P          = 0x50
	VK_Q          = 0x51
	VK_R          = 0x52
	VK_S          = 0x53
	VK_T          = 0x54
	VK_U          = 0x55
	VK_V          = 0x56
	VK_W          = 0x57
	VK_X          = 0x58
	VK_Y          = 0x59
	VK_Z          = 0x5A
	VK_LWIN       = 0x5B
	VK_RWIN       = 0x5C
	VK_APPS       = 0x5D
	VK_NUMPAD0    = 0x60
	VK_NUMPAD1    = 0x61
	VK_NUMPAD2    = 0x62
	VK_NUMPAD3    = 0x63
	VK_NUMPAD4    = 0x64
	VK_NUMPAD5    = 0x65
	VK_NUMPAD6    = 0x66
	VK_NUMPAD7    = 0x67
	VK_NUMPAD8    = 0x68
	VK_NUMPAD9    = 0x69
	VK_MULTIPLY   = 0x6A
	VK_ADD        = 0x6B
	VK_SEPARATOR  = 0x6C
	VK_SUBTRACT   = 0x6D
	VK_DECIMAL    = 0x6E
	VK_DIVIDE     = 0x6F
	VK_F1         = 0x70
	VK_F2         = 0x71
	VK_F3         = 0x72
	VK_F4         = 0x73
	VK_F5         = 0x74
	VK_F6         = 0x75
	VK_F7         = 0x76
	VK_F8         = 0x77
	VK_F9         = 0x78
	VK_F10        = 0x79
	VK_F11        = 0x7A
	VK_F12        = 0x7B
	VK_NUMLOCK    = 0x90
	VK_SCROLL     = 0x91
)

// Input types
const (
	INPUT_KEYBOARD = 1
	INPUT_MOUSE    = 0

	KEYEVENTF_KEYUP       = 0x0002
	KEYEVENTF_EXTENDEDKEY = 0x0001

	MOUSEEVENTF_LEFTDOWN   = 0x0002
	MOUSEEVENTF_LEFTUP     = 0x0004
	MOUSEEVENTF_RIGHTDOWN  = 0x0008
	MOUSEEVENTF_RIGHTUP    = 0x0010
	MOUSEEVENTF_MIDDLEDOWN  = 0x0020
	MOUSEEVENTF_MIDDLEUP    = 0x0040
	MOUSEEVENTF_XDOWN      = 0x0080
	MOUSEEVENTF_XUP        = 0x0100

	MAPVK_VK_TO_VSC = 0
)

// Messages
const (
	WM_KEYDOWN    = 0x0100
	WM_KEYUP      = 0x0101
	WM_HOTKEY     = 0x0312
	WM_QUIT       = 0x0012
	WM_MOUSEMOVE   = 0x0200
	WM_LBUTTONDOWN = 0x0201
	WM_LBUTTONUP   = 0x0202
	WM_RBUTTONDOWN = 0x0204
	WM_RBUTTONUP   = 0x0205
	WM_MBUTTONDOWN = 0x0208
	WM_MBUTTONUP   = 0x0209
	WM_XBUTTONDOWN = 0x020B
	WM_XBUTTONUP   = 0x020C
)

// Mouse hook
const (
	WH_MOUSE_LL      = 14
	MOD_NOREPEAT     = 0x4000
	XBUTTON1         = 1
	XBUTTON2         = 2
)

// GDI32
const (
	SRCCOPY = 0x00CC0020
)

// Structures
type (
	KEYBDINPUT struct {
		WVk         uint16
		WScan       uint16
		DwFlags     uint32
		Time        uint32
		DwExtraInfo uintptr
	}

	MOUSEINPUT struct {
		Dx          int32
		Dy          int32
		MouseData    uint32
		DwFlags     uint32
		Time         uint32
		DwExtraInfo uintptr
	}

	INPUT_UNION struct {
		Ki KEYBDINPUT
		Mi MOUSEINPUT
	}

	INPUT struct {
		Type uint32
		U    INPUT_UNION
	}

	POINT struct {
		X int32
		Y int32
	}

	MSG struct {
		Hwnd    uintptr
		Message uint32
		WParam  uintptr
		LParam  uintptr
		Time    uint32
		Pt      POINT
	}
)

// DLL functions
var (
	user32              = syscall.NewLazyDLL("user32.dll")
	procSendInput        = user32.NewProc("SendInput")
	procMapVirtualKey    = user32.NewProc("MapVirtualKeyW")
	procGetDC            = user32.NewProc("GetDC")
	procReleaseDC        = user32.NewProc("ReleaseDC")
	procGetPixel         = user32.NewProc("GetPixel")
	procGetSystemMetrics = user32.NewProc("GetSystemMetrics")
	procRegisterHotKey   = user32.NewProc("RegisterHotKey")
	procUnregisterHotKey = user32.NewProc("UnregisterHotKey")
	procSetWindowsHookEx = user32.NewProc("SetWindowsHookExW")
	procUnhookWindowsHookEx = user32.NewProc("UnhookWindowsHookEx")
	procCallNextHookEx  = user32.NewProc("CallNextHookEx")
	procGetMessageW     = user32.NewProc("GetMessageW")
	procPostMessageW     = user32.NewProc("PostMessageW")
	procGetForegroundWindow = user32.NewProc("GetForegroundWindow")
	procGetWindowThreadProcessId = user32.NewProc("GetWindowThreadProcessId")
	procGetCursorPos    = user32.NewProc("GetCursorPos")
	procSetCursorPos    = user32.NewProc("SetCursorPos")

	kernel32            = syscall.NewLazyDLL("kernel32.dll")
	procGetModuleHandle  = kernel32.NewProc("GetModuleHandleW")
	procGetCurrentThread = kernel32.NewProc("GetCurrentThreadId")
	procQueryPerformanceCounter = kernel32.NewProc("QueryPerformanceCounter")
	procQueryPerformanceFrequency = kernel32.NewProc("QueryPerformanceFrequency")

	gdi32               = syscall.NewLazyDLL("gdi32.dll")
)

// MapVirtualKey converts a virtual key to a scan code
func MapVirtualKey(vk uint32) uint32 {
	ret, _, _ := procMapVirtualKey.Call(uintptr(vk), uintptr(MAPVK_VK_TO_VSC))
	return uint32(ret)
}

// SendInput sends synthetic input events
func SendInput(inputs []INPUT) uint32 {
	if len(inputs) == 0 {
		return 0
	}
	ret, _, _ := procSendInput.Call(
		uintptr(len(inputs)),
		uintptr(unsafe.Pointer(&inputs[0])),
		intptr(unsafe.Sizeof(inputs[0])),
	)
	return uint32(ret)
}

// MakeKeyInput creates a keyboard INPUT struct
func MakeKeyInput(vk uint32, up bool) INPUT {
	input := INPUT{}
	input.Type = INPUT_KEYBOARD
	flags := uint32(0)
	if up {
		flags |= KEYEVENTF_KEYUP
	}

	// Check for extended keys
	if isExtendedKey(vk) {
		flags |= KEYEVENTF_EXTENDEDKEY
	}

	scan := MapVirtualKey(vk)
	input.U.Ki.WVk = uint16(vk)
	input.U.Ki.WScan = uint16(scan)
	input.U.Ki.DwFlags = flags
	input.U.Ki.Time = 0
	input.U.Ki.DwExtraInfo = 0
	return input
}

// MakeMouseInput creates a mouse INPUT struct
func MakeMouseInput(button string, up bool) INPUT {
	input := INPUT{}
	input.Type = INPUT_MOUSE
	var flags uint32
	var mouseData uint32

	switch button {
	case "LButton":
		if up {
			flags = MOUSEEVENTF_LEFTUP
		} else {
			flags = MOUSEEVENTF_LEFTDOWN
		}
	case "RButton":
		if up {
			flags = MOUSEEVENTF_RIGHTUP
		} else {
			flags = MOUSEEVENTF_RIGHTDOWN
		}
	case "MButton":
		if up {
			flags = MOUSEEVENTF_MIDDLEUP
		} else {
			flags = MOUSEEVENTF_MIDDLEDOWN
		}
	case "XButton1":
		if up {
			flags = MOUSEEVENTF_XUP
		} else {
			flags = MOUSEEVENTF_XDOWN
		}
		mouseData = XBUTTON1
	case "XButton2":
		if up {
			flags = MOUSEEVENTF_XUP
		} else {
			flags = MOUSEEVENTF_XDOWN
		}
		mouseData = XBUTTON2
	}

	input.U.Mi.Dx = 0
	input.U.Mi.Dy = 0
	input.U.Mi.MouseData = mouseData
	input.U.Mi.DwFlags = flags
	input.U.Mi.Time = 0
	input.U.Mi.DwExtraInfo = 0
	return input
}

// isExtendedKey checks if a key needs the extended flag
func isExtendedKey(vk uint32) bool {
	extendedKeys := []uint32{
		VK_INSERT, VK_DELETE, VK_HOME, VK_END, VK_PRIOR, VK_NEXT,
		VK_LEFT, VK_UP, VK_RIGHT, VK_DOWN,
		VK_NUMPAD0, VK_NUMPAD1, VK_NUMPAD2, VK_NUMPAD3, VK_NUMPAD4,
		VK_NUMPAD5, VK_NUMPAD6, VK_NUMPAD7, VK_NUMPAD8, VK_NUMPAD9,
		VK_DIVIDE,
	}
	for _, k := range extendedKeys {
		if vk == k {
			return true
		}
	}
	return false
}

// GetPixel returns the color at screen coordinates
func GetPixel(hdc uintptr, x, y int32) uint32 {
	ret, _, _ := procGetPixel.Call(hdc, uintptr(x), uintptr(y))
	return uint32(ret)
}

// GetDC returns the device context for the screen
func GetDC() uintptr {
	ret, _, _ := procGetDC.Call(0)
	return ret
}

// ReleaseDC releases the device context
func ReleaseDC(hdc uintptr) {
	procReleaseDC.Call(0, hdc)
}

// GetSystemMetrics returns system metric values
func GetSystemMetrics(index int32) int32 {
	ret, _, _ := procGetSystemMetrics.Call(uintptr(index))
	return int32(ret)
}

// GetScreenResolution returns current screen resolution
func GetScreenResolution() (width, height int32) {
	width = GetSystemMetrics(0) // SM_CXSCREEN
	height = GetSystemMetrics(1) // SM_CYSCREEN
	return
}

// GetForegroundWindow returns the handle to the foreground window
func GetForegroundWindow() uintptr {
	ret, _, _ := procGetForegroundWindow.Call()
	return ret
}

// GetCursorPos returns the current cursor position
func GetCursorPos() (x, y int32) {
	var pt POINT
	procGetCursorPos.Call(uintptr(unsafe.Pointer(&pt)))
	return pt.X, pt.Y
}

// QueryPerformanceCounter returns the current performance counter value
func QueryPerformanceCounter() int64 {
	var counter int64
	procQueryPerformanceCounter.Call(uintptr(unsafe.Pointer(&counter)))
	return counter
}

// QueryPerformanceFrequency returns the performance counter frequency
func QueryPerformanceFrequency() int64 {
	var frequency int64
	procQueryPerformanceFrequency.Call(uintptr(unsafe.Pointer(&frequency)))
	return frequency
}
