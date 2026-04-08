import subprocess
import time
import os


def play_sound(sound_file='Funk.aiff', volume=4.0, repeats=2, rate=1):
    """
    Play a system sound louder and longer.

    - volume: 0.0 to ~2.0+ (1.0 = normal, 2.0 = max boost via afplay)
    - repeats: how many times to loop the sound
    - rate: playback speed (0.5 = slow, 1.0 = normal, 2.0 = fast)
    """
    for _ in range(repeats):
        subprocess.run([
            "afplay",
            "-v", str(volume),  # volume multiplier
            "-r", str(rate),  # playback rate
            f"/System/Library/Sounds/{sound_file}"
        ])

def all_sounds():
    sounds_dir = "/System/Library/Sounds"
    for f in sorted(os.listdir(sounds_dir)):
        print(f)
        play_sound(f)
        time.sleep(0.5)