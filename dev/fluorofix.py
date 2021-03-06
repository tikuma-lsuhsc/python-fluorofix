import sys
from os import path, walk
from configure import readOptionJSON
from transcode import transcode

# from tqdm import tqdm
import ffmpegio

# print(f"current dir: {getcwd()}")

if not getattr(sys, "frozen", False):
    print("non-exe test run")
    sys.argv = [
        sys.executable,
        # "data\\280\\Pt280_Visit1.avi",
        r"data\florofix items"
        # r"data\florofix items\new_1080p.json",
        # r"data\florofix items\cc 6122  cpbar with pharyngeal emtying Rec1_hd_video_2022_06_01T12_19_09_066.mp4",
        # r"data\florofix items\DUPAN 5 2 2022 UES and E.mp4"
        # "data\\480p.mp4",
        # "data\\1080p.mp4",
    ]

# read the config file
if path.basename(sys.executable).startswith("python"):
    optfile = path.splitext(__file__)[0] + ".json"
else:
    optfile = path.splitext(sys.executable)[0] + ".json"
    try:
        basedir = sys._MEIPASS
    except:
        basedir = path.dirname(sys.executable)
    ffmpeg_bin = path.join(basedir, "bin")
    ffmpegio.set_path(ffmpeg_bin)

opts = readOptionJSON(optfile)

del sys.argv[0]
nfiles = len(sys.argv)  # number of input files

if nfiles == 0:
    print("No files to process. Exiting...")
    sys.exit(0)

# scan for json file in the input
vid_files, json_files = set(), set()

for x in sys.argv:
    if path.isdir(x):
        for y in [path.join(p, f) for p, _, fs in walk(x) for f in fs]:
            (vid_files, json_files)[y.endswith(".json")].add(y)
    else:
        (vid_files, json_files)[x.endswith(".json")].add(x)

if len(json_files):
    opts = readOptionJSON(tuple(json_files)[-1], opts, update_file=False)

n = len(vid_files)
fail_msg = "failed" if opts["Overwrite"] else "failed or file already exists"
# with tqdm(total=n) as pbar:
for i, file in enumerate(vid_files):
    print(f"({i+1}/{n}) {file}...")
    try:
        # pbar.set_description(path.basename(file))
        # pbar.update(i)
        transcode(file, opts)
    except Exception as err:
        print(f"   skipping: {err}")

input("\nPress Enter to Exit...")
