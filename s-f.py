import os
os.environ["SDL_VIDEODRIVER"] = "dummy"

import ctypes
import pygame
import time
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController

ctypes.CDLL(None).SDL_EnableScreenSaver()

# ==============================================================================
# ======================== 新的 Pygame 控制器类 ============================
# ==============================================================================
class XboxController:
    """
    使用 Pygame 作为后端的 Xbox 控制器类。
    这个类的目标是输出与原始 hid 版本完全相同的数据结构，
    以便上层的 Action 系统可以无缝衔接。
    """
    # --- 按钮和轴的映射 ---
    # 注意：这个映射可能因操作系统和手柄型号而异。
    # 这是 Xbox 手柄在大多数系统（尤其是 Windows 和 Linux）上常见的映射。
    # 如果按钮不对应，请在此处修改。
    # PYGAME_BUTTON_MAP = {
    #     1: 'A', 0: 'B', 3: 'X', 2: 'Y',
    #     9: 'LB', 10: 'RB',
    #     6: 'MENU',  # "View" 或 "Back" 按钮
    #     7: 'WIN',   # "Menu" 或 "Start" 按钮
    #     # 8: 'LS', 9: 'RS'
    # }

    # # Pygame 将扳机键(LT/RT)也视为轴
    # AXIS_MAP = {
    #     0: 'lx', 1: 'ly',  # 左摇杆 X/Y
    #     2: 'lt',           # 左扳机
    #     3: 'rx', 4: 'ry',  # 右摇杆 X/Y
    #     5: 'rt'            # 右扳机
    # }
    # # Pygame 中，摇杆向上通常是负值，我们将其反转以匹配原始代码的习惯
    # INVERT_Y_AXES = ['ly', 'ry']

    def __init__(self):
        self.joy = None
        try:
            pygame.init()
            pygame.joystick.init()
            joystick_count = pygame.joystick.get_count()
            if joystick_count == 0:
                print("错误：未检测到任何手柄。")
                return

            self.joy = pygame.joystick.Joystick(0)
            self.joy.init()
            print("已连接手柄:", self.joy.get_name())
            if 'Nintendo' in self.joy.get_name():
                    self.PYGAME_BUTTON_MAP = {
                        1: 'A', 0: 'B', 3: 'X', 2: 'Y',
                        9: 'LB', 10: 'RB',
                        6: 'MENU',  # "View" 或 "Back" 按钮
                        4: 'WIN',   # "Menu" 或 "Start" 按钮
                        # 8: 'LS', 9: 'RS'
                    }

                    # Pygame 将扳机键(LT/RT)也视为轴
                    self.AXIS_MAP = {
                        0: 'lx', 1: 'ly',  # 左摇杆 X/Y
                        2: 'lt',           # 左扳机
                        3: 'rx', 4: 'ry',  # 右摇杆 X/Y
                        5: 'rt'            # 右扳机
                    }
                    # Pygame 中，摇杆向上通常是负值，我们将其反转以匹配原始代码的习惯
                    self.INVERT_Y_AXES = ['ly', 'ry']
        except Exception as e:
            print(f"初始化 Pygame 或手柄时出错: {e}")
            self.joy = None

    def close(self):
        """在程序退出时关闭 Pygame。"""
        if self.joy:
            pygame.quit()

    def read(self):
        """
        读取手柄的当前状态，并返回与原始 hid 版本兼容的字典。
        """
        if not self.joy:
            return None

        # Pygame 需要事件泵来更新内部状态
        pygame.event.pump()

        # 1. 解码按钮
        buttons = {}
        for i in range(self.joy.get_numbuttons()):
            if self.joy.get_button(i):
                button_name = self.PYGAME_BUTTON_MAP.get(i)
                if button_name:
                    buttons[button_name] = True
        
        # 2. 解码十字键 (Hat)
        if self.joy.get_numhats() > 0:
            hat = self.joy.get_hat(0)
            if hat[1] == 1:  buttons['UP'] = True
            if hat[1] == -1: buttons['DOWN'] = True
            if hat[0] == -1: buttons['LEFT'] = True
            if hat[0] == 1:  buttons['RIGHT'] = True

        # 3. 解码轴 (摇杆和扳机)
        axes = {}
        for i in range(self.joy.get_numaxes()):
            axis_name = self.AXIS_MAP.get(i)
            if axis_name:
                value = self.joy.get_axis(i)
                # 反转 Y 轴
                if axis_name in self.INVERT_Y_AXES:
                    value *= -1
                axes[axis_name] = value

        # 4. 标准化扳机键的值
        # Pygame 的扳机轴范围是 -1.0 (释放) 到 1.0 (按满)
        # 我们需要将其转换为 0.0 到 1.0
        lt_val = (axes.get('lt', -1.0) + 1.0) / 2.0
        rt_val = (axes.get('rt', -1.0) + 1.0) / 2.0

        # 5. 组装成最终的状态字典
        state = {
            "buttons": buttons,
            "lt": lt_val,
            "rt": rt_val,
            "lx": axes.get('lx', 0.0),
            "ly": axes.get('ly', 0.0),
            "rx": axes.get('rx', 0.0),
            "ry": axes.get('ry', 0.0),
        }
        return state

    # 旧的 _decode_buttons 和 _normalize_axis 不再需要，因为 Pygame 已经处理了
    # 标准化，我们只需要做少量转换。

# ==============================================================================
# ======================== ACTION HANDLING SYSTEM ==========================
# ==============================================================================

# --- ✨✨✨ 您的所有 Action 类都保持不变！✨✨✨ ---
# 无需对下面的任何 Action 类进行修改，因为新的 XboxController 提供了
# 完全相同的数据接口。

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
        if modifier:
            if not isinstance(modifier, (list, tuple)):
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
                with keyboard.pressed(*self.modifier):
                    keyboard.tap(self.key)
            else:
                keyboard.tap(self.key)

class AnalogAsButtonScrollAction(Action):
    def __init__(self, axis_name, threshold, scroll_speed, initial_delay, repeat_rate, scroll_rate=1):
        self.axis_name, self.threshold, self.initial_delay, self.repeat_rate = axis_name, threshold, initial_delay, repeat_rate
        self.scroll_speed = scroll_speed * scroll_rate
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
    """
    一个预处理 Action，它将一个模拟输入值（如扳机）与一个阈值比较，
    如果超过阈值，就在 state['buttons'] 中创建一个“虚拟”的按钮状态。
    这个 Action 应该放在配置列表的前面。
    """
    def __init__(self, source_axis, threshold, output_button_name):
        self.source_axis = source_axis             # 源模拟轴, e.g., 'lt'
        self.threshold = threshold                 # 阈值, e.g., 0.5
        self.output_button_name = output_button_name # 虚拟按钮的名称, e.g., 'LT_AS_BUTTON'

    def update(self, state, last_state, mouse, keyboard):
        value = state.get(self.source_axis, 0.0)
        # 如果值超过阈值, 就在 buttons 字典里设置虚拟按钮为 True，否则为 False
        if self.threshold >= 0:
            state['buttons'][self.output_button_name] = (value >= self.threshold)
        else:
            state['buttons'][self.output_button_name] = (value <= self.threshold)


# ==============================================================================
# ======================== 主程序与配置 =====================================
# ==============================================================================
if __name__ == "__main__":
    # --------------------------------------------------------------------------
    # --- ✨✨✨ ACTION 配置中心 (保持不变) ✨✨✨ ---
    # --------------------------------------------------------------------------
    ACTION_CONFIG = [
        # MouseMoveAction(x_axis='lx', y_axis='ly', sensitivity=25, deadzone=0.15),
        # MouseMoveAction(x_axis='rx', y_axis='ry', sensitivity=25, deadzone=0.15),
        ThresholdAction(source_axis='lx', threshold=0.5, output_button_name='RIGHT'),
        ThresholdAction(source_axis='lx', threshold=-0.5, output_button_name='LEFT'),
        ClickAction(controller_button='A', mouse_button=Button.left),
        ClickAction(controller_button='B', mouse_button=Button.right),
        AnalogAsButtonScrollAction(axis_name='ly', threshold=-0.5, scroll_speed=15, initial_delay=0.3, repeat_rate=0.05),
        AnalogAsButtonScrollAction(axis_name='ly', threshold=0.5, scroll_speed=-15, initial_delay=0.3, repeat_rate=0.05),
        # AnalogAsButtonScrollAction(axis_name='rt', threshold=0.5, scroll_speed=-15, initial_delay=0.3, repeat_rate=0.05),
        # ScrollAction(controller_button='RB', scroll_speed=-15, initial_delay=0.3, repeat_rate=0.05),
        # ScrollAction(controller_button='LB', scroll_speed=15, initial_delay=0.3, repeat_rate=0.05),
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

    xbox = None # 定义在 try 块外部，以便 finally 可以访问
    try:
        xbox = XboxController()
        # 修改了这里的检查条件
        if not xbox.joy:
            raise OSError("手柄未找到或无法打开。")
        
        mouse = MouseController()
        keyboard = KeyboardController()

        print("\n手柄映射成功！鼠标和键盘控制已激活。")
        print("配置已加载。按 Ctrl+C 退出。")
        print("-" * 50)
        
        last_state = None
        last_print_time = 0

        while True:
            state = xbox.read()
            if state:
                for action in ACTION_CONFIG:
                    action.update(state, last_state, mouse, keyboard)
                
                last_state = state

                # Debugging output (稍作调整以适应新的数据结构)
                current_time = time.time()
                if current_time - last_print_time > 0.1:
                    pressed_buttons = sorted([name for name, pressed in state["buttons"].items() if pressed])
                    # 调整了打印格式以适应新的数据
                    print(f"L:({state['lx']:.2f},{state['ly']:.2f}) R:({state['rx']:.2f},{state['ry']:.2f}) LT:{state['lt']:.2f} RT:{state['rt']:.2f} B:{pressed_buttons}      ", end='\r')
                    last_print_time = current_time
            else:
                # 如果手柄断开或读取失败，可以暂停一下
                time.sleep(5)

    except OSError as e:
        print(f"\n错误: {e}")
    except KeyboardInterrupt:
        print("\n正在退出。")
    finally:
        if xbox:
            xbox.close()