from fractions import Fraction
from ffmpegio import image, probe, process
import numpy as np
import re
from tempfile import TemporaryDirectory
from os import path, makedirs


def create_mask(pngfile, dia):
    I = np.zeros((dia, dia, 4), "u1")
    X, Y = np.meshgrid(range(dia), range(dia))
    r = dia / 2
    I[:, :, 3] = 255 * ((X - r) ** 2 + (Y - r) ** 2 > r ** 2)
    image.write(pngfile, I)


def find_profile(info, profiles):
    def test(key):
        for s in re.split(r"(?<!\\)(?:\\\\)*\:", key):
            k, v = s.split("=", 1)
            if str(info[k]) != v:
                return False
        return True

    return next((p for k, p in profiles.items() if test(k)))


def form_filters(info, p, config):
    filters = []

    sar = p.get("sar", info.get("sample_aspect_ratio", None))
    if sar is not None:
        if isinstance(sar, Fraction):
            sar = [sar.numerator, sar.denominator]
        if (sar[0] < sar[1]) == (config["SquarePixel"] > 0):
            info["height"] = h = info["height"] * sar[1] // sar[0]
            filters.append(f"scale=height={h}")
        elif (sar[0] > sar[1]) == (config["SquarePixel"] < 0):
            info["width"] = w = info["width"] * sar[0] // sar[1]
            filters.append(f"scale={w}")
    if config["SquarePixel"]:
        filters.append(f"setsar=1:1")

    if "circ" in p:
        x0, y0, dia = p["circ"]
        if sar is not None and config["SquarePixel"] < 0:
            # params are defined assuming stretching
            s = min(sar)/max(sar)
            dia *= s**2.0
            x0 *= s
            y0 *= s
        dia = round(dia)
        filters.append(f"crop={dia}:{dia}:{round(x0)}:{round(y0)}")
        fg = ",".join(filters)
        return fg, dia
    else:
        raise ValueError("no mask specified")


def get_dst(src, config):
    srcfolder, srcfile = path.split(src)
    dstfile = path.splitext(srcfile)[0]
    dstsuffix = config["OutputSuffix"]
    if dstsuffix is not None:
        dstfile += dstsuffix
    dstfile += config["OutputExt"]
    dstfolder = config["OutputFolder"]
    return path.join(
        dstfolder if dstfolder else srcfolder if dstsuffix else path.expanduser("~"),
        dstfile,
    )


def transcode(src, config):

    info = probe.video_streams_basic(src)[0]

    prof = find_profile(info, config["Profiles"])

    dst = get_dst(src, config)
    makedirs(path.split(dst)[0], exist_ok=True)

    args = {
        "inputs": [(src, None)],
        "outputs": [(dst, {**config["OutputOptions"]})],
        "global_options": {"hide_banner": None, "loglevel": "fatal"},
    }
    args["global_options"]["y" if config["Overwrite"] else "n"] = None

    fg, circ_dia = form_filters(info, prof, config)

    with TemporaryDirectory() as dir:  # TemporaryFile(suffix='.png') as tmpfile:

        if circ_dia:
            pngfile = path.join(dir, "mask.png")
            create_mask(pngfile, circ_dia)
            args["inputs"].append((pngfile, None))
            fg = f"{fg}[vid];[vid][1:v]overlay"

        args["global_options"]["filter_complex"] = f"[0:v]{fg}"

        if process.run(args, capture_log=False).returncode:
            raise RuntimeError("FFmpeg execution failed...")

    return dst


if __name__ == "__main__":
    import configure

    config = configure.defaultOption()
    url = r"data\1080p.mp4"
    dst_url = transcode(url, config)
    print(probe.video_streams_basic(dst_url)[0])
