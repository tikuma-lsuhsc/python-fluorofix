from pprint import pprint
import sys
from os import path, walk, makedirs
from fluorofix.configure import readOptionJSON, defaultOption, convert_inkscape
from fluorofix.transcode import transcode, form_filters
import ffmpegio


def run(config, src):
    dst = probe.get_dst(config, src)
    makedirs(path.dirname(dst), exist_ok=True)

    args = {
        "inputs": [(src, {"hwaccel": "none"})],
        "outputs": [(dst, {**config["OutputOptions"]})],
        # "outputs": [("test.png", {"vframes": 1})],
        "global_options": {"hide_banner": None, "loglevel": "fatal"},
    }
    args["global_options"]["y" if config["Overwrite"] else "n"] = None

    args["global_options"]["filter_complex"] = form_filters(
        info, config["Profiles"][prof][1], config
    )

    if ffmpegio.ffmpegprocess.run(args, capture_log=None).returncode:
        raise RuntimeError("FFmpeg execution failed...")


if __name__ == "__main__":
    boxdir = r"C:\Users\tikum\Box"

    new_files = [
        "cc 6122  cpbar with pharyngeal emtying Rec1_hd_video_2022_06_01T12_19_09_066.mp4",
        "DUPAN 5 2 2022 UES and E.mp4",
    ]
    ignore_files = [
        # *new_files,
        "aleJohn   NO Initation of pharyngeal swallow  with severe saliva pooling 2 4 2021 Rec1_hd_video_2021_02_04T16_07_41_099.mp4",
        "CAGE ZENKRec1_hd_video_2021_06_14T13_09_26_936.mp4",
    ]

    src_dir = path.join(boxdir, "BRSLP presentation", "FLOUROFIX ITEMS")
    json_file = path.join(src_dir, "new_1080p.json")

    config = defaultOption()
    config = readOptionJSON(json_file, config)
    config["Overwrite"] = True
    config["OutputFolder"] = r"data\florofix items"
    config["ApplyMask"] = True
    config['OutputOptions']['crf'] = 23
    pprint(config)

    from fluorofix import probe
    from ffmpegio import probe as ffprobe
    from glob import glob

    for src in glob(src_dir + "/*.mp4"):
        if path.basename(src) not in new_files:
            continue
        print(src)
        try:
            try:
                info = ffprobe.video_streams_basic(src)[0]
            except:
                raise ValueError("not a video file")

            try:
                prof = probe.find_profile(info, config["Profiles"])
            except:
                raise ValueError("no matching profile found")

            config["Profiles"][prof][1] = convert_inkscape(
                config["Profiles"][prof][1], info["height"]
            )

            run(config, src)
        except:
            pass
