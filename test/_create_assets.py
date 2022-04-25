from subprocess import PIPE
from ffmpegio import ffmpeg, ffprobe
from os import path
import random

t = 5
s = 120

wh = ((720, 480), (1280, 720), (1920, 1080))

for w, h in wh:

    nw = w // s
    nh = h // s

    ntotal = nw * nh

    outfile = path.join(path.dirname(__file__), "assets", f"colorchart_{w}x{h}.mp4")

    copts = [f"#{x:06x}" for x in random.sample(range(256**3), ntotal)]

    cmds = ";".join([f"{i} drawbox c {c}" for i, c in enumerate(copts)])

    # print(ntotal)
    ffmpeg(
        [
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=s={s}x{s}:r=1:d={ntotal},sendcmd='{cmds}',drawbox=w={s}:h={s}:t=fill,tile={nw}x{nh},setpts=N/TB",
            # f"colorchart=s={w}x{h}:r=1:patch_size={s}x{s}",
            "-r",
            "30",
            "-t",
            str(t),
            outfile,
        ]
    )
