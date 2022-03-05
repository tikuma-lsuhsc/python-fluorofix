from ffmpegio import probe
from os import path, walk

from . import configure


def find_profile(info, profiles):
    def test(keys):
        for k, v in keys.items():
            if str(info[k]) != v:
                return False
        return True

    return next((k for k, p in profiles.items() if test(p[0])))


def get_dst(ctx, src):
    srcfolder, srcfile = path.split(src)
    dstfile = path.splitext(srcfile)[0]
    dstsuffix = ctx["OutputSuffix"]
    if dstsuffix is not None:
        dstfile += dstsuffix
    dstfile += ctx["OutputExt"]
    dstfolder = ctx["OutputFolder"]
    return path.join(
        dstfolder if dstfolder else srcfolder if dstsuffix else path.expanduser("~"),
        dstfile,
    )


def check_file(ctx, filepath):

    res = {"info": None, "prof": None, "dst": None}

    try:
        res["info"] = info = probe.video_streams_basic(filepath)[0]
        try:
            res["prof"] = find_profile(info, ctx["Profiles"])
            res["dst"] = get_dst(ctx, filepath)
        except:
            pass
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

    return {file: check_file(ctx, file) for file in vid_files}, {
        file: configure.readOptionJSON(file) for file in json_files
    }
