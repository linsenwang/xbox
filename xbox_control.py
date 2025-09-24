import objc
from Foundation import NSLog, NSRunLoop, NSDate, NSNotificationCenter
import GameController

# 定义一个类来管理手柄逻辑
class ControllerManager(objc.lookUpClass('NSObject')):

    def init(self):
        """初始化方法"""
        self = super().init()
        if self is None:
            return None
        
        self.controller = None
        NSLog("ControllerManager 已初始化")
        return self

    def startMonitoring(self):
        """开始监听手柄连接"""
        NSLog("正在搜索手柄...")

        nc = NSNotificationCenter.defaultCenter()
        
        # ✅ 修正点 1: 使用正确的 selector 'controllerConnected:'
        nc.addObserver_selector_name_object_(
            self,
            b'controllerConnected:', # 注意这里的变化
            GameController.GCControllerDidConnectNotification,
            None
        )

        # 检查是否已经有手柄连接
        controllers = GameController.GCController.controllers()
        if controllers:
            NSLog(f"已发现 {len(controllers)} 个已连接的手柄")
            # 为所有已经连接的手柄设置回调
            for controller in controllers:
                # 使用一个假的 notification 对象来调用处理器
                self.controllerConnected_(controller)

    # ✅ 修正点 2: 修正方法名，从 controller_connected_ 改为 controllerConnected_
    def controllerConnected_(self, notificationOrController):
        """手柄连接时的回调方法"""
        
        # 这个方法现在可以处理两种情况：
        # 1. 来自 NSNotificationCenter 的通知 (notificationOrController 是 NSNotification)
        # 2. 手动调用传入的控制器 (notificationOrController 是 GCController)
        if hasattr(notificationOrController, 'object'):
             controller = notificationOrController.object()
        else:
             controller = notificationOrController
        
        self.controller = controller
        NSLog(f"处理手柄: {self.controller.vendorName()}")

        gamepad = self.controller.extendedGamepad()
        if gamepad:
            NSLog("手柄支持 Extended Gamepad 模式")
            a_button = gamepad.buttonA()
            
            # ✅ 修正点 3: 调用修正后的 buttonHandler_ 方法
            a_button.setPressedChangedHandler_(self.buttonHandler_)
            NSLog("已为 A 键绑定事件处理器")
        else:
            NSLog("手柄不支持 Extended Gamepad 模式")
            
    # ✅ 修正点 4: 修正方法名，从 button_handler_ 改为 buttonHandler_
    def buttonHandler_(self, button, value, pressed):
        """按键事件的回调方法 (Block)"""
        if pressed:
            NSLog(f"按钮事件: A键被按下, value={value:.2f}")
        else:
            NSLog(f"按钮事件: A键被松开, value={value:.2f}")


def main():
    manager = ControllerManager.alloc().init()
    manager.startMonitoring() # 修正了方法名调用

    loop = NSRunLoop.currentRunLoop()
    NSLog("进入主循环，等待事件...")
    while True:
        # runUntilDate_ 是更节能的方式
        loop.runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.1))
        
if __name__ == '__main__':
    main()