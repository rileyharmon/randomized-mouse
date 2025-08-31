import ctypes
import random
import time
import json
import threading
from pynput import mouse, keyboard
import pyautogui

# ---------------- Windows SendInput Setup ----------------
PUL = ctypes.POINTER(ctypes.c_ulong)
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000

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

def smooth_move_hw(start_pos, end_pos, steps=100):
    x0, y0 = start_pos
    x1, y1 = end_pos
    for i in range(1, steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t + random.uniform(-0.2, 0.2)
        y = y0 + (y1 - y0) * t + random.uniform(-0.2, 0.2)
        send_input(x, y)

# ---------------- Global state ----------------
events = []
recording = False  # Auto-record OFF
playing = False
stop_playback = False
loop_playback = True  # default ON
start_time = None
playback_thread = None

SKIP_FACTOR = 10
MIN_DELTA = 0.1

print("Ready. Press F9 to start recording. F12 toggles loop playback (default ON).")

# ---------------- Event Handlers ----------------
def on_click(x, y, button, pressed):
    global events, start_time
    if recording and start_time is not None:
        events.append({
            "type": "mouse_click",
            "button": str(button),
            "pressed": pressed,
            "pos": (x, y),
            "time": time.time() - start_time
        })

def on_move(x, y):
    global events, start_time
    if recording and start_time is not None:
        events.append({
            "type": "mouse_move",
            "pos": (x, y),
            "time": time.time() - start_time
        })

def on_scroll(x, y, dx, dy):
    global events, start_time
    if recording and start_time is not None:
        events.append({
            "type": "mouse_scroll",
            "dx": dx,
            "dy": dy,
            "time": time.time() - start_time
        })

def on_press(key):
    global events, start_time
    if recording and start_time is not None:
        try:
            events.append({
                "type": "key_press",
                "key": key.char,
                "time": time.time() - start_time
            })
        except AttributeError:
            events.append({
                "type": "key_press",
                "key": str(key),
                "time": time.time() - start_time
            })

def on_release(key):
    global recording, playing, stop_playback, playback_thread, events, start_time, loop_playback

    if key == keyboard.Key.esc:
        if playing:
            print("Stopping playback...")
            stop_playback = True
        elif recording:
            recording = False
            print("Recording paused")
        else:
            print("Esc pressed, nothing to stop.")

    elif key == keyboard.Key.f9:
        recording = not recording
        if recording:
            start_time = time.time()
            events.clear()
            print("Recording started")
        else:
            print("Recording paused")

    elif key == keyboard.Key.f10:
        try:
            # Map special keys for PyAutoGUI
            for e in events:
                if e.get("type") == "key_press":
                    k = e["key"]
                    if k.startswith("Key."):
                        key_map = {
                            "Key.space": "space",
                            "Key.enter": "enter",
                            "Key.tab": "tab",
                            "Key.backspace": "backspace",
                            "Key.shift": "shift",
                            "Key.ctrl_l": "ctrl",
                            "Key.ctrl_r": "ctrl",
                            "Key.alt_l": "alt",
                            "Key.alt_r": "alt",
                            "Key.esc": "esc",
                        }
                        e["key"] = key_map.get(k, "")
            with open("activity_log.json", "w") as f:
                json.dump(events, f, indent=2)
            print(f"Saved {len(events)} events to activity_log.json (overwritten)")
        except Exception as e:
            print(f"Error saving events: {e}")

    elif key == keyboard.Key.f11:
        if not playing:
            try:
                with open("activity_log.json", "r") as f:
                    playback_events = json.load(f)
                print("Playing back events...")
                stop_playback = False
                playing = True
                playback_thread = threading.Thread(
                    target=play_events,
                    args=(playback_events,),
                    daemon=True
                )
                playback_thread.start()
            except FileNotFoundError:
                print("No log file found!")

    elif key == keyboard.Key.f12:
        loop_playback = not loop_playback
        print(f"Loop playback {'ON' if loop_playback else 'OFF'}")

# ---------------- Playback ----------------
def play_events(playback_events):
    global playing, stop_playback
    if not playback_events:
        playing = False
        return

    while not stop_playback:
        last_time = playback_events[0]["time"]
        count = 0

        for event in playback_events:
            if stop_playback:
                break

            count += 1
            if event["type"] == "mouse_move" and count % SKIP_FACTOR != 0:
                continue

            delta = event["time"] - last_time
            if delta > MIN_DELTA:
                time.sleep(MIN_DELTA)
            last_time = event["time"]

            if stop_playback:
                break

            try:
                if event["type"] == "mouse_move":
                    start = pyautogui.position()
                    smooth_move_hw(start, event["pos"], steps=random.randint(50, 150))
                elif event["type"] == "mouse_click":
                    btn = event["button"].split('.')[-1]
                    if event["pressed"]:
                        pyautogui.mouseDown(*event["pos"], button=btn)
                    else:
                        pyautogui.mouseUp(*event["pos"], button=btn)
                elif event["type"] == "mouse_scroll":
                    pyautogui.scroll(event["dy"])
                elif event["type"] == "key_press":
                    key_name = event["key"]
                    if key_name:
                        pyautogui.press(key_name)
            except Exception:
                pass

        if not loop_playback:
            break

    playing = False
    stop_playback = False
    print("Playback finished")

# ---------------- Start listeners ----------------
with mouse.Listener(on_click=on_click, on_move=on_move, on_scroll=on_scroll) as ml, \
     keyboard.Listener(on_press=on_press, on_release=on_release) as kl:
    ml.join()
    kl.join()
