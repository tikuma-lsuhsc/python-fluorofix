from ffmpegio import probe
from os import path, walk

from . import configure


def find_profile(info, profiles):
    def test(keys):
        for k, v in keys.items():
            if str(info[k]) != str(v):
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

    res = {"prof": None, "dst": None}

    try:
        info = probe.video_streams_basic(filepath)[0]
        assert info["codec_name"] != "ansi"
        try:
            res["prof"] = find_profile(info, ctx["Profiles"])
            res["dst"] = get_dst(ctx, filepath)
        except Exception as e:
            print(e)
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
