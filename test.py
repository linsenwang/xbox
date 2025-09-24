import pygame
import time

# --- 新增：设置常量 ---
# 屏幕尺寸
SCREEN_WIDTH = 500
SCREEN_HEIGHT = 300
# 颜色
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

def main():
    pygame.init()
    pygame.joystick.init()
    
    # --- 新增：初始化字体和时钟 ---
    font = pygame.font.Font(None, 74) # 用于显示页码的字体
    clock = pygame.time.Clock()      # 用于控制刷新率

    joystick_count = pygame.joystick.get_count()
    if joystick_count == 0:
        print("没有检测到手柄，确保已连接")
        return

    # 初始化所有找到的手柄
    joysticks = []
    for i in range(joystick_count):
        print(i)
        joy = pygame.joystick.Joystick(i)
        joy.init()
        joysticks.append(joy)
        print(f"检测到手柄 {i}: {joy.get_name()}")
        
    print("\n--- 开始监听事件 ---")
    print("使用方向键(D-pad)、肩键(L1/R1)或左摇杆左右拨动来翻页。")


    # 设置窗口
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("手柄翻页测试")

    # --- 1. 创建“页面”状态 ---
    current_page = 1
    total_pages = 100
    
    # --- 新增：用于处理摇杆的变量 ---
    # 这个布尔值确保你拨动一次摇杆只翻一页，而不是连续翻页
    axis_moved = False 

    running = True
    try:
        while running:
            # --- 2. 映射输入到动作 (事件处理) ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False # 优雅地退出循环
                
                # --- A. 使用方向键 (Hat) 翻页 ---
                if event.type == pygame.JOYHATMOTION:
                    # event.value 是一个元组 (x, y)
                    # (1, 0) 是右, (-1, 0) 是左
                    hat_x, hat_y = event.value
                    if hat_x == 1:
                        current_page += 1
                        print("方向键: 下一页")
                    elif hat_x == -1:
                        current_page -= 1
                        print("方向键: 上一页")
                
                # --- B. 使用按钮 (Buttons) 翻页 ---
                # 通常，按钮4是L1/LB，按钮5是R1/RB。你的手柄可能不同。
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 5: # R1/RB
                        current_page += 1
                        print("按钮: 下一页")
                    elif event.button == 4: # L1/LB
                        current_page -= 1
                        print("按钮: 上一页")
                        
                # --- C. 使用摇杆 (Axis) 翻页 ---
                if event.type == pygame.JOYAXISMOTION:
                    # 通常，轴0是左摇杆的左右方向
                    if event.axis == 0: 
                        # 向右拨动 (值接近 1.0)
                        if event.value > 0.8 and not axis_moved:
                            current_page += 1
                            print("摇杆: 下一页")
                            axis_moved = True # 标记为已移动，防止连续触发
                        # 向左拨动 (值接近 -1.0)
                        elif event.value < -0.8 and not axis_moved:
                            current_page -= 1
                            print("摇杆: 上一页")
                            axis_moved = True # 标记为已移动
                        # 摇杆回中
                        elif abs(event.value) < 0.2:
                            axis_moved = False # 回到中间时重置标志

            # --- 核心逻辑：确保页码不会超出范围 ---
            if current_page > total_pages:
                current_page = total_pages
            if current_page < 1:
                current_page = 1
            
            # --- 3. 显示当前状态 (绘制屏幕) ---
            # 用黑色填充背景
            screen.fill(BLACK)
            
            # 准备要显示的文本
            text_to_show = f"Page {current_page} / {total_pages}"
            text_surface = font.render(text_to_show, True, WHITE)
            
            # 将文本居中显示
            text_rect = text_surface.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
            
            # 在屏幕上绘制文本
            screen.blit(text_surface, text_rect)
            
            # 更新整个屏幕
            pygame.display.flip()
            
            # 控制游戏循环的频率，比如每秒60帧
            clock.tick(60)

    except KeyboardInterrupt:
        print("用户中断退出")
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()