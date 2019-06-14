import ctypes, ctypes.util

from ctypes import Structure, POINTER

from math import sqrt

XINPUT_DLL_NAMES = (
    "XInput1_4.dll",
    "XInput9_1_0.dll",
    "XInput1_3.dll",
    "XInput1_2.dll",
    "XInput1_1.dll"
)

libXInput = None

for name in XINPUT_DLL_NAMES:
    found = ctypes.util.find_library(name)
    if found:
        libXInput = ctypes.WinDLL(found)
        break

if not libXInput:
    raise IOError("XInput library was not found.")

WORD = ctypes.c_ushort
BYTE = ctypes.c_ubyte
SHORT = ctypes.c_short
DWORD = ctypes.c_ulong

ERROR_SUCCESS = 0
ERROR_DEVICE_NOT_CONNECTED = 1167

XINPUT_GAMEPAD_LEFT_THUMB_DEADZONE = 7849
XINPUT_GAMEPAD_RIGHT_THUMB_DEADZONE = 8689
XINPUT_GAMEPAD_TRIGGER_THRESHOLD = 30

BATTERY_DEVTYPE_GAMEPAD         = 0x00
BATTERY_TYPE_DISCONNECTED       = 0x00
BATTERY_TYPE_WIRED              = 0x01
BATTERY_TYPE_ALKALINE           = 0x02
BATTERY_TYPE_NIMH               = 0x03
BATTERY_TYPE_UNKNOWN            = 0xFF
BATTERY_LEVEL_EMPTY             = 0x00
BATTERY_LEVEL_LOW               = 0x01
BATTERY_LEVEL_MEDIUM            = 0x02
BATTERY_LEVEL_FULL              = 0x03

_battery_type_dict = {BATTERY_TYPE_DISCONNECTED : "DISCONNECTED",
                      BATTERY_TYPE_WIRED : "WIRED",
                      BATTERY_TYPE_ALKALINE : "ALKALINE",
                      BATTERY_TYPE_NIMH : "NIMH",
                      BATTERY_TYPE_UNKNOWN : "UNKNOWN"}

_battery_level_dict = {BATTERY_LEVEL_EMPTY : "EMPTY",
                       BATTERY_LEVEL_LOW : "LOW",
                       BATTERY_LEVEL_MEDIUM : "MEDIUM",
                       BATTERY_LEVEL_FULL : "FULL"}

class XINPUT_GAMEPAD(Structure):
    _fields_ = [("wButtons", WORD),
                ("bLeftTrigger", BYTE),
                ("bRightTrigger", BYTE),
                ("sThumbLX", SHORT),
                ("sThumbLY", SHORT),
                ("sThumbRX", SHORT),
                ("sThumbRY", SHORT),
                ]

class XINPUT_STATE(Structure):
    _fields_ = [("dwPacketNumber", DWORD),
                ("Gamepad", XINPUT_GAMEPAD),
                ]

State = XINPUT_STATE

class XINPUT_VIBRATION(Structure):
    _fields_ = [("wLeftMotorSpeed", WORD),
                ("wRightMotorSpeed", WORD),
                ]

class XINPUT_BATTERY_INFORMATION(Structure):
    _fields_ = [("BatteryType", BYTE),
                ("BatteryLevel", BYTE),
                ]

libXInput.XInputGetState.argtypes = [DWORD, POINTER(XINPUT_STATE)]
libXInput.XInputGetState.restype = DWORD

def XInputGetState(dwUserIndex, state):
    return libXInput.XInputGetState(dwUserIndex, ctypes.byref(state))

libXInput.XInputSetState.argtypes = [DWORD, POINTER(XINPUT_VIBRATION)]
libXInput.XInputSetState.restype = DWORD

def XInputSetState(dwUserIndex, vibration):
    return libXInput.XInputSetState(dwUserIndex, ctypes.byref(vibration))

libXInput.XInputGetBatteryInformation.argtypes = [DWORD, BYTE, POINTER(XINPUT_BATTERY_INFORMATION)]
libXInput.XInputGetBatteryInformation.restype = DWORD

def XInputGetBatteryInformation(dwUserIndex, devType, batteryInformation):
    return libXInput.XInputGetBatteryInformation(dwUserIndex, devType, ctypes.byref(batteryInformation))


class XInputNotConnectedError(Exception):
    pass

def get_connected():
    state = XINPUT_STATE()
    out = [False] * 4
    for i in range(4):
        out[i] = (XInputGetState(i, state) == 0)

    return tuple(out)

def get_state(user_index):
    state = XINPUT_STATE()
    res = XInputGetState(user_index, state)
    if res == ERROR_DEVICE_NOT_CONNECTED:
        raise XInputNotConnectedError("Controller [{}] appears to be disconnected.".format(user_index))
    
    assert res == 0, "Couldn't get the state of controller [{}]. Is it disconnected?".format(user_index)

    return state

def get_battery_information(user_index):
    battery_information = XINPUT_BATTERY_INFORMATION()
    XInputGetBatteryInformation(user_index, BATTERY_DEVTYPE_GAMEPAD, battery_information)
    return (_battery_type_dict[battery_information.BatteryType], _battery_level_dict[battery_information.BatteryLevel])

def set_vibration(user_index, left_speed, right_speed):
    if type(left_speed) == float and left_speed <= 1.0:
        left_speed = (round(65535 * left_speed, 0))

    if type(right_speed) == float and right_speed <= 1.0:
        right_speed = (round(65535 * right_speed, 0))
        
    vibration = XINPUT_VIBRATION()
    
    vibration.wLeftMotorSpeed = int(left_speed)
    vibration.wRightMotorSpeed = int(right_speed)

    return XInputSetState(user_index, vibration) == 0

def get_button_values(state):
    wButtons = state.Gamepad.wButtons
    return {"DPAD_UP" : bool(wButtons & 0x0001),
            "DPAD_DOWN" : bool(wButtons & 0x0002),
            "DPAD_LEFT" : bool(wButtons & 0x0004),
            "DPAD_RIGHT" : bool(wButtons & 0x0008),
            "START" : bool(wButtons & 0x0010),
            "BACK" : bool(wButtons & 0x0020),
            "LEFT_THUMB" : bool(wButtons & 0x0040),
            "RIGHT_THUMB" : bool(wButtons & 0x0080),
            "LEFT_SHOULDER" : bool(wButtons & 0x0100),
            "RIGHT_SHOULDER" : bool(wButtons & 0x0200),
            "A" : bool(wButtons & 0x1000),
            "B" : bool(wButtons & 0x2000),
            "X" : bool(wButtons & 0x4000),
            "Y" : bool(wButtons & 0x8000),
        }

def get_trigger_values(state):
    LT = state.Gamepad.bLeftTrigger
    RT = state.Gamepad.bRightTrigger

    normLT = 0
    normRT = 0

    if LT > XINPUT_GAMEPAD_TRIGGER_THRESHOLD:
        LT -= XINPUT_GAMEPAD_TRIGGER_THRESHOLD
        normLT = LT / (255 - XINPUT_GAMEPAD_TRIGGER_THRESHOLD)
    else:
        LT = 0

    if RT > XINPUT_GAMEPAD_TRIGGER_THRESHOLD:
        RT -= XINPUT_GAMEPAD_TRIGGER_THRESHOLD
        normRT = RT / (255 - XINPUT_GAMEPAD_TRIGGER_THRESHOLD)
    else:
        RT = 0

    return (normLT, normRT)

def get_thumb_values(state):
    LX = state.Gamepad.sThumbLX
    LY = state.Gamepad.sThumbLY
    RX = state.Gamepad.sThumbRX
    RY = state.Gamepad.sThumbRY

    magL = sqrt(LX*LX + LY*LY)
    magR = sqrt(RX*RX + RY*RY)

    normLX = LX / magL
    normLY = LY / magL
    normRX = RX / magR
    normRY = RY / magR

    normMagL = 0
    normMagR = 0

    if (magL > XINPUT_GAMEPAD_LEFT_THUMB_DEADZONE):
        magL = min(32767, magL)

        magL -= XINPUT_GAMEPAD_LEFT_THUMB_DEADZONE

        normMagL = magL / (32767 - XINPUT_GAMEPAD_LEFT_THUMB_DEADZONE)
    else:
        magL = 0

    if (magR > XINPUT_GAMEPAD_RIGHT_THUMB_DEADZONE):
        magR = min(32767, magR)

        magR -= XINPUT_GAMEPAD_RIGHT_THUMB_DEADZONE

        normMagR = magR / (32767 - XINPUT_GAMEPAD_RIGHT_THUMB_DEADZONE)
    else:
        magR = 0

    return ((normLX * normMagL, normLY * normMagL), (normRX * normMagR, normRY * normMagR))
        
