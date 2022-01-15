import PyInstaller.__main__

import os
from ffmpegio.ffmpeg import FFMPEG_BIN, FFPROBE_BIN

add_ffmpeg = f'{FFMPEG_BIN}{os.pathsep}bin'
add_ffprobe = f'{FFPROBE_BIN}{os.pathsep}bin'

onefile_or_ondir = '--onefile' if 1 else '--onedir'

PyInstaller.__main__.run(
    [
        onefile_or_ondir,
        f"--add-binary={add_ffmpeg}",
        f"--add-binary={add_ffprobe}",
        # f"--icon=%s" % os.path.join("resource", "path", "icon.ico"),
        os.path.join("dev", "fluorofix.py"),
    ]
)
