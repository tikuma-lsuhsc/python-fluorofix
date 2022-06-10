from fractions import Fraction
from ffmpegio import probe, ffmpegprocess, transcode as fftranscode, FilterGraph
import re
from tempfile import TemporaryDirectory
from os import path, makedirs

import ffmpegio


def create_mask(dia, sar=None, color="black", x0=0, y0=0, w=None, h=None):
    """Create an FFmpeg filtergraph to generate a circular mask to deidentify

    :param dia: mask diameter in pixels
    :type dia: int
    :param sar: w/h sample aspect ratio, defaults to None
    :type sar: Fraction, optional
    :param color: mask color, defaults to "black"
    :type color: str, optional
    :returns: a filter chain spec
    """
    r = dia / 2

    if sar is None or sar[0] == sar[1]:
        # square frame with transparent circle
        sstr = f"{w or dia}x{h or dia}"
        astr = f"if(gt((X-{x0+r})^2+(Y-{y0+r})^2,{r**2}),255,0)"
    else:
        # rectangular frame with transparent oval
        sar = sar[0] / sar[1]
        if sar < 1:
            rx = r
            ry = r * sar
        else:
            rx = r / sar
            ry = r

        sstr = f"{w or round(2*rx)}x{h or round(2*ry)}"
        astr = f"if(gt((X-{x0+round(rx)})^2/{rx**2}+(Y-{y0+ry})^2/{ry**2},1),255,0)"

    return [
        ("color", {"c": color, "s": sstr}),
        "trim=end_frame=1",
        "format=ya8",
        ("geq", {"lum": "lum(X,Y)", "cb": "cb(X,Y)", "a": astr}),
    ]


def form_filters(info, p, config):

    fchain = []
    fg = [fchain]
    links = {}

    h = info["height"]
    w = info["width"]
    sar_spec = p.get("sar", None)  # SAR in profile takes precedence over video header
    sar = sar_spec if sar_spec is not None else info.get("sample_aspect_ratio", None)
    if isinstance(sar, Fraction):
        sar = [sar.numerator, sar.denominator]
    elif isinstance(sar, (int, float)):
        sar = [sar, 1]

    has_mask = "circ" in p
    is_nonsquare = sar is not None and sar[0] != sar[1]
    upscaling = config.get("Scaling", "up") != "down"

    # configure squaring pixels
    square_pixels = is_nonsquare and config["SquarePixel"]
    if square_pixels:
        # add scale filter + setsar filter
        if (sar[0] < sar[1]) == upscaling:
            h = 2 * round(h * sar[1] / sar[0] / 2)
            fchain.append(f"scale=h={h}")
        elif (sar[0] > sar[1]) == (config["SquarePixel"] < 0):
            w = 2 * round(w * sar[0] / sar[1] / 2)
            fchain.append(f"scale=w={w}:h={h}")
        fchain.append(f"setsar=1:1")

    # configure cropping setup
    # - cropping always occurs after scaling
    # - if pixel remain nonsquare, crop spec must be scaled first
    do_crop = config.get("CropVideo", True) and has_mask
    do_mask = config.get("ApplyMask", True) and has_mask
    if do_crop or do_mask:
        x0, y0, dia = p["circ"]

        if square_pixels and not upscaling:
            # profile params are defined assuming upscaling
            s = min(sar) / max(sar)
            dia = dia * s
            if sar[0] < sar[1]:
                x0 *= s
            else:
                y0 *= s

        hc = wc = dia

        if is_nonsquare and not square_pixels:
            # if not squaring, adjust cropping position
            if (sar[0] < sar[1]) == upscaling:
                s = sar[0] / sar[1] if upscaling else sar[1] / sar[0]
                hc = round(hc * s)
                y0 = round(y0 * s)
            else:
                s = sar[1] / sar[0] if upscaling else sar[0] / sar[1]
                wc = round(wc * s)
                y0 = round(y0 * s)

    if do_crop:
        hadj = h - (y0 + hc)
        if hadj < 0:
            hc += hadj
        wadj = w - (x0 + wc)
        if wadj < 0:
            wc += wadj

        fchain.append(f"crop={wc// 2 * 2}:{hc// 2 * 2}:{round(x0)}:{round(y0)}")

    # configure masking setup
    if do_mask:
        sar = None if (square_pixels or not is_nonsquare) else sar
        fg.append(
            mask_chain := create_mask(
                round(dia / 2) * 2 if do_crop else dia,
                sar,
                x0=0 if do_crop else x0,
                y0=0 if do_crop else y0,
                w=None if do_crop else w,
                h=None if do_crop else h,
            )
        )
        fg.append(["overlay"])
        links[(2, 0, 0)] = (0, len(fchain) - 1, 0)
        links[(2, 0, 1)] = (1, len(mask_chain) - 1, 0)

    return ffmpegio.FilterGraph(fg, links=links)


def transcode(src, config):

    try:
        info = probe.video_streams_basic(src)[0]
    except:
        raise ValueError("not a video file")

    try:
        prof = probe.find_profile(info, config["Profiles"])
    except:
        raise ValueError("no matching profile found")

    dst = probe.get_dst(config, src)
    makedirs(path.split(dst)[0], exist_ok=True)

    args = {
        "inputs": [(src, {"hwaccel": "none"})],
        "outputs": [(dst, {**config["OutputOptions"]})],
        "global_options": {"hide_banner": None, "loglevel": "debug"},
    }
    args["global_options"]["y" if config["Overwrite"] else "n"] = None

    fg, circ_dia, mask_sar = form_filters(info, prof, config)

    with TemporaryDirectory() as dir:  # TemporaryFile(suffix='.png') as tmpfile:

        if circ_dia:
            pngfile = path.join(dir, "mask.png")
            create_mask(pngfile, circ_dia, mask_sar)
            args["inputs"].append((pngfile, None))
            fg = f"{fg}[vid];[vid][1:v]overlay"

        args["global_options"]["filter_complex"] = f"[0:v]{fg}"

        if ffmpegprocess.run(args, capture_log=None).returncode:
            raise RuntimeError("FFmpeg execution failed...")

    return dst


if __name__ == "__main__":
    import configure

    config = configure.defaultOption()
    config["Overwrite"] = True
    config["SquarePixel"] = 0
    config["OutputSuffix"] = "_fixed_nsq"
    url = r"data\480p.mp4"
    # url = r"data\1080p.mp4"
    dst_url = transcode(url, config)

    print(probe.video_streams_basic(dst_url)[0])
