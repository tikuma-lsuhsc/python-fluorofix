from os import path, walk
from configure import readOptionJSON
from transcode import transcode

optfile = "dev/fluorofix.json"
opts = readOptionJSON(optfile)
opts_nsq = {**opts, "SquarePixel": 0, "OutputSuffix": "_nsq"}

for file in [path.join(p, f) for p, _, fs in walk("data") for f in fs]:
    if not (file.endswith(".mp4") or file.endswith(".mpg")):
        continue
    print(f"processing {file}...")
    try:
        transcode(file, opts_nsq)
        print(f"done.")
    except Exception as err:
        print(f"   skipping: {err}")
