from fractions import Fraction
from ffmpegio import probe, ffmpegprocess, transcode as fftranscode, FilterGraph
import re
from tempfile import TemporaryDirectory
from os import path, makedirs


def create_mask(pngfile, dia, sar=None):
    r = dia / 2
    filtspec = [
        [
            ("color", {"c": "black", "s": f"{dia}x{dia}", "r": 1, "d": 1}),
            "format=rgba",
            (
                "geq",
                {
                    "lum": "lum(X, Y)",
                    "a": f"if(gt((X-{r})^2+(Y-{r})^2,{r**2}),255,0)",
                },
            ),
        ],
    ]

    if sar is not None:
        sar = sar[0] / sar[1]
        filtspec[0].append(
            (
                "scale",
                {"w": dia, "h": dia * sar} if sar < 1 else {"w": dia / sar, "h": dia},
            )
        )

    fftranscode(
        FilterGraph(filtspec),
        pngfile,
        f_in="lavfi",
        pix_fmt="ya8",
        vframes=1,
        overwrite=True,
    )



def form_filters(info, p, config):

    if "circ" not in p:
        raise ValueError("no mask specified")

    filters = []

    h = info["height"]
    w = info["width"]
    sar_spec = p.get("sar", None)  # SAR in profile takes precedence over video header
    sar = sar_spec if sar_spec is not None else info.get("sample_aspect_ratio", None)
    if isinstance(sar, Fraction):
        sar = [sar.numerator, sar.denominator]

    if config["SquarePixel"] == 0:
        if sar_spec is not None:  # specify the profile SAR
            filters.append(f"setsar={sar_spec[0]}/{sar_spec[1]}")

        x0, y0, dia = p["circ"]
        wc = hc = dia
        if sar is not None:
            # profile params are defined assuming stretching
            if sar[0] < sar[1]:
                r = sar[0] / sar[1]
                hc *= r
                y0 *= r
            else:
                r = sar[1] / sar[0]
                wc *= r
                x0 *= r
        filters.append(f"crop={wc}:{hc}:{x0}:{y0}")
    else:
        # if pixels are to be squared
        if sar is not None:
            # if sar_spec is not None and
            # specify
            if (sar[0] < sar[1]) == (config["SquarePixel"] > 0):
                h = info["height"] * sar[1] // sar[0]
                filters.append(f"scale=height={h}")
            elif (sar[0] > sar[1]) == (config["SquarePixel"] < 0):
                w = info["width"] * sar[0] // sar[1]
                filters.append(f"scale={w}")
        filters.append(f"setsar=1:1")

        x0, y0, dia = p["circ"]
        if sar is not None and config["SquarePixel"] < 0:
            # profile params are defined assuming stretching
            s = min(sar) / max(sar)
            dia *= s ** 2.0
            x0 *= s
            y0 *= s
        dia = round(dia)
        w = dia if w > x0 + dia else w - x0
        h = dia if h > y0 + dia else h - y0
        filters.append(f"crop={w}:{h}:{round(x0)}:{round(y0)}")
    fg = ",".join(filters)
    return fg, dia, (None if config["SquarePixel"] else sar)



def transcode(src, config):

    try:
        info = probe.video_streams_basic(src)[0]
    except:
        raise ValueError("not a video file")

    try:
        prof = find_profile(info, config["Profiles"])
    except:
        raise ValueError("no matching profile found")

    dst = get_dst(src, config)
    makedirs(path.split(dst)[0], exist_ok=True)

    args = {
        "inputs": [(src, None)],
        "outputs": [(dst, {**config["OutputOptions"]})],
        "global_options": {"hide_banner": None, "loglevel": "fatal"},
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
