import logging
import re
from ffmpegio import probe
from os import path, walk

from . import configure

def remove_file_protocol(url):
    return re.sub(r"^file://(localhost)?(/)?", "", url, flags=re.IGNORECASE)


def is_video(filepath, profiles=None):

    filepath = remove_file_protocol(filepath)

    try:
        info = probe.video_streams_basic(filepath)[0]
        found = True
    except:
        found = False

    prof = None
    try:
        if found:
            prof = find_profile(info, profiles)
    finally:
        return found, prof


def find_profile(info, profiles):
    def test(keys):
        for k, v in keys.items():
            if str(info[k]) != str(v):
                return False
        return True

    return next((k for k, p in profiles.items() if test(p[0])))


def get_dst(ctx, src, dstfile=None, dstdir=None):
    """generate output filepath

    :param ctx: fluorofix context
    :type ctx: dict
    :param src: source file
    :type src: str
    :param dstfile: user-specified output file name, defaults to None
    :type dstfile: str, optional
    :param dstdir: user-specified output directory, defaults to None
    :type dstdir: str, optional
    :return: output filepath
    :rtype: str

    """
    srcfolder, srcfile = path.split(src)
    if not path.exists(srcfolder):
        srcfolder = ""

    if dstfile:
        dstfolder, dstfile = path.split(dstfile)
    else:
        dstfolder = None

    if dstdir:
        dstfolder = dstdir

    if dstfile:
        dstfile, dstext = path.splitext(dstfile)

    else:
        dstfile = path.splitext(srcfile)[0]
        dstfile += ctx.get("OutputSuffix", "")
        dstext = ""

    dstfile += dstext or ctx.get("OutputExt", ".mp4")

    if not (dstdir or (dstfile and dstfolder)):
        # if dstfolder not specified, use one of:
        # 1. default output path
        # 2. folder of the input file
        # 3. user's home folder
        dstfolder = ctx.get("OutputFolder", "") or (
            srcfolder if srcfolder and srcfile != dstfile else path.expanduser("~")
        )

    dst = path.join(dstfolder, dstfile)

    # in/out files must be different
    try:
        if path.samefile(src, dst):
            raise ValueError("Cannot overwrite the input file.")
    except:
        pass  # dst does not exist (or both...)

    return dst


def check_file(ctx, filepath):

    res = {"prof": None, "dst": None}

    try:
        info = probe.video_streams_basic(filepath)[0]
        assert info["codec_name"] != "ansi"
        try:
            res["prof"] = find_profile(info, ctx["Profiles"])
            res["dst"] = get_dst(ctx, filepath)
        except Exception as e:
            logging.warning(e)
    except:
        pass

    return res


def analyze_files(ctx, paths):
    # scan for json file in the input
    vid_files, json_files = set(), set()

    for x in paths:
        if path.isdir(x):
            for y in [path.join(p, f) for p, _, fs in walk(x) for f in fs]:
                (vid_files, json_files)[y.endswith(".json")].add(y)
        else:
            (vid_files, json_files)[x.endswith(".json")].add(x)

    return {
        file: data
        for file, data in [(file, check_file(ctx, file)) for file in vid_files]
        if data["prof"] is not None
    }, {file: configure.readOptionJSON(file) for file in json_files}
