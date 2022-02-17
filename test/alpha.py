from fractions import Fraction
import logging
from pprint import pprint

logging.basicConfig(level=logging.DEBUG)
# import ffmpegio

# from matplotlib import pyplot as plt


# h = 1280
# w = 1920
# x0 = 396
# y0 = 92
# d = 1140
# r = d / 2
# xc = x0 + r
# yc = y0 + r

# vfsrc = ffmpegio.FilterGraph(
#     filter_specs=[
#         [
#             ("color", {"c": "black", "s": f"{w}x{h}", "r": 1, "d": 1}),
#             "format=rgba",
#             (
#                 "geq",
#                 {
#                     'lum': 'lum(X, Y)',
#                     "a": f"if(gt((X-{xc})^2+(Y-{yc})^2,{r**2}),255,0)",
#                 },
#             ),
#         ],
#     ],
# )

# ffmpegio.transcode(
#     vfsrc, "test/mask.png", f_in="lavfi", pix_fmt="ya8", show_log=True, overwrite=True
# )

# pprint(ffmpegio.probe.video_streams_basic("test/mask.png"))

from dev import transcode

transcode.create_mask("test/mask.png", 1000, sar=None)
transcode.create_mask("test/mask1.png", 1000, sar=Fraction(8, 9))

# plt.imshow(I)
# plt.show()

# alpha = f"color=black:s={w}x{h}"

# ffmpeg -y -i "${ifn}" -i "_alpha01.png" -filter_complex "
# [1:v]loop=-1:size=2,scale=1280:720,setsar=1[alpha];

# [0:v]curves=preset=color_negative[vf];
# [0:v][alpha]alphamerge[vt];

# [vf][vt]overlay=shortest=1
# " -an "${pref}_${ifnb}.mp4"
