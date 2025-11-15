import hid
import struct
import time
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController

# --- XboxController class remains unchanged ---
class XboxController:
    BUTTON_MAP = {0:"A1", 1:"A2", 2:"MENU", 3:"WIN", 4: "A", 5: "B", 6: "X", 7: "Y"}
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
    def update(self, state, last_state, mouse, keyboard):
        pass

class MouseMoveAction(Action):
    def __init__(self, x_axis, y_axis, sensitivity, deadzone):
        self.x_axis, self.y_axis, self.sensitivity, self.deadzone = x_axis, y_axis, sensitivity, deadzone

    def update(self, state, last_state, mouse, keyboard):
        lx, ly = state[self.x_axis], state[self.y_axis]
        if abs(lx) < self.deadzone: lx = 0
        if abs(ly) < self.deadzone: ly = 0
        if lx != 0 or ly != 0:
            mouse.move((lx ** 3) * self.sensitivity, -(ly ** 3) * self.sensitivity)

class ClickAction(Action):
    def __init__(self, controller_button, mouse_button):
        self.controller_button, self.mouse_button = controller_button, mouse_button

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

class KeyboardAction(Action):
    def __init__(self, controller_button, key, modifier=None):
        self.controller_button = controller_button
        self.key = key

        # --- Improvement ---
        # Ensure self.modifier is always a list or tuple if it exists
        if modifier:
            if not isinstance(modifier, (list, tuple)):
                # If a single modifier is passed, wrap it in a list
                self.modifier = [modifier]
            else:
                self.modifier = modifier
        else:
            self.modifier = None

    def update(self, state, last_state, mouse, keyboard):
        is_pressed = state['buttons'].get(self.controller_button, False)
        was_pressed = last_state['buttons'].get(self.controller_button, False) if last_state else False

        if is_pressed and not was_pressed:
            if self.modifier:
                # Now this will always work correctly because self.modifier is a list
                with keyboard.pressed(*self.modifier):
                    keyboard.tap(self.key)
            else:
                keyboard.tap(self.key)

class AnalogAsButtonScrollAction(Action):
    """
    将模拟输入（如扳机）当作按钮使用，以触发固定速度的滚动。
    当模拟值超过设定的阈值时，就认为按钮被“按下”。
    """
    def __init__(self, axis_name, threshold, scroll_speed, initial_delay, repeat_rate, scroll_rate=1):
        self.axis_name = axis_name             # 模拟轴名称, 如 'lt', 'rt'
        self.threshold = threshold             # 触发阈值, 如 0.5 (表示按下一半)
        self.scroll_speed = scroll_speed * scroll_rate       # 固定的滚动速度
        self.initial_delay = initial_delay     # 首次滚动后的延迟
        self.repeat_rate = repeat_rate         # 重复滚动的频率
        self.pressed = False
        self.next_scroll_time = 0

    def update(self, state, last_state, mouse, keyboard):
        # 从 state 获取模拟值
        value = state.get(self.axis_name, 0.0)
        # 判断模拟值是否超过阈值，将其转换为布尔值
        if self.threshold > 0:
            is_down = value >= self.threshold
        else:
            is_down = value <= self.threshold

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

class VariableScrollAction(Action):
    """
    根据模拟输入（扳机或摇杆）的值来控制滚动速度。
    这个类处理的是“可变值”。
    """
    def __init__(self, axis_name, sensitivity, deadzone, is_inverted=False):
        self.axis_name = axis_name         # 要使用的轴，如 'lt', 'rt', 'ly', 'ry'
        self.sensitivity = sensitivity     # 灵敏度，即最大滚动速度
        self.deadzone = deadzone           # 死区，低于此值输入无效
        self.direction = -1 if is_inverted else 1 # 方向控制

    def update(self, state, last_state, mouse, keyboard):
        # 从 state 字典中获取扳机或摇杆的模拟值 (0.0 到 1.0)
        value = state.get(self.axis_name, 0.0)

        # 应用死区
        if abs(value) < self.deadzone:
            value = 0.0

        # 如果值不为零，则进行滚动
        if value != 0.0:
            # 计算滚动量：模拟值 * 灵敏度 * 方向
            # 添加一个平方或立方可以使滚动加速更平滑 (可选)
            scroll_amount = (value ** 2) * self.sensitivity * self.direction
            mouse.scroll(0, scroll_amount)


# ==============================================================================
# ======================== 主程序与配置 =====================================
# ==============================================================================
if __name__ == "__main__":
    # --------------------------------------------------------------------------
    # --- ✨✨✨ ACTION 配置中心 ✨✨✨ ---
    # 在这里“注册”你想要的所有功能
    # --------------------------------------------------------------------------
    ACTION_CONFIG = [
        # --- 鼠标移动 ---
        MouseMoveAction(x_axis='lx', y_axis='ly', sensitivity=25, deadzone=0.15),
        MouseMoveAction(x_axis='rx', y_axis='ry', sensitivity=25, deadzone=0.15),
        # MouseMoveAction(x_axis='rx', y_axis='ry', sensitivity=15, deadzone=0.15),
        
        # --- 鼠标点击 ---
        ClickAction(controller_button='A', mouse_button=Button.left),
        ClickAction(controller_button='B', mouse_button=Button.right),

        # --- 按扳机键(RT/LT)速度滚动 ---
        # VariableScrollAction(axis_name='rt', sensitivity=-1, deadzone=0.1, is_inverted=False),
        # VariableScrollAction(axis_name='lt', sensitivity=1, deadzone=0.1, is_inverted=False),
        # VariableScrollAction(axis_name='ry', sensitivity=-1, deadzone=0.15, is_inverted=True),

        AnalogAsButtonScrollAction(axis_name='lt', threshold=0.01, scroll_speed=15, initial_delay=0.3, repeat_rate=0.05),
        AnalogAsButtonScrollAction(axis_name='rt', threshold=0.01, scroll_speed=15, initial_delay=0.3, repeat_rate=0.05),

        # AnalogAsButtonScrollAction(axis_name='ry', threshold=-0.5, scroll_speed=-15, initial_delay=0.3, repeat_rate=0.05),
        # AnalogAsButtonScrollAction(axis_name='ry', threshold=0.5, scroll_speed=15, initial_delay=0.3, repeat_rate=0.05),
        
        # 当右扳机(rt)按下超过50%时，向下滚动
        # AnalogAsButtonScrollAction(
        #     axis_name='rt', 
        #     threshold=0.01, 
        #     scroll_speed=-15, 
        #     initial_delay=0.3, 
        #     repeat_rate=0.05
        # ),

        # --- 新增功能 2: 使用肩键(RB/LB)或十字键进行“原版”固定速度滚动 ---
        ScrollAction(controller_button='RB', scroll_speed=-15, initial_delay=0.3, repeat_rate=0.05),
        ScrollAction(controller_button='LB', scroll_speed=-15, initial_delay=0.3, repeat_rate=0.05),
        # 示例：添加十字键的上和下作为额外的滚动按钮
        ScrollAction(controller_button='UP', scroll_speed=1, initial_delay=0.4, repeat_rate=0.1),
        ScrollAction(controller_button='DOWN', scroll_speed=-1, initial_delay=0.4, repeat_rate=0.1),
        
        # --- 键盘按键映射 ---
        KeyboardAction(
            controller_button='X', 
            key=Key.left, 
            modifier=Key.cmd
        ),
        KeyboardAction(
            controller_button='Y',
            key=Key.right,
            modifier=Key.cmd
        ),

        KeyboardAction(controller_button='RIGHT', key=Key.tab),
        KeyboardAction(controller_button='LEFT', key=Key.tab, modifier=Key.shift),
        KeyboardAction(controller_button='WIN', key=Key.enter),
        KeyboardAction(controller_button='MENU', key='q', modifier=[Key.cmd, Key.ctrl]),
        KeyboardAction(controller_button='RS', key='w', modifier=Key.cmd),
        # KeyboardAction(
        #     controller_button='RIGHT',
        #     key=Key.right,
        #     modifier=[Key.cmd, Key.alt]
        # ),

        # KeyboardAction(
        #     controller_button='LEFT',
        #     key=Key.left,
        #     modifier=[Key.cmd, Key.alt]
        # ),
    ]

    try:
        xbox = XboxController()
        if not xbox.device:
            raise OSError("Controller not found or could not be opened.")
        
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