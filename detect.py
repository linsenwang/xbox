# joystick.py
# A demonstration of the joystick module
#
# This simple example prints the joystick's name, GUID, power level, number of
# axes, hats, balls, and buttons, and whenever a joystick input is detected,
# it prints the input.

import pygame
import pygame.joystick

pygame.init()

# Initialize the joysticks
pygame.joystick.init()

print("pygame version:", pygame.version.ver)
print("SDL version:", ".".join(str(x) for x in pygame.get_sdl_version()))

def print_joystick_info(joystick):
    print("Joystick name:", joystick.get_name())
    print("Joystick GUID:", joystick.get_guid())
    try:
        print("Joystick's power level:", joystick.get_power_level())
    except pygame.error:
        print("Joystick's power level: unknown")
    print("Number of axes:", joystick.get_numaxes())
    print("Number of hats:", joystick.get_numhats())
    print("Number of balls:", joystick.get_numballs())
    print("Number of buttons:", joystick.get_numbuttons())
    print()


def main():
    done = False

    # Print information about connected joysticks
    joystick_count = pygame.joystick.get_count()
    print("Number of joysticks detected:", joystick_count)

    for i in range(joystick_count):
        joystick = pygame.joystick.Joystick(i)
        joystick.init()
        print("Joystick {}: ".format(i), end="")
        print_joystick_info(joystick)

    # Event loop
    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True

            # --- Joystick events ---
            elif event.type == pygame.JOYBUTTONDOWN:
                print("Joystick {} button {} down".format(event.joy, event.button))
            elif event.type == pygame.JOYBUTTONUP:
                print("Joystick {} button {} up".format(event.joy, event.button))

            elif event.type == pygame.JOYAXISMOTION:
                print("Joystick {} axis {} value: {:>6.3f}".format(
                    event.joy, event.axis, event.value
                ))

            elif event.type == pygame.JOYHATMOTION:
                print("Joystick {} hat {} value: {}".format(
                    event.joy, event.hat, event.value
                ))

            elif event.type == pygame.JOYBALLMOTION:
                print("Joystick {} ball {} value: {}".format(
                    event.joy, event.ball, event.rel
                ))


if __name__ == "__main__":
    main()