import ctypes, ctypes.util

from ctypes import Structure, POINTER

from math import sqrt

import time

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
ERROR_BAD_ARGUMENTS = 160
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


_last_states = (State(), State(), State(), State())

_last_norm_values = [None, None, None, None]

_connected = [False, False, False, False]

_last_checked = 0

class XInputNotConnectedError(Exception):
    pass

class XInputBadArgumentError(ValueError):
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

    if res == ERROR_BAD_ARGUMENTS:
        raise XInputBadArgumentError("Controller [{}] doesn't exist. IDs range from 0 to 3.".format(user_index))
    
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
        normLT = LT / (255. - XINPUT_GAMEPAD_TRIGGER_THRESHOLD)
    else:
        LT = 0

    if RT > XINPUT_GAMEPAD_TRIGGER_THRESHOLD:
        RT -= XINPUT_GAMEPAD_TRIGGER_THRESHOLD
        normRT = RT / (255. - XINPUT_GAMEPAD_TRIGGER_THRESHOLD)
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

        normMagL = magL / (32767. - XINPUT_GAMEPAD_LEFT_THUMB_DEADZONE)
    else:
        magL = 0

    if (magR > XINPUT_GAMEPAD_RIGHT_THUMB_DEADZONE):
        magR = min(32767, magR)

        magR -= XINPUT_GAMEPAD_RIGHT_THUMB_DEADZONE

        normMagR = magR / (32767. - XINPUT_GAMEPAD_RIGHT_THUMB_DEADZONE)
    else:
        magR = 0

    return ((normLX * normMagL, normLY * normMagL), (normRX * normMagR, normRY * normMagR))


_button_dict = {0x0001 : "DPAD_UP",
            0x0002 : "DPAD_DOWN",
            0x0004 : "DPAD_LEFT",
            0x0008 : "DPAD_RIGHT",
            0x0010 : "START",
            0x0020 : "BACK",
            0x0040 : "LEFT_THUMB",
            0x0080 : "RIGHT_THUMB",
            0x0100 : "LEFT_SHOULDER",
            0x0200 : "RIGHT_SHOULDER",
            0x1000 : "A",
            0x2000 : "B",
            0x4000 : "X",
            0x8000 : "Y",
        }

EVENT_CONNECTED = 1
EVENT_DISCONNECTED = 2
EVENT_BUTTON_PRESSED = 3
EVENT_BUTTON_RELEASED = 4
EVENT_TRIGGER_MOVED = 5
EVENT_STICK_MOVED = 6

LEFT = 0
RIGHT = 1

class Event:
    def __init__(self, user_index, type_):
        self.user_index = user_index
        self.type = type_

    def __str__(self):
        return str(self.__dict__)
        
def get_events():
    global _last_states, _connected, _last_checked, _button_dict, _last_norm_values
    this_time = time.time()
    these_states = (State(), State(), State(), State())
    if _last_checked + 1 < this_time:
        _last_checked = this_time
        for i in range(4):
            is_connected = (XInputGetState(i, these_states[i]) == 0)
            if is_connected != _connected[i]:
                yield Event(i, EVENT_CONNECTED if is_connected else EVENT_DISCONNECTED)
                _connected[i] = is_connected
    else:
        for i in range(4):
            was_connected = _connected[i]
            if not was_connected:
                continue
            is_connected = (XInputGetState(i, these_states[i]) == 0)

            if not is_connected:
                yield Event(i, EVENT_DISCONNECTED)
                _connected[i] = False
                continue

    for i in range(4):
        is_connected = _connected[i]
        if not is_connected: continue

        if these_states[i].Gamepad.wButtons != _last_states[i].Gamepad.wButtons:
            changed = these_states[i].Gamepad.wButtons ^ _last_states[i].Gamepad.wButtons
            if changed:
                for button in _button_dict:
                    if changed & button:
                        event = Event(i, EVENT_BUTTON_PRESSED if changed & button & these_states[i].Gamepad.wButtons else EVENT_BUTTON_RELEASED)
                        event.button = _button_dict[button]
                        event.button_id = button
                        yield event

        if these_states[i].Gamepad.bLeftTrigger != _last_states[i].Gamepad.bLeftTrigger:
            LT = these_states[i].Gamepad.bLeftTrigger

            normLT = 0

            if LT > XINPUT_GAMEPAD_TRIGGER_THRESHOLD:
                LT -= XINPUT_GAMEPAD_TRIGGER_THRESHOLD
                normLT = LT / (255. - XINPUT_GAMEPAD_TRIGGER_THRESHOLD)
            else:
                LT = 0

            if normLT != _last_norm_values[0]:
                event = Event(i, EVENT_TRIGGER_MOVED)
                event.trigger = LEFT
                event.value = normLT
                yield event

            _last_norm_values[0] = normLT

        if these_states[i].Gamepad.bRightTrigger != _last_states[i].Gamepad.bRightTrigger:
            RT = these_states[i].Gamepad.bRightTrigger

            normRT = 0

            if RT > XINPUT_GAMEPAD_TRIGGER_THRESHOLD:
                RT -= XINPUT_GAMEPAD_TRIGGER_THRESHOLD
                normRT = RT / (255. - XINPUT_GAMEPAD_TRIGGER_THRESHOLD)
            else:
                RT = 0

            if normRT != _last_norm_values[1]:
                event = Event(i, EVENT_TRIGGER_MOVED)
                event.trigger = RIGHT
                event.value = normRT
                yield event

            _last_norm_values[1] = normRT

        if these_states[i].Gamepad.sThumbLX != _last_states[i].Gamepad.sThumbLX or these_states[i].Gamepad.sThumbLY != _last_states[i].Gamepad.sThumbLY:
            LX = these_states[i].Gamepad.sThumbLX
            LY = these_states[i].Gamepad.sThumbLY

            magL = sqrt(LX*LX + LY*LY)

            normLX = LX / magL
            normLY = LY / magL

            normMagL = 0

            if (magL > XINPUT_GAMEPAD_LEFT_THUMB_DEADZONE):
                magL = min(32767, magL)

                magL -= XINPUT_GAMEPAD_LEFT_THUMB_DEADZONE

                normMagL = magL / (32767. - XINPUT_GAMEPAD_LEFT_THUMB_DEADZONE)
            else:
                magL = 0

            out = (normLX * normMagL, normLY * normMagL)

            if out != _last_norm_values[2]:
                event = Event(i, EVENT_STICK_MOVED)
                event.stick = LEFT
                event.x = out[0]
                event.y = out[1]
                event.value = normMagL
                event.dir = (normLX, normLY) if event.value else (0.0, 0.0)
                yield event

            _last_norm_values[2] = out

        if these_states[i].Gamepad.sThumbRX != _last_states[i].Gamepad.sThumbRX or these_states[i].Gamepad.sThumbRY != _last_states[i].Gamepad.sThumbRY:
            RX = these_states[i].Gamepad.sThumbRX
            RY = these_states[i].Gamepad.sThumbRY

            magR = sqrt(RX*RX + RY*RY)

            normRX = RX / magR
            normRY = RY / magR

            normMagR = 0

            if (magR > XINPUT_GAMEPAD_RIGHT_THUMB_DEADZONE):
                magR = min(32767, magR)

                magR -= XINPUT_GAMEPAD_RIGHT_THUMB_DEADZONE

                normMagR = magR / (32767. - XINPUT_GAMEPAD_RIGHT_THUMB_DEADZONE)
            else:
                magR = 0

            out = (normRX * normMagR, normRY * normMagR)

            if out != _last_norm_values[3]:
                event = Event(i, EVENT_STICK_MOVED)
                event.stick = RIGHT
                event.x = out[0]
                event.y = out[1]
                event.value = normMagR
                event.dir = (normRX, normRY) if event.value else (0.0, 0.0)
                yield event

            _last_norm_values[3] = out

    _last_states = these_states

if __name__ == "__main__":
    try:
        import tkinter as tk
    except ImportError:
        import Tkinter as tk

    root = tk.Tk()
    root.title("XInput")
    canvas = tk.Canvas(root, width= 600, height = 400, bg="white")
    canvas.pack()

    class Controller:
        def __init__(self, center):
            self.center = center

            self.on_indicator_pos = (self.center[0], self.center[1] - 50)

            self.on_indicator = canvas.create_oval(((self.on_indicator_pos[0] - 10, self.on_indicator_pos[1] - 10), (self.on_indicator_pos[0] + 10, self.on_indicator_pos[1] + 10)))
            
            self.r_thumb_pos = (self.center[0] + 50, self.center[1] + 20)

            r_thumb_outline = canvas.create_oval(((self.r_thumb_pos[0] - 25, self.r_thumb_pos[1] - 25), (self.r_thumb_pos[0] + 25, self.r_thumb_pos[1] + 25)))

            r_thumb_stick_pos = self.r_thumb_pos

            self.r_thumb_stick = canvas.create_oval(((r_thumb_stick_pos[0] - 10, r_thumb_stick_pos[1] - 10), (r_thumb_stick_pos[0] + 10, r_thumb_stick_pos[1] + 10)))

            self.l_thumb_pos = (self.center[0] - 100, self.center[1] - 20)

            l_thumb_outline = canvas.create_oval(((self.l_thumb_pos[0] - 25, self.l_thumb_pos[1] - 25), (self.l_thumb_pos[0] + 25, self.l_thumb_pos[1] + 25)))

            l_thumb_stick_pos = self.l_thumb_pos

            self.l_thumb_stick = canvas.create_oval(((l_thumb_stick_pos[0] - 10, l_thumb_stick_pos[1] - 10), (l_thumb_stick_pos[0] + 10, l_thumb_stick_pos[1] + 10)))

            self.l_trigger_pos = (self.center[0] - 120, self.center[1] - 70)

            l_trigger_outline = canvas.create_rectangle(((self.l_trigger_pos[0] - 5, self.l_trigger_pos[1] - 20), (self.l_trigger_pos[0] + 5, self.l_trigger_pos[1] + 20)))

            l_trigger_index_pos = (self.l_trigger_pos[0], self.l_trigger_pos[1] - 20)

            self.l_trigger_index = canvas.create_rectangle(((l_trigger_index_pos[0] - 10, l_trigger_index_pos[1] - 5), (l_trigger_index_pos[0] + 10, l_trigger_index_pos[1] + 5)))

            self.r_trigger_pos = (self.center[0] + 120, self.center[1] - 70)

            r_trigger_outline = canvas.create_rectangle(((self.r_trigger_pos[0] - 5, self.r_trigger_pos[1] - 20), (self.r_trigger_pos[0] + 5, self.r_trigger_pos[1] + 20)))

            r_trigger_index_pos = (self.r_trigger_pos[0], self.r_trigger_pos[1] - 20)

            self.r_trigger_index = canvas.create_rectangle(((r_trigger_index_pos[0] - 10, r_trigger_index_pos[1] - 5), (r_trigger_index_pos[0] + 10, r_trigger_index_pos[1] + 5)))

            buttons_pos = (self.center[0] + 100, self.center[1] - 20)

            A_button_pos = (buttons_pos[0], buttons_pos[1] + 20)

            B_button_pos = (buttons_pos[0] + 20, buttons_pos[1])

            Y_button_pos = (buttons_pos[0], buttons_pos[1] - 20)

            X_button_pos = (buttons_pos[0] - 20, buttons_pos[1])

            self.A_button = canvas.create_oval(((A_button_pos[0] - 10, A_button_pos[1] - 10), (A_button_pos[0] + 10, A_button_pos[1] + 10)))

            self.B_button = canvas.create_oval(((B_button_pos[0] - 10, B_button_pos[1] - 10), (B_button_pos[0] + 10, B_button_pos[1] + 10)))

            self.Y_button = canvas.create_oval(((Y_button_pos[0] - 10, Y_button_pos[1] - 10), (Y_button_pos[0] + 10, Y_button_pos[1] + 10)))

            self.X_button = canvas.create_oval(((X_button_pos[0] - 10, X_button_pos[1] - 10), (X_button_pos[0] + 10, X_button_pos[1] + 10)))

            dpad_pos = (self.center[0] - 50, self.center[1] + 20)

            self.dpad_left = canvas.create_rectangle(((dpad_pos[0] - 30, dpad_pos[1] - 10), (dpad_pos[0] - 10, dpad_pos[1] + 10)), outline = "")

            self.dpad_up = canvas.create_rectangle(((dpad_pos[0] - 10, dpad_pos[1] - 30), (dpad_pos[0] + 10, dpad_pos[1] - 10)), outline = "")

            self.dpad_right = canvas.create_rectangle(((dpad_pos[0] + 10, dpad_pos[1] - 10), (dpad_pos[0] + 30, dpad_pos[1] + 10)), outline = "")

            self.dpad_down = canvas.create_rectangle(((dpad_pos[0] - 10, dpad_pos[1] + 10), (dpad_pos[0] + 10, dpad_pos[1] + 30)), outline = "")

            dpad_outline = canvas.create_polygon(((dpad_pos[0] - 30, dpad_pos[1] - 10), (dpad_pos[0] - 10, dpad_pos[1] - 10), (dpad_pos[0] - 10, dpad_pos[1] - 30), (dpad_pos[0] + 10, dpad_pos[1] - 30),
                                                  (dpad_pos[0] + 10, dpad_pos[1] - 10), (dpad_pos[0] + 30, dpad_pos[1] - 10), (dpad_pos[0] + 30, dpad_pos[1] + 10), (dpad_pos[0] + 10, dpad_pos[1] + 10),
                                                  (dpad_pos[0] + 10, dpad_pos[1] + 30), (dpad_pos[0] - 10, dpad_pos[1] + 30), (dpad_pos[0] - 10, dpad_pos[1] + 10), (dpad_pos[0] - 30, dpad_pos[1] + 10)),
                                                 fill = "", outline = "black")

            back_button_pos = (self.center[0] - 20, self.center[1] - 20)

            self.back_button = canvas.create_oval(((back_button_pos[0] - 5, back_button_pos[1] - 5), (back_button_pos[0] + 5, back_button_pos[1] + 5)))

            start_button_pos = (self.center[0] + 20, self.center[1] - 20)

            self.start_button = canvas.create_oval(((start_button_pos[0] - 5, start_button_pos[1] - 5), (start_button_pos[0] + 5, start_button_pos[1] + 5)))

            l_shoulder_pos = (self.center[0] - 90, self.center[1] - 70)

            self.l_shoulder = canvas.create_rectangle(((l_shoulder_pos[0] - 20, l_shoulder_pos[1] - 5), (l_shoulder_pos[0] + 20, l_shoulder_pos[1] + 10)))

            r_shoulder_pos = (self.center[0] + 90, self.center[1] - 70)

            self.r_shoulder = canvas.create_rectangle(((r_shoulder_pos[0] - 20, r_shoulder_pos[1] - 10), (r_shoulder_pos[0] + 20, r_shoulder_pos[1] + 5)))

    controllers = (Controller((150., 100.)),
                   Controller((450., 100.)),
                   Controller((150., 300.)),
                   Controller((450., 300.)))

    while 1:
        events = get_events()
        for event in events:
            controller = controllers[event.user_index]
            if event.type == EVENT_CONNECTED:
                canvas.itemconfig(controller.on_indicator, fill="light green")
                
            elif event.type == EVENT_DISCONNECTED:
                canvas.itemconfig(controller.on_indicator, fill="")
                
            elif event.type == EVENT_STICK_MOVED:
                if event.stick == LEFT:
                    l_thumb_stick_pos = (int(round(controller.l_thumb_pos[0] + 25 * event.x,0)), int(round(controller.l_thumb_pos[1] - 25 * event.y,0)))
                    canvas.coords(controller.l_thumb_stick, (l_thumb_stick_pos[0] - 10, l_thumb_stick_pos[1] - 10, l_thumb_stick_pos[0] + 10, l_thumb_stick_pos[1] + 10))
                    
                elif event.stick == RIGHT:
                    r_thumb_stick_pos = (int(round(controller.r_thumb_pos[0] + 25 * event.x,0)), int(round(controller.r_thumb_pos[1] - 25 * event.y,0)))
                    canvas.coords(controller.r_thumb_stick, (r_thumb_stick_pos[0] - 10, r_thumb_stick_pos[1] - 10, r_thumb_stick_pos[0] + 10, r_thumb_stick_pos[1] + 10))

            elif event.type == EVENT_TRIGGER_MOVED:
                if event.trigger == LEFT:
                    l_trigger_index_pos = (controller.l_trigger_pos[0], controller.l_trigger_pos[1] - 20 + int(round(40 * event.value, 0)))
                    canvas.coords(controller.l_trigger_index, (l_trigger_index_pos[0] - 10, l_trigger_index_pos[1] - 5, l_trigger_index_pos[0] + 10, l_trigger_index_pos[1] + 5))
                elif event.trigger == RIGHT:
                    r_trigger_index_pos = (controller.r_trigger_pos[0], controller.r_trigger_pos[1] - 20 + int(round(40 * event.value, 0)))
                    canvas.coords(controller.r_trigger_index, (r_trigger_index_pos[0] - 10, r_trigger_index_pos[1] - 5, r_trigger_index_pos[0] + 10, r_trigger_index_pos[1] + 5))

            elif event.type == EVENT_BUTTON_PRESSED:
                if event.button == "LEFT_THUMB":
                    canvas.itemconfig(controller.l_thumb_stick, fill="red")
                elif event.button == "RIGHT_THUMB":
                    canvas.itemconfig(controller.r_thumb_stick, fill="red")

                elif event.button == "LEFT_SHOULDER":
                    canvas.itemconfig(controller.l_shoulder, fill="red")
                elif event.button == "RIGHT_SHOULDER":
                    canvas.itemconfig(controller.r_shoulder, fill="red")

                elif event.button == "BACK":
                    canvas.itemconfig(controller.back_button, fill="red")
                elif event.button == "START":
                    canvas.itemconfig(controller.start_button, fill="red")

                elif event.button == "DPAD_LEFT":
                    canvas.itemconfig(controller.dpad_left, fill="red")
                elif event.button == "DPAD_RIGHT":
                    canvas.itemconfig(controller.dpad_right, fill="red")
                elif event.button == "DPAD_UP":
                    canvas.itemconfig(controller.dpad_up, fill="red")
                elif event.button == "DPAD_DOWN":
                    canvas.itemconfig(controller.dpad_down, fill="red")

                elif event.button == "A":
                    canvas.itemconfig(controller.A_button, fill="red")
                elif event.button == "B":
                    canvas.itemconfig(controller.B_button, fill="red")
                elif event.button == "Y":
                    canvas.itemconfig(controller.Y_button, fill="red")
                elif event.button == "X":
                    canvas.itemconfig(controller.X_button, fill="red")

            elif event.type == EVENT_BUTTON_RELEASED:
                if event.button == "LEFT_THUMB":
                    canvas.itemconfig(controller.l_thumb_stick, fill="")
                elif event.button == "RIGHT_THUMB":
                    canvas.itemconfig(controller.r_thumb_stick, fill="")

                elif event.button == "LEFT_SHOULDER":
                    canvas.itemconfig(controller.l_shoulder, fill="")
                elif event.button == "RIGHT_SHOULDER":
                    canvas.itemconfig(controller.r_shoulder, fill="")

                elif event.button == "BACK":
                    canvas.itemconfig(controller.back_button, fill="")
                elif event.button == "START":
                    canvas.itemconfig(controller.start_button, fill="")

                elif event.button == "DPAD_LEFT":
                    canvas.itemconfig(controller.dpad_left, fill="")
                elif event.button == "DPAD_RIGHT":
                    canvas.itemconfig(controller.dpad_right, fill="")
                elif event.button == "DPAD_UP":
                    canvas.itemconfig(controller.dpad_up, fill="")
                elif event.button == "DPAD_DOWN":
                    canvas.itemconfig(controller.dpad_down, fill="")

                elif event.button == "A":
                    canvas.itemconfig(controller.A_button, fill="")
                elif event.button == "B":
                    canvas.itemconfig(controller.B_button, fill="")
                elif event.button == "Y":
                    canvas.itemconfig(controller.Y_button, fill="")
                elif event.button == "X":
                    canvas.itemconfig(controller.X_button, fill="")
    
        root.update()
    
