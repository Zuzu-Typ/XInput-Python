# XInput  
## A simple to use interface to the XInput API for Python\.  
**XInput** provides a few simple methods that can be used to query controller information\.  
  
## Tiny Documentation  
### Using XInput  
XInput provides a few functions:  
`get_connected() -> (bool, bool, bool, bool)` Query which controllers are connected \(note: don't query each frame\)  
  
`get_state(user_index) -> State` Get the State of the controller `user_index`  
  
`get_button_values(state) -> dict` Returns a dictionary, showing which buttons are currently being pressed\.  
  
`get_trigger_values(state) -> (LT, RT)` Returns a tuple with the values of the left and right triggers in range `0.0` to `1.0`  
  
`get_thumb_values(state) -> ((LX, LY), (RX, RY))` Returns the values of the thumb sticks, expressed in X and Y ranging from `0.0` to `1.0`  
  
`set_vibration(user_index, left_speed, right_speed) -> bool (Success)` Sets the vibration of the left and right motors of `user_index` to values between `0` and `65535` or in range `0.0` to `1.0` respectively\.  
  
`get_battery_information(user_index) -> (<type>, <level>)` Returns the battery information for `user_index`