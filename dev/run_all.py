from glob import glob
from os import path, makedirs
import re
import ffmpegio
from pprint import pprint
from  matplotlib import pyplot as plt

import logging
logging.basicConfig(level=logging.DEBUG)

datadir = 'data'
outdir = 'fixed'
srcfiles = sorted(glob(f"{path.join(datadir,'**','*.mpg')}")+glob(f"{path.join(datadir,'**','*.mp4')}"))

sar = {480: (8,9), 1080: (9, 10)}
height = {480: 540, 1080: 1200}
circ = {480: (45,8,530,530), 1080: (396,92,1140,1140)}

fg = {k: f"scale=h={h},crop={c[2]}:{c[3]}:{c[0]}:{c[1]},geq='if(lt(pow(X-{c[2]/2},2) + pow(Y-{c[3]/2},2),{(c[3]//2)**2}),lum(X,Y),0)':cb(X\,Y):cr(X\,Y),setsar=1" for (k,h),c in zip(height.items(),circ.values())}

args = {'inputs':[['',None]],'outputs':[['',{'vf': None,'crf':20}]], 'global_options':{'n':None}}

for src in srcfiles:
    info = ffmpegio.probe.video_streams_basic(src)[0]

    try:
        height = info['height']
    except:
        continue

    dst = re.sub(datadir,outdir,path.splitext(src)[0]+'.mp4',1)
    
    makedirs(path.split(dst)[0],exist_ok=True)

    args['inputs'][0][0] = src
    args['outputs'][0][0] = dst
    args['outputs'][0][1]['vf'] = fg[height]
    try:
        ffmpegio.process.run(args,capture_log=False)
    except:
        pass
    # exit()
