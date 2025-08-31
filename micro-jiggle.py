import time
import random
import pyautogui

# Track last mouse position & movement time
last_pos = pyautogui.position()
last_move_time = time.time()

while True:
    current_pos = pyautogui.position()

    # If the user moved the mouse, reset timer
    if current_pos != last_pos:
        last_pos = current_pos
        last_move_time = time.time()

    # Random idle threshold (between 2 and 6 seconds)
    idle_threshold = random.uniform(2, 6)

    if time.time() - last_move_time > idle_threshold:
        # Random chance to actually fire movement (80% chance)
        if random.random() < 0.8:
            # Random movement between -5 and +5 pixels in x/y
            dx = random.randint(-5, 5)
            dy = random.randint(-5, 5)

            pyautogui.moveRel(dx, dy, duration=random.uniform(0.05, 0.3))

        # Reset idle timer after we considered moving
        last_move_time = time.time()

    # Small sleep to reduce CPU usage
    time.sleep(0.2)
