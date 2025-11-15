import pygame

pygame.init()
pygame.joystick.init()

# 检查手柄数量
count = pygame.joystick.get_count()
print(f"检测到 {count} 个手柄")

for i in range(count):
    js = pygame.joystick.Joystick(i)
    js.init()

    print("\n======================")
    print(f"手柄索引:       {i}")
    print(f"名称:           {js.get_name()}")
    
    # 一些系统下可用
    try:
        print(f"GUID:           {js.get_guid()}")
    except:
        print("GUID:           <此版本 pygame 不支持>")

    print(f"轴数量:         {js.get_numaxes()}")
    print(f"按钮数量:       {js.get_numbuttons()}")
    print(f"帽子数量:       {js.get_numhats()}")

pygame.quit()