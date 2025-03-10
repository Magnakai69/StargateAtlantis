import os
import time
import subprocess
import psutil
from pynput import keyboard
import threading
import win32api  # Requires: pip install pywin32

# Path to MPV
MPV_PATH = r"C:\Program Files\MPV\mpv.exe"

# Video files
videos = [
    {"path": r"C:\Users\YourProfile\Videos\ZPMDiagnostics.mp4"},
    {"path": r"C:\Users\YourProfile\Videos\AtlantisChairDiag.mp4"},
    {"path": r"C:\Users\YourProfile\Videos\AtlantisCityScan.mp4"},
    {"path": r"C:\Users\YourProfile\Videos\AtlantisControlScreen.mp4"},
    {"path": r"C:\Users\YourProfile\Videos\PegasusStargateDiagnostics.mp4"},
    {"path": r"C:\Users\YourProfile\Videos\AtlantisScan.mp4"},
    {"path": r"C:\Users\YourProfile\Videos\AtlantisScreensaver.mp4"}
]

# Verify paths
if not os.path.exists(MPV_PATH):
    raise FileNotFoundError(f"MPV not found at: {MPV_PATH}")
for video in videos:
    if not os.path.exists(video["path"]):
        raise FileNotFoundError(f"Video file not found: {video['path']}")

# Global flags
exit_flag = False
rotate_flag = threading.Event()

# Stop all MPV instances
def stop_mpv():
    print("\nStopping all MPV instances...")
    for proc in psutil.process_iter(attrs=['pid', 'name']):
        if proc.info['name'] and "mpv" in proc.info['name'].lower():
            try:
                proc.terminate()
                time.sleep(0.5)
            except:
                proc.kill()
    print("All MPV instances closed.")

# Get monitor info
monitors = win32api.EnumDisplayMonitors()
monitor_map = {}
for i, mon in enumerate(monitors):
    left, top, right, bottom = mon[2]
    width = right - left
    height = bottom - top
    monitor_map[i] = {"left": left, "top": top, "width": width, "height": height}
print("Detected monitors (screen, x, y, width, height):", [(i, d["left"], d["top"], d["width"], d["height"]) for i, d in monitor_map.items()])

# Assign initial screen numbers to videos
if len(monitors) != len(videos):
    print(f"Warning: {len(monitors)} monitors detected, but {len(videos)} videos provided")
for i, video in enumerate(videos):
    video["screen"] = i % len(monitors)

def start_mpv_instances(videos_list):
    mpv_processes = []
    stop_mpv()  # Ensure clean start
    for i, video in enumerate(videos_list):
        if i < len(monitors):
            screen = video["screen"]
            bounds = monitor_map[screen]
            command = (
                f'"{MPV_PATH}" "{video["path"]}" '
                f'--loop-file '
                f'--fullscreen '
                f'--fs-screen={screen} '  # Specify fullscreen screen
                f'--geometry={bounds["width"]}x{bounds["height"]}+{bounds["left"]}+{bounds["top"]} '
                f'--no-osc '
                f'--no-input-default-bindings '
                f'--no-border '
                f'--log-file=mpv_log_screen_{screen}.txt'  # Add logging for debugging
            )
            try:
                proc = subprocess.Popen(command, shell=True)
                mpv_processes.append(proc)
                print(f"✅ Started MPV for: {video['path']} on screen {screen} at ({bounds['left']}, {bounds['top']}, {bounds['width']}, {bounds['height']})")
                time.sleep(1)  # Add delay between launches
            except subprocess.SubprocessError as e:
                print(f"❌ Failed to start MPV for {video['path']}: {e}")
    return mpv_processes

# Rotation function
def rotate_videos():
    while not exit_flag:
        rotate_flag.wait(timeout=300)  # 5 minutes = 300 seconds
        if exit_flag:
            break
        print("\nRotating videos...")
        current_screens = [v["screen"] for v in videos]
        rotated_screens = current_screens[1:] + current_screens[:1]
        for i, video in enumerate(videos):
            video["screen"] = rotated_screens[i]
        global mpv_processes
        mpv_processes = start_mpv_instances(videos)

# Keypress listener
def on_press(key):
    global exit_flag
    try:
        if key == keyboard.Key.esc:
            exit_flag = True
            rotate_flag.set()
            return False
    except AttributeError:
        pass

# Initial start
if any("mpv" in proc.info['name'].lower() for proc in psutil.process_iter(attrs=['name'])):
    stop_mpv()
mpv_processes = start_mpv_instances(videos)

# Start rotation thread
rotation_thread = threading.Thread(target=rotate_videos)
rotation_thread.start()

# Start keypress listener
listener_thread = threading.Thread(target=lambda: keyboard.Listener(on_press=on_press).start())
listener_thread.start()

print("\n✅ Setup complete. Videos will rotate every 5 minutes across monitors. Press 'Esc' to stop.")

# Main loop
while not exit_flag:
    time.sleep(1)

# Cleanup
stop_mpv()
rotation_thread.join()
listener_thread.join()
print("Screensaver stopped.")