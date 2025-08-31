import ctypes
import random
import time
import threading
from pynput import keyboard
import pyautogui

# ---------------- Windows SendInput Setup ----------------
PUL = ctypes.POINTER(ctypes.c_ulong)
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_WHEEL = 0x0800  # vertical wheel

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("mi", MOUSEINPUT)]

def send_input(x, y):
    screen_width = ctypes.windll.user32.GetSystemMetrics(0)
    screen_height = ctypes.windll.user32.GetSystemMetrics(1)
    abs_x = int(x * 65535 / screen_width)
    abs_y = int(y * 65535 / screen_height)

    mi = MOUSEINPUT(dx=abs_x, dy=abs_y, mouseData=0,
                    dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE,
                    time=0, dwExtraInfo=None)
    inp = INPUT(type=0, mi=mi)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

def send_scroll(amount):
    """Scroll up (positive) or down (negative) using hardware-level input"""
    mi = MOUSEINPUT(dx=0, dy=0, mouseData=amount * 120,
                    dwFlags=MOUSEEVENTF_WHEEL,
                    time=0, dwExtraInfo=None)
    inp = INPUT(type=0, mi=mi)
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

# ---------------- Human-like Movement ----------------
def bezier_curve(p0, p1, p2, p3, t):
    """Cubic Bezier curve"""
    return (
        (1 - t)**3 * p0 +
        3 * (1 - t)**2 * t * p1 +
        3 * (1 - t) * t**2 * p2 +
        t**3 * p3
    )

def smooth_move_curve(start_pos, end_pos, steps=80):
    """Smooth curved movement using random Bezier control points"""
    x0, y0 = start_pos
    x3, y3 = end_pos

    # Random control points near line between start & end
    cx1 = x0 + (x3 - x0) * 0.3 + random.randint(-100, 100)
    cy1 = y0 + (y3 - y0) * 0.3 + random.randint(-100, 100)
    cx2 = x0 + (x3 - x0) * 0.6 + random.randint(-100, 100)
    cy2 = y0 + (y3 - y0) * 0.6 + random.randint(-100, 100)

    for i in range(1, steps + 1):
        t = i / steps
        x = bezier_curve(x0, cx1, cx2, x3, t) + random.uniform(-1, 1)
        y = bezier_curve(y0, cy1, cy2, y3, t) + random.uniform(-1, 1)
        send_input(x, y)
        time.sleep(random.uniform(0.005, 0.02))

# ---------------- Random Mouse Mover ----------------
running = False
clicks_enabled = True
scroll_enabled = True
mover_thread = None

def random_mouse_mover():
    global running, clicks_enabled, scroll_enabled
    screen_width, screen_height = pyautogui.size()

    # Define bounding box (65% of screen, centered)
    box_width = int(screen_width * 0.65)
    box_height = int(screen_height * 0.65)
    x_min = (screen_width - box_width) // 2
    x_max = x_min + box_width
    y_min = (screen_height - box_height) // 2
    y_max = y_min + box_height

    while running:
        start = pyautogui.position()

        # Occasionally stay still for 1-8 seconds
        if random.random() < 0.25:
            pause_time = random.uniform(1.0, 8.0)
            time.sleep(pause_time)
            continue

        # Random target inside bounding box
        target_x = random.randint(x_min, x_max)
        target_y = random.randint(y_min, y_max)

        # 50/50 chance: straight-ish vs curved move
        if random.random() < 0.5:
            smooth_move_curve(start, (target_x, target_y), steps=random.randint(50, 120))
        else:
            smooth_move_curve(start, (target_x, target_y), steps=random.randint(30, 80))

        # Random short pause between movements
        time.sleep(random.uniform(0.2, 2.0))

        # Occasional click if enabled
        if clicks_enabled and random.random() < 0.03:
            pyautogui.click()
            time.sleep(random.uniform(0.1, 0.7))

        # Occasional scroll if enabled
        if scroll_enabled and random.random() < 0.06:
            scroll_dir = random.choice([-1, 1])
            burst_len = random.randint(2, 8)  # multiple ticks
            print(f"Scrolling {'up' if scroll_dir > 0 else 'down'} for {burst_len} ticks")
            for _ in range(burst_len):
                send_scroll(scroll_dir)
                time.sleep(random.uniform(0.1, 0.3))  # small pause between ticks
            time.sleep(random.uniform(1.0, 3.0))

# ---------------- Keyboard Controls ----------------
def on_release(key):
    global running, clicks_enabled, scroll_enabled, mover_thread
    if key == keyboard.Key.f8:
        if not running:
            print("Random mouse mover started")
            running = True
            mover_thread = threading.Thread(target=random_mouse_mover, daemon=True)
            mover_thread.start()
        else:
            print("Random mouse mover stopped")
            running = False
    elif key == keyboard.Key.f9:
        clicks_enabled = not clicks_enabled
        print(f"Mouse clicks {'enabled' if clicks_enabled else 'disabled'}")
    elif key == keyboard.Key.f10:
        scroll_enabled = not scroll_enabled
        print(f"Mouse scrolling {'enabled' if scroll_enabled else 'disabled'}")
    elif key == keyboard.Key.esc:
        running = False
        print("Exiting...")
        return False

# ---------------- Main ----------------
with keyboard.Listener(on_release=on_release) as kl:
    print("Random human-like mouse mover")
    print("F8: Start/Stop mover")
    print("F9: Toggle clicks")
    print("F10: Toggle scrolling")
    print("Esc: Exit")
    kl.join()
