import hid
import struct
import time
# [MODIFIED] Import keyboard controller and keys
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController

# --- XboxController class remains unchanged ---
class XboxController:
    BUTTON_MAP = {0:"A1", 1:"A2", 2:"A3", 3:"A4", 4: "A", 5: "B", 6: "X", 7: "Y"}
    BUTTON_MAP_2 = {0:"UP", 1:"DOWN", 2:"LEFT", 3:"RIGHT", 4: "LB", 5: "RB", 6: "LS", 7: "RS"}

    def __init__(self, vendor_id=0x045E, product_id=0x0B12):
        self.device = None
        try:
            self.device = hid.device()
            self.device.open(vendor_id, product_id)
            self.device.set_nonblocking(True)
            print("Connected:", self.device.get_manufacturer_string(), self.device.get_product_string())
        except OSError as e:
            print(f"Error opening device: {e}")
            self.device = None

    def close(self):
        if self.device: self.device.close()

    def read(self):
        if not self.device: return None
        data = self.device.read(64, timeout_ms=1)
        if not data or len(data) < 18: return None
        raw = bytes(data)
        buttons1_raw = raw[4]
        buttons2_raw = raw[5]
        lt, rt = struct.unpack_from("<HH", raw, 6)
        lx, ly, rx, ry = struct.unpack_from("<hhhh", raw, 10)
        buttons = self._decode_buttons(buttons1_raw, self.BUTTON_MAP)
        buttons.update(self._decode_buttons(buttons2_raw, self.BUTTON_MAP_2))
        return {"buttons": buttons, "lt": lt / 1023.0, "rt": rt / 1023.0, "lx": self._normalize_axis(lx), "ly": self._normalize_axis(ly), "rx": self._normalize_axis(rx), "ry": self._normalize_axis(ry)}

    def _decode_buttons(self, bitmask, button_map):
        return {name: bool(bitmask & (1 << bit)) for bit, name in button_map.items()}

    def _normalize_axis(self, v):
        v = int(v)
        if v < 0: return max(-1.0, v / 32768.0)
        else: return min(1.0, v / 32767.0)

# ==============================================================================
# ======================== ACTION HANDLING SYSTEM ==========================
# ==============================================================================

class Action:
    # [MODIFIED] Update the base class signature to include keyboard
    def update(self, state, last_state, mouse, keyboard):
        pass

class MouseMoveAction(Action):
    def __init__(self, x_axis, y_axis, sensitivity, deadzone):
        self.x_axis, self.y_axis, self.sensitivity, self.deadzone = x_axis, y_axis, sensitivity, deadzone

    # [MODIFIED] Update signature
    def update(self, state, last_state, mouse, keyboard):
        lx, ly = state[self.x_axis], state[self.y_axis]
        if abs(lx) < self.deadzone: lx = 0
        if abs(ly) < self.deadzone: ly = 0
        if lx != 0 or ly != 0:
            mouse.move((lx ** 3) * self.sensitivity, -(ly ** 3) * self.sensitivity)

class ClickAction(Action):
    def __init__(self, controller_button, mouse_button):
        self.controller_button, self.mouse_button = controller_button, mouse_button

    # [MODIFIED] Update signature
    def update(self, state, last_state, mouse, keyboard):
        is_pressed = state['buttons'].get(self.controller_button, False)
        was_pressed = last_state['buttons'].get(self.controller_button, False) if last_state else False
        if is_pressed and not was_pressed:
            mouse.press(self.mouse_button)
        elif not is_pressed and was_pressed:
            mouse.release(self.mouse_button)

class ScrollAction(Action):
    def __init__(self, controller_button, scroll_speed, initial_delay, repeat_rate):
        self.controller_button, self.scroll_speed, self.initial_delay, self.repeat_rate = controller_button, scroll_speed, initial_delay, repeat_rate
        self.pressed, self.next_scroll_time = False, 0

    # [MODIFIED] Update signature
    def update(self, state, last_state, mouse, keyboard):
        is_down = state['buttons'].get(self.controller_button, False)
        current_time = time.time()
        if is_down:
            if not self.pressed:
                mouse.scroll(0, self.scroll_speed)
                self.pressed = True
                self.next_scroll_time = current_time + self.initial_delay
            elif current_time >= self.next_scroll_time:
                mouse.scroll(0, self.scroll_speed)
                self.next_scroll_time = current_time + self.repeat_rate
        else:
            self.pressed = False

# ==============================================================================
# ✨✨✨ STEP 1: DEFINE THE NEW KeyboardAction CLASS ✨✨✨
# ==============================================================================
class KeyboardAction(Action):
    """
    Handles mapping a controller button to a keyboard key press (tap).
    Can handle single keys or key combinations with a modifier.
    """
    def __init__(self, controller_button, key, modifier=None):
        self.controller_button = controller_button
        self.key = key
        self.modifier = modifier

    # This is the core logic for the keyboard action
    def update(self, state, last_state, mouse, keyboard):
        is_pressed = state['buttons'].get(self.controller_button, False)
        was_pressed = last_state['buttons'].get(self.controller_button, False) if last_state else False

        # Trigger only on the initial press down
        if is_pressed and not was_pressed:
            if self.modifier:
                # If a modifier key is specified, press it, tap the main key, then release it
                with keyboard.pressed(self.modifier):
                    keyboard.tap(self.key)
            else:
                # If no modifier, just tap the main key
                keyboard.tap(self.key)

# ==============================================================================

if __name__ == "__main__":
    # --------------------------------------------------------------------------
    # --- ✨✨✨ STEP 4: ADD YOUR NEW ACTION TO THE CONFIGURATION ✨✨✨ ---
    # --------------------------------------------------------------------------
    ACTION_CONFIG = [
        MouseMoveAction(x_axis='lx', y_axis='ly', sensitivity=25, deadzone=0.15),
        
        ClickAction(controller_button='A', mouse_button=Button.left),
        ClickAction(controller_button='B', mouse_button=Button.right),

        ScrollAction(controller_button='RB', scroll_speed=-15, initial_delay=0.3, repeat_rate=0.05),
        ScrollAction(controller_button='LB', scroll_speed=15, initial_delay=0.3, repeat_rate=0.05),
        
        KeyboardAction(
            controller_button='X', 
            key=Key.left, 
            modifier=Key.cmd # On Windows, use Key.ctrl
        ),
        KeyboardAction(
            controller_button='Y',
            key=Key.right,
            modifier=Key.cmd # On Windows, use Key.ctrl
        ),
    ]

    try:
        xbox = XboxController()
        if not xbox.device:
            raise OSError("Controller not found or could not be opened.")
        
        # ✨ STEP 2 & 3: Instantiate both controllers
        mouse = MouseController()
        keyboard = KeyboardController()

        print("\nController mapped successfully! Mouse and keyboard control is active.")
        print("Configuration loaded. Ctrl+C to exit.")
        print("-" * 50)
        
        last_state = None
        last_print_time = 0

        while True:
            state = xbox.read()
            if state:
                # ✨ STEP 3 (continued): Pass both controllers to the update method
                for action in ACTION_CONFIG:
                    action.update(state, last_state, mouse, keyboard)
                
                last_state = state

                # Debugging output
                current_time = time.time()
                if current_time - last_print_time > 0.1:
                    pressed_buttons = sorted([name for name, pressed in state["buttons"].items() if pressed])
                    print(f"Stick:({state['lx']:.2f}, {state['ly']:.2f}) LT:{state['lt']:.2f} RT:{state['rt']:.2f} Buttons: {pressed_buttons}      ", end='\r')
                    last_print_time = current_time
            else:
                time.sleep(0.001)

    except OSError as e:
        print(f"\nError: {e}")
    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        if 'xbox' in locals() and xbox:
            xbox.close()