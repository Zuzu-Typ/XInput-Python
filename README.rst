
######
XInput
######

********************************************************
A simple to use interface to the XInput API for Python\.
********************************************************
| **XInput** provides a few simple methods that can be used to query controller information\.
| 

Tiny Documentation
==================

Using XInput
------------
| XInput provides a few functions\:
| :code:`get_connected() -> (bool, bool, bool, bool)` Query which controllers are connected \(note\: don\'t query each frame\)
| 
| :code:`get_state(user_index) -> State` Get the State of the controller :code:`user_index`
| 
| :code:`get_button_values(state) -> dict` Returns a dictionary\, showing which buttons are currently being pressed\.
| 
| :code:`get_trigger_values(state) -> (LT, RT)` Returns a tuple with the values of the left and right triggers in range :code:`0.0` to :code:`1.0`
| 
| :code:`get_thumb_values(state) -> ((LX, LY), (RX, RY))` Returns the values of the thumb sticks\, expressed in X and Y ranging from :code:`0.0` to :code:`1.0`
| 
| :code:`set_vibration(user_index, left_speed, right_speed) -> bool (Success)` Sets the vibration of the left and right motors of :code:`user_index` to values between :code:`0` and :code:`65535` or in range :code:`0.0` to :code:`1.0` respectively\.
| 
| :code:`get_battery_information(user_index) -> (<type>, <level>)` Returns the battery information for :code:`user_index`