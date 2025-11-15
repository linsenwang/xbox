import pygame
import sys

# This is a helper class from the second example to handle rendering text to the screen.
class TextPrint:
    def __init__(self):
        self.reset()
        self.font = pygame.font.SysFont(None, 28)

    def tprint(self, screen, text):
        text_bitmap = self.font.render(text, True, (255, 255, 255))
        screen.blit(text_bitmap, (self.x, self.y))
        self.y += self.line_height

    def reset(self):
        self.x = 20
        self.y = 20
        self.line_height = 30

    def indent(self):
        self.x += 20

    def unindent(self):
        self.x -= 20


def main():
    pygame.init()

    screen = pygame.display.set_mode((800, 400))
    pygame.display.set_caption("Gamepad Mapping Tool")
    clock = pygame.time.Clock()
    text_print = TextPrint()

    # This dictionary will hold all connected joysticks, keyed by their instance_id.
    joysticks = {}
    
    # --- Mapping tasks from the first example ---
    tasks = [
        ("button_A", "Press the 'A' button (bottom face button)"),
        ("button_B", "Press the 'B' button (right face button)"),
        ("button_X", "Press the 'X' button (left face button)"),
        ("button_Y", "Press the 'Y' button (top face button)"),
        ("button_LB", "Press the Left Bumper (LB)"),
        ("button_RB", "Press the Right Bumper (RB)"),
        ("button_Back", "Press the Back/Select/View button"),
        ("button_Start", "Press the Start/Menu button"),
        ("button_LS", "Press the Left Stick (click)"),
        ("button_RS", "Press the Right Stick (click)"),
        ("axis_LT", "Pull the Left Trigger (LT)"),
        ("axis_RT", "Pull the Right Trigger (RT)"),
        ("axis_LX", "Move the Left Stick left/right"),
        ("axis_LY", "Move the Left Stick up/down"),
        ("axis_RX", "Move the Right Stick left/right"),
        ("axis_RY", "Move the Right Stick up/down"),
        ("hat_Dpad", "Press any direction on the D-Pad"),
    ]

    mapping = {}
    task_i = 0
    selected_joystick_id = None
    done = False

    while not done:
        # --- Event processing ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True

            # Handle hotplugging
            if event.type == pygame.JOYDEVICEADDED:
                joy = pygame.joystick.Joystick(event.device_index)
                joysticks[joy.get_instance_id()] = joy
                print(f"Joystick {joy.get_instance_id()} ({joy.get_name()}) connected")

            if event.type == pygame.JOYDEVICEREMOVED:
                if event.instance_id == selected_joystick_id:
                    # If the joystick we were mapping is disconnected, reset.
                    print("The mapped joystick was disconnected. Please restart.")
                    done = True # Or handle this more gracefully
                del joysticks[event.instance_id]
                print(f"Joystick {event.instance_id} disconnected")

            # --- Phase 1: Select which joystick to map ---
            if selected_joystick_id is None and len(joysticks) > 0:
                if event.type == pygame.JOYBUTTONDOWN:
                    selected_joystick_id = event.instance_id
                    print(f"Started mapping for joystick {selected_joystick_id}: {joysticks[selected_joystick_id].get_name()}")
                elif event.type == pygame.JOYAXISMOTION and abs(event.value) > 0.5:
                    selected_joystick_id = event.instance_id
                    print(f"Started mapping for joystick {selected_joystick_id}: {joysticks[selected_joystick_id].get_name()}")
                elif event.type == pygame.JOYHATMOTION and event.value != (0, 0):
                    selected_joystick_id = event.instance_id
                    print(f"Started mapping for joystick {selected_joystick_id}: {joysticks[selected_joystick_id].get_name()}")
                continue # Skip to the next event

            # --- Phase 2: Perform the mapping task ---
            if selected_joystick_id is not None and task_i < len(tasks):
                # Ensure the event is from the selected joystick
                if hasattr(event, 'instance_id') and event.instance_id != selected_joystick_id:
                    continue

                key, msg = tasks[task_i]

                # Buttons
                if event.type == pygame.JOYBUTTONDOWN:
                    if ("button", event.button) not in mapping.values():
                        mapping[key] = ("button", event.button)
                        print(f"Mapped {key} = button {event.button}")
                        task_i += 1
                
                # Axes
                elif event.type == pygame.JOYAXISMOTION:
                    if abs(event.value) > 0.7:
                         if ("axis", event.axis) not in mapping.values():
                            mapping[key] = ("axis", event.axis)
                            print(f"Mapped {key} = axis {event.axis}")
                            task_i += 1

                # Hat (D-pad)
                elif event.type == pygame.JOYHATMOTION:
                    if event.value != (0, 0):
                        if ("hat", event.hat) not in mapping.values():
                            # We only care about the hat index, not its value
                            mapping[key] = ("hat", event.hat)
                            print(f"Mapped {key} = hat {event.hat}")
                            task_i += 1
        
        # --- Drawing step ---
        screen.fill((30, 30, 30))
        text_print.reset()

        if len(joysticks) == 0:
            text_print.tprint(screen, "Please connect a joystick.")
        elif selected_joystick_id is None:
            text_print.tprint(screen, "Press any button on the controller you wish to map.")
            text_print.tprint(screen, "")
            text_print.tprint(screen, "Connected controllers:")
            text_print.indent()
            for joy_id, joy in joysticks.items():
                text_print.tprint(screen, f"[{joy_id}] {joy.get_name()}")
            text_print.unindent()
        elif task_i < len(tasks):
            joy_name = joysticks[selected_joystick_id].get_name()
            text_print.tprint(screen, f"Mapping: {joy_name}")
            text_print.tprint(screen, "----------------------------------------------------")
            text_print.tprint(screen, f"Task {task_i + 1}/{len(tasks)}:")
            text_print.tprint(screen, "")
            text_print.tprint(screen, f"--> {tasks[task_i][1]}") # Display current instruction
        else:
            text_print.tprint(screen, "Mapping complete!")
            text_print.tprint(screen, "Check the console output for the mapping dictionary.")
            text_print.tprint(screen, "You can now close this window.")
            done = True # Automatically mark as done to exit loop

        pygame.display.flip()
        clock.tick(30)
    
    # --- Print final results ---
    print("\n" + "="*25)
    print("=== Mapping Completed ===")
    print("="*25)
    if mapping:
        for k, v in mapping.items():
            print(f"'{k}': {v},")
    else:
        print("No mapping was generated.")

    pygame.quit()


if __name__ == "__main__":
    main()