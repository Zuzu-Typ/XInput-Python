#/usr/bin python3

from XInput import *

if __name__ == "__main__":

    class MyHandler(GamepadEventsHandler):
        def on_button_event(self,event):
            print(event)
        
        def on_stick_event(self, event):
            print(event)

        def on_trigger_event(self, event):
            print(event)

        def on_connection_event(self, event):
            print(event)
    
    handler = MyHandler()
    thread = GamepadThread(handler)
    
    try:
        while(1):
            pass

    except KeyboardInterrupt:
        print("\n--- User exit ---")