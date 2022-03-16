from pprint import pprint
from configure import readOptionJSON
from transcode import transcode, get_dst
import ffmpegio
from os import path

optfile = r"dev\fluorofix.json"
# src = r"data\9569\Pt9569_Visit1.mpg"
src = r"data\280\Pt280_Visit2.mpg"
# src = r"data\6312\Pt6312_Visit4.mp4" # 9/10
# src = r"data\6312\Pt6312_Visit5.mp4" # 9/10
# src = r"data\280\Pt280_Visit3.mp4" # 8/7

opts = readOptionJSON(optfile)
print(opts)

opts["OutputFolder"] = "data"
opts["OutputSuffix"] = "_fixed_nsq"
opts["Overwrite"] = True

crf = "original"
vf = (
    lambda crf: f"drawtext='font=monospace:fontcolor=white:fontsize=12:text=t = %{{pts}} s\ncrf={crf}':x=10:y=10"
)

cap_img = False
to_img = {"ss": 32, "vframes": 30, "overwrite": True}  # modify the timing & # frames
# to_img = {"ss": 33.066367, "vframes": 2, "overwrite": True} # 280.2
if cap_img:
    ffmpegio.transcode(src, f"data/frame_original_%d.png", vf=vf(crf), **to_img)

opts["OutputOptions"]["t"] = 30
opts["Overwrite"] = True
# opts["OutputOptions"]["crf"] = 8

# dst = transcode(src, opts)

src_bps = ffmpegio.probe.video_streams_basic(src)[0]["bit_rate"]
stop_bps = src.endswith(".mp4")
print(f"original bitrate={src_bps}")

for crf in range(0, 24, 2):
    opts["OutputOptions"]["crf"] = crf
    # opts['OutputSuffix'] = f'_crf={crf}'
    dst = get_dst(src, opts)
    # if not path.exists(dst):
    dst = transcode(src, opts)

    if cap_img:
        ffmpegio.transcode(dst, f"data/frame_crf={crf}_%d.png", vf=vf(crf), **to_img)

    dst_bps = ffmpegio.probe.video_streams_basic(dst)[0]["bit_rate"]
    print(f"crf={crf} bitrate={dst_bps}")
    if stop_bps and dst_bps < src_bps:
        break
