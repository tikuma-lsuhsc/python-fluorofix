from pprint import pprint
from configure import readOptionJSON
from transcode import transcode
import ffmpegio

optfile = r"dev\fluorofix.json"
src = r"data\9569\Pt9569_Visit1.mpg"

opts = readOptionJSON(optfile)
print(opts)

opts["OutputFolder"] = "data"
opts["OutputSuffix"] = "_fixed_nsq"
opts["Overwrite"] = True

crf = "original"
vf = (
    lambda crf: f"drawtext='font=monospace:fontcolor=white:fontsize=12:text=t = %{{pts}} s\ncrf={crf}':x=10:y=10"
)

to_img = {"ss": 7.21, "vframes": 1, "overwrite": True}
ffmpegio.transcode(src, f"data/frame_original.png", vf=vf(crf), **to_img)

opts["OutputOptions"]["t"] = 8

for crf in range(0, 24, 2):
    opts["OutputOptions"]["crf"] = crf
    dst = transcode(src, opts)
    ffmpegio.transcode(dst, f"data/frame_crf={crf}.png", vf=vf(crf), **to_img)

pprint(ffmpegio.probe.full_details(src))
pprint(ffmpegio.probe.full_details(r'data/Pt9569_Visit1_fixed_nsq.mp4'))
