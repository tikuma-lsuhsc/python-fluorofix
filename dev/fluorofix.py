import sys
from os import path
from configure import readOptionJSON
from transcode import transcode
from tqdm import tqdm

if not getattr(sys, "frozen", False):
    print("non-exe test run")
    sys.argv = [
        "fluorofix",
        "data\\480p.mp4",
        "data\\1080p.mp4",
    ]

# read the config file
if path.basename(sys.executable).startswith("python"):
    optfile = path.splitext(__file__)[0] + ".json"
else:
    optfile = path.splitext(sys.executable)[0] + ".json"

opts = readOptionJSON(optfile)

del sys.argv[0]
nfiles = len(sys.argv)  # number of input files

if nfiles == 0:
    print("No files to process. Exiting...")
    sys.exit(0)

# scan for json file in the input
vid_files, json_files = [], []
for x in sys.argv:
    (vid_files, json_files)[x.endswith(".json")].append(x)

if len(json_files):
    opts = readOptionJSON(json_files[-1], opts, update_file=False)

n = len(vid_files)
fail_msg = "failed" if opts["Overwrite"] else "failed or file already exists"
with tqdm(total=n) as pbar:
    for i, file in enumerate(vid_files):
        try:
            pbar.set_description(path.basename(file))
            pbar.update(i)
            transcode(file, opts)
        except Exception as err:
            pass#print(f"({i}/{n}) {file}... {fail_msg}")

input("\nPress Enter to Exit...")
