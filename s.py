# ==============================================================================
# ======================== 依赖导入 ========================================
# ==============================================================================
import os
import struct
import time
import ctypes

# 关键：在导入 pygame 之前设置环境变量，以实现无头运行
os.environ["SDL_VIDEODRIVER"] = "dummy"

# 尝试导入 hid，如果失败也没关系，因为我们优先使用 Pygame
try:
    import hid
except ImportError:
    hid = None
    print("提示: 'hidapi' 库未安装。将仅使用 Pygame 后端。")

import pygame

from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController

# 在某些系统上，这可以防止屏幕保护程序启动
try:
    ctypes.CDLL(None).SDL_EnableScreenSaver()
except Exception:
    pass

# ==============================================================================
# =========== 控制器类定义 (HID - 作为备用/参考) =================
# ==============================================================================
# ... (HID 类代码保持不变，此处省略) ...
class XboxControllerHID:
    BUTTON_MAP = {0:"A1", 1:"A2", 2:"MENU", 3:"WIN", 4: "A", 5: "B", 6: "X", 7: "Y"}
    BUTTON_MAP_2 = {0:"UP", 1:"DOWN", 2:"LEFT", 3:"RIGHT", 4: "LB", 5: "RB", 6: "LS", 7: "RS"}
    def __init__(self, vendor_id=0x045E, product_id=0x0B12):
        self.device = None
        if not hid:
            print("错误: HIDAPI 库不可用, 无法使用 XboxControllerHID。")
            return
        try:
            self.device = hid.device()
            self.device.open(vendor_id, product_id)
            self.device.set_nonblocking(True)
            print("已连接 (HID):", self.device.get_manufacturer_string(), self.device.get_product_string())
        except OSError as e:
            print(f"打开 HID 设备时出错: {e}")
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
# ============ 控制器类定义 (Pygame - 支持热插拔) ============
# ==============================================================================
class GenericController:
    """
    使用 Pygame 作为后端的通用控制器类。
    支持手柄的热插拔，并根据手柄名称加载正确的按键映射。
    """
    # --- 为不同厂商的控制器定义映射表 ---
    MAPS = {
        # ================================================================== #
        # ✨✨✨ 此处已根据你提供的 Xbox 映射进行精确更新 ✨✨✨ #
        # ================================================================== #
        "MICROSOFT": {
            "buttons": {
                0: 'A', 1: 'B', 2: 'X', 3: 'Y',
                4: 'LB', 5: 'RB',
                6: 'LS',    # button_LS
                7: 'RS',    # button_RS
                8: 'MENU',  # button_Back
                10: 'WIN'   # button_Start
            },
            "axes": {
                0: 'lx', 1: 'ly',  # axis_LX, axis_LY
                2: 'lt',           # axis_LT
                3: 'rx', 4: 'ry',  # axis_RX, axis_RY
                5: 'rt'            # axis_RT
            },
            "invert_y": ['ly', 'ry'] # Y轴通常需要反转
        },
        # ================================================================== #
        
        "NINTENDO": {
            "buttons": {1: 'A', 0: 'B', 3: 'X', 2: 'Y', 4: 'LB', 5: 'RB', 8: 'MENU', 9: 'WIN', 10: 'LS', 11: 'RS'},
            "axes": {0: 'lx', 1: 'ly', 2: 'rx', 3: 'ry'}, # Pro 手柄没有模拟扳机
            "invert_y": ['ly', 'ry']
        },
        "DEFAULT": { # 其他手柄的默认/备用映射
            "buttons": {0: 'A', 1: 'B', 2: 'X', 3: 'Y', 4: 'LB', 5: 'RB', 6: 'MENU', 7: 'WIN', 8: 'LS', 9: 'RS'},
            "axes": {0: 'lx', 1: 'ly', 2: 'rx', 3: 'ry', 4: 'lt', 5: 'rt'},
            "invert_y": ['ly', 'ry']
        }
    }

    def __init__(self):
        self.joy = None
        self.detected_type = None
        self.button_map = {}
        self.axis_map = {}
        self.invert_y_axes = []
        
        pygame.init()
        pygame.joystick.init()
        print("Pygame 已初始化。等待手柄连接...")
        
        self._connect_joystick()

    def _connect_joystick(self):
        """扫描并连接第一个可用的手柄，然后加载对应的按键映射。"""
        if self.joy:
            self.joy = None

        if pygame.joystick.get_count() > 0:
            self.joy = pygame.joystick.Joystick(0)
            self.joy.init()
            joy_name = self.joy.get_name()
            print(f"\n已连接手柄: {joy_name} (ID: {self.joy.get_instance_id()})")

            if 'Microsoft' in joy_name or 'Xbox' in joy_name:
                self.detected_type = "MICROSOFT"
            elif 'Nintendo' in joy_name:
                self.detected_type = "NINTENDO"
            else:
                self.detected_type = "DEFAULT"
            
            config = self.MAPS[self.detected_type]
            self.button_map = config["buttons"]
            self.axis_map = config["axes"]
            self.invert_y_axes = config.get("invert_y", [])
            print(f"检测到手柄类型: {self.detected_type}, 已加载对应映射。")
            return True
        else:
            self.detected_type = None
            print("未检测到手柄。")
            return False

    def close(self):
        pygame.quit()

    def is_connected(self):
        return self.joy is not None

    def read(self):
        """
        处理Pygame事件（用于热插拔），然后轮询当前手柄状态。
        """
        for event in pygame.event.get():
            if event.type == pygame.JOYDEVICEADDED:
                print("\n检测到新设备插入！")
                if not self.is_connected():
                    self._connect_joystick()
            
            elif event.type == pygame.JOYDEVICEREMOVED:
                if self.is_connected() and event.instance_id == self.joy.get_instance_id():
                    print(f"\n手柄 (ID: {event.instance_id}) 已断开连接。")
                    self.joy = None
                    self.detected_type = None

        if not self.is_connected():
            return None
        
        buttons = {name: False for name in self.button_map.values()}
        for i in range(self.joy.get_numbuttons()):
            if self.joy.get_button(i):
                button_name = self.button_map.get(i)
                if button_name:
                    buttons[button_name] = True
        
        if self.joy.get_numhats() > 0:
            hat = self.joy.get_hat(0)
            if hat[1] == 1:  buttons['UP'] = True
            if hat[1] == -1: buttons['DOWN'] = True
            if hat[0] == -1: buttons['LEFT'] = True
            if hat[0] == 1:  buttons['RIGHT'] = True

        axes = {name: 0.0 for name in self.axis_map.values()}
        for i in range(self.joy.get_numaxes()):
            axis_name = self.axis_map.get(i)
            if axis_name:
                value = self.joy.get_axis(i)
                if axis_name in self.invert_y_axes:
                    value *= -1
                axes[axis_name] = value

        # 标准化扳机键的值 (-1.0 to 1.0 -> 0.0 to 1.0)
        lt_val = (axes.get('lt', -1.0) + 1.0) / 2.0
        rt_val = (axes.get('rt', -1.0) + 1.0) / 2.0

        return {
            "buttons": buttons,
            "lt": lt_val, "rt": rt_val,
            "lx": axes.get('lx', 0.0), "ly": axes.get('ly', 0.0),
            "rx": axes.get('rx', 0.0), "ry": axes.get('ry', 0.0),
        }

# ==============================================================================
# ======================== ACTION HANDLING SYSTEM (完整版) ====================
# ==============================================================================
# ... (Action 类代码保持不变，此处省略) ...
class Action:
    def update(self, state, last_state, mouse, keyboard):
        pass
class MouseMoveAction(Action):
    def __init__(self, x_axis, y_axis, sensitivity, deadzone):
        self.x_axis, self.y_axis, self.sensitivity, self.deadzone = x_axis, y_axis, sensitivity, deadzone
    def update(self, state, last_state, mouse, keyboard):
        x_val, y_val = state[self.x_axis], state[self.y_axis]
        if abs(x_val) < self.deadzone: x_val = 0
        if abs(y_val) < self.deadzone: y_val = 0
        if x_val != 0 or y_val != 0:
            mouse.move((x_val ** 3) * self.sensitivity, -(y_val ** 3) * self.sensitivity)
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
        if modifier:
            self.modifier = [modifier] if not isinstance(modifier, (list, tuple)) else modifier
        else:
            self.modifier = None
    def update(self, state, last_state, mouse, keyboard):
        is_pressed = state['buttons'].get(self.controller_button, False)
        was_pressed = last_state['buttons'].get(self.controller_button, False) if last_state else False
        if is_pressed and not was_pressed:
            if self.modifier:
                with keyboard.pressed(*self.modifier):
                    keyboard.tap(self.key)
            else:
                keyboard.tap(self.key)
class AnalogAsButtonScrollAction(Action):
    def __init__(self, axis_name, threshold, scroll_speed, initial_delay, repeat_rate):
        self.axis_name, self.threshold, self.scroll_speed, self.initial_delay, self.repeat_rate = axis_name, threshold, scroll_speed, initial_delay, repeat_rate
        self.pressed, self.next_scroll_time = False, 0
    def update(self, state, last_state, mouse, keyboard):
        value = state.get(self.axis_name, 0.0)
        is_down = value >= self.threshold if self.threshold >= 0 else value <= self.threshold
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
    def __init__(self, axis_name, sensitivity, deadzone, is_inverted=False):
        self.axis_name, self.sensitivity, self.deadzone = axis_name, sensitivity, deadzone
        self.direction = -1 if is_inverted else 1
    def update(self, state, last_state, mouse, keyboard):
        value = state.get(self.axis_name, 0.0)
        if abs(value) < self.deadzone: value = 0.0
        if value != 0.0:
            scroll_amount = (value ** 2) * self.sensitivity * self.direction
            mouse.scroll(0, scroll_amount)
class ThresholdAction(Action):
    def __init__(self, source_axis, threshold, output_button_name):
        self.source_axis, self.threshold, self.output_button_name = source_axis, threshold, output_button_name
    def update(self, state, last_state, mouse, keyboard):
        value = state.get(self.source_axis, 0.0)
        if self.threshold >= 0:
            state['buttons'][self.output_button_name] = (value >= self.threshold)
        else:
            state['buttons'][self.output_button_name] = (value <= self.threshold)

# ==============================================================================
# ======================== 主程序与配置 =====================================
# ==============================================================================
if __name__ == "__main__":
    # --- 配置文件 (保持不变) ---
    CONFIG_MICROSOFT = [
        MouseMoveAction(x_axis='lx', y_axis='ly', sensitivity=25, deadzone=0.15),
        MouseMoveAction(x_axis='rx', y_axis='ry', sensitivity=15, deadzone=0.15),
        ClickAction(controller_button='A', mouse_button=Button.left),
        ClickAction(controller_button='B', mouse_button=Button.right),
        AnalogAsButtonScrollAction(axis_name='lt', threshold=0.01, scroll_speed=15, initial_delay=0.3, repeat_rate=0.05),
        AnalogAsButtonScrollAction(axis_name='rt', threshold=0.01, scroll_speed=-15, initial_delay=0.3, repeat_rate=0.05),
        ScrollAction(controller_button='RB', scroll_speed=-15, initial_delay=0.3, repeat_rate=0.05),
        ScrollAction(controller_button='LB', scroll_speed=15, initial_delay=0.3, repeat_rate=0.05),
        ScrollAction(controller_button='UP', scroll_speed=1, initial_delay=0.4, repeat_rate=0.1),
        ScrollAction(controller_button='DOWN', scroll_speed=-1, initial_delay=0.4, repeat_rate=0.1),
        KeyboardAction(controller_button='X', key=Key.left, modifier=Key.cmd),
        KeyboardAction(controller_button='Y', key=Key.right, modifier=Key.cmd),
        KeyboardAction(controller_button='RIGHT', key=Key.tab),
        KeyboardAction(controller_button='LEFT', key=Key.tab, modifier=Key.shift),
        KeyboardAction(controller_button='WIN', key=Key.enter),
        KeyboardAction(controller_button='MENU', key='q', modifier=[Key.cmd, Key.ctrl]),
        KeyboardAction(controller_button='RS', key='w', modifier=Key.cmd),
    ]
    CONFIG_GENERIC = [
        ThresholdAction(source_axis='lx', threshold=0.5, output_button_name='STICK_RIGHT'),
        ThresholdAction(source_axis='lx', threshold=-0.5, output_button_name='STICK_LEFT'),
        ClickAction(controller_button='A', mouse_button=Button.left),
        ClickAction(controller_button='B', mouse_button=Button.right),
        AnalogAsButtonScrollAction(axis_name='ry', threshold=-0.5, scroll_speed=15, initial_delay=0.3, repeat_rate=0.05),
        AnalogAsButtonScrollAction(axis_name='ry', threshold=0.5, scroll_speed=-15, initial_delay=0.3, repeat_rate=0.05),
        ScrollAction(controller_button='UP', scroll_speed=1, initial_delay=0.4, repeat_rate=0.1),
        ScrollAction(controller_button='DOWN', scroll_speed=-1, initial_delay=0.4, repeat_rate=0.1),
        KeyboardAction(controller_button='X', key=Key.left, modifier=Key.cmd),
        KeyboardAction(controller_button='Y', key=Key.right, modifier=Key.cmd),
        KeyboardAction(controller_button='STICK_RIGHT', key=Key.tab),
        KeyboardAction(controller_button='STICK_LEFT', key=Key.tab, modifier=Key.shift),
        KeyboardAction(controller_button='WIN', key=Key.enter),
        KeyboardAction(controller_button='MENU', key='q', modifier=[Key.cmd, Key.ctrl]),
    ]

    # --- 主程序逻辑 (保持不变) ---
    controller = None
    ACTION_CONFIG = None
    mouse = None
    keyboard = None

    try:
        controller = GenericController()
        mouse = MouseController()
        keyboard = KeyboardController()
        
        last_state = None
        last_print_time = 0
        is_active = False

        while True:
            state = controller.read()

            if state:
                if not is_active:
                    is_active = True
                    if controller.detected_type == "MICROSOFT":
                        ACTION_CONFIG = CONFIG_MICROSOFT
                        print("\n已加载 Microsoft/Xbox 控制器配置文件。")
                    else:
                        ACTION_CONFIG = CONFIG_GENERIC
                        print(f"\n已加载通用配置文件 (适用于 {controller.detected_type})。")
                    print("手柄映射成功！鼠标和键盘控制已激活。")
                    print("按 Ctrl+C 退出。")
                    print("-" * 50)
                
                for action in ACTION_CONFIG:
                    action.update(state, last_state, mouse, keyboard)
                
                last_state = state

                current_time = time.time()
                if current_time - last_print_time > 0.1:
                    pressed = sorted([name for name, is_on in state["buttons"].items() if is_on])
                    print(f"L:({state['lx']:.2f},{state['ly']:.2f}) R:({state['rx']:.2f},{state['ry']:.2f}) LT:{state['lt']:.2f} RT:{state['rt']:.2f} B:{pressed}      ", end='\r')
                    last_print_time = current_time
            else:
                if is_active:
                    is_active = False
                    print("\n" + "-" * 50)
                    print("手柄控制已暂停。请重新连接手柄...")
                    ACTION_CONFIG = None
                    last_state = None
                
                print("等待手柄连接... (按 Ctrl+C 退出)", end='\r')
                time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n正在退出。")
    finally:
        if controller:
            controller.close()