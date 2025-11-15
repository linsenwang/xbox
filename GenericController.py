import pygame

class GenericController:
    def __init__(self, custom_mapping):
        if not custom_mapping:
            raise ValueError("必须提供自定义映射 (custom_mapping)。")
        
        self.mapping = custom_mapping
        
        # --- 核心数据结构 ---
        self.joysticks = {}       # 存储所有【可用】手柄对象 {instance_id: joy_object}
        self.active_joy = None    # 当前被激活用于控制的手柄

        # 映射解析逻辑保持不变
        self.button_map = {v[1]: k for k, v in self.mapping.items() if v[0] == 'button'}
        self.axis_map = {v[1]: k for k, v in self.mapping.items() if v[0] == 'axis'}
        self.hat_map_index = self.mapping.get("dpad", (None, -1))[1]

        # 初始化 Pygame 及其 joystick 模块
        pygame.init()
        pygame.joystick.init()
        print("Pygame 已初始化。")
        
        # 启动时扫描并添加所有已连接的【可用】手柄
        for i in range(pygame.joystick.get_count()):
            self._add_joystick(i)

    def _add_joystick(self, device_index):
        """
        尝试添加一个新检测到的手柄，并进行有效性验证。
        """
        try:
            joy = pygame.joystick.Joystick(device_index)
            instance_id = joy.get_instance_id()

            # 防止重复添加
            if instance_id in self.joysticks:
                return

            # --- 关键的有效性检查 ---
            # 如果一个设备没有任何按键、摇杆和方向键，就认为它是无效设备并忽略。
            if joy.get_numbuttons() == 0 and joy.get_numaxes() == 0 and joy.get_numhats() == 0:
                print(f"检测到无效或非输入设备: '{joy.get_name()}' (ID: {instance_id})，已忽略。")
                return

            self.joysticks[instance_id] = joy
            print(f"发现可用手柄: {joy.get_name()} (ID: {instance_id})")

        except pygame.error as e:
            print(f"添加手柄 device_index {device_index} 时出错: {e}")


    def close(self):
        pygame.quit()

    def read(self):
        # --- 核心逻辑：完全基于事件驱动 ---
        for event in pygame.event.get():
            # 1. 处理手柄热插拔 (连接)
            if event.type == pygame.JOYDEVICEADDED:
                self._add_joystick(event.device_index)

            # 2. 处理手柄热插拔 (断开)
            if event.type == pygame.JOYDEVICEREMOVED:
                instance_id = event.instance_id
                if instance_id in self.joysticks:
                    print(f"\n手柄 '{self.joysticks[instance_id].get_name()}' (ID: {instance_id}) 已断开。")
                    del self.joysticks[instance_id]
                
                if self.active_joy and self.active_joy.get_instance_id() == instance_id:
                    print("当前活动手柄已断开，控制已暂停。")
                    self.active_joy = None
                    return None # 向主循环报告状态变更

            # 3. 如果当前没有激活的手柄，则等待任意输入来激活一个
            if self.active_joy is None:
                if (event.type == pygame.JOYBUTTONDOWN or
                   (event.type == pygame.JOYAXISMOTION and abs(event.value) > 0.8) or
                   (event.type == pygame.JOYHATMOTION and event.value != (0, 0))):
                    
                    joy_to_activate = self.joysticks.get(event.instance_id)
                    if joy_to_activate:
                        self.active_joy = joy_to_activate
                        print(f"\n手柄已激活: {self.active_joy.get_name()} (ID: {self.active_joy.get_instance_id()})")
                        
                        if self.mapping['name'].split(' ')[0].lower() not in self.active_joy.get_name().lower():
                            print(f"警告：激活的手柄 '{self.active_joy.get_name()}' 可能与映射文件中的 '{self.mapping['name']}' 不匹配。")
                        print("已成功加载自定义映射。")
                        # 激活后不立即返回数据，让主循环在下一轮开始读取状态
                        # 这避免了激活时的那个按键被立即解析为一次点击

        # --- 如果没有激活的手柄，直接返回 ---
        if self.active_joy is None:
            return None

        # --- 如果手柄已激活，执行正常的轮询来获取状态 ---
        joy = self.active_joy
        
        buttons = {name: False for name in self.button_map.values()}
        for i in range(joy.get_numbuttons()):
            if joy.get_button(i):
                button_name = self.button_map.get(i)
                if button_name: buttons[button_name] = True
        
        if self.hat_map_index != -1 and joy.get_numhats() > self.hat_map_index:
            hat = joy.get_hat(self.hat_map_index)
            buttons['UP'], buttons['DOWN'], buttons['LEFT'], buttons['RIGHT'] = (hat[1] == 1), (hat[1] == -1), (hat[0] == -1), (hat[0] == 1)
        
        axes = {name: 0.0 for name in self.axis_map.values()}
        for i in range(joy.get_numaxes()):
            axis_name = self.axis_map.get(i)
            if axis_name:
                value = joy.get_axis(i)
                if axis_name in ['ly', 'ry']: value *= -1
                axes[axis_name] = value

        lt_val = (axes.get('lt', -1.0) + 1.0) / 2.0
        rt_val = (axes.get('rt', -1.0) + 1.0) / 2.0

        return {"buttons": buttons, "lt": lt_val, "rt": rt_val, "lx": axes.get('lx', 0.0), "ly": axes.get('ly', 0.0), "rx": axes.get('rx', 0.0), "ry": axes.get('ry', 0.0)}