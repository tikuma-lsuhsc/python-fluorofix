from pprint import pprint
from ffmpegio import transcode as fftranscode, probe


urlin = r"data\1080p.mp4"
# urlin = r"data\6904\Pt6904_Visit3.mp4" #r"data\1080p.mp4"
urlout = r"data\1080p_setsar.mp4"


# fftranscode(urlin, urlout, overwrite=True, vf="setsar=10/11", an=None, t=5)
fftranscode(urlin, urlout, overwrite=True, aspect=f"{1920*11//10}:1080", an=None, t=5)

pprint(probe.video_streams_basic(urlin))
pprint(probe.video_streams_basic(urlout))
