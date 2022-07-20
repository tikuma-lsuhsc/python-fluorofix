from copy import deepcopy
from fractions import Fraction
from ffmpegio import probe, ffmpegprocess, transcode as fftranscode, FilterGraph
import re
from tempfile import TemporaryDirectory
from os import path, makedirs

import ffmpegio


def create_mask_alpha(
    vidw, vidh, x0, y0, w, h, fill_in=False, is_rect=False, sx=1.0, sy=1.0
):
    """create a filterchain to form the alpha channel of a rectangular or ellipstical mask

    :param vidw: video frame width
    :type vidw: int
    :param vidh: video frame height
    :type vidh: int
    :param x0: left edge of the mask
    :type x0: numeric
    :param y0: upper edge of the mask
    :type y0: numeric
    :param w: width of the mask
    :type w: numeric
    :param h: height of the mask
    :type h: numeric
    :param fill_in: True to mask inside, False to mask outside, defaults to False
    :type fill_in: bool, optional
    :param is_rect: True for rectangular mask, False for elliptical mask, defaults to False
    :type is_rect: bool, optional
    :param color: color of the mask, defaults to "black"
    :type color: str, optional
    :return: ffmpeg filterchain expression
    :rtype: str
    """

    if is_rect:
        x1 = x0 + w
        y1 = y0 + (w or h)
        aif = f"between(X,{x0},{x1})*bewteen(Y,{y0},{y1})"
        if not fill_in:
            aif = f"not({aif})"
    else:
        ieq = "lt" if fill_in else "gt"
        rx = w / 2
        ry = (h or w) / 2
        xe = x0 + rx
        ye = y0 + ry
        rx2 = rx**2
        ry2 = ry**2
        astr = f"{ieq}((X-{xe})^2/{rx2}+(Y-{ye})^2/{ry2},1)"

    return f"nullsrc=s={vidw}x{vidh},format=grayscale,geq=lum='if({astr},255,0)'"


def create_mask(vidw, vidh, mask_shapes, color="black"):
    """create lavfi input expression to form a mask

    :param vidw: video frane width
    :type vidw: int
    :param vidh: video frame height
    :type vidh: int
    :param mask_shapes: mask shape specifications (keyword arguments for create_mask_alpha)
    :type mask_shapes: sequence of dicts
    :param color: _description_, defaults to 'black'
    :type color: str, optional
    """

    # 1. define filtergraph to form mask's alpha channel
    # 1a: generate individual alpha shapes
    alpha_chains = [create_mask_alpha(**args) for args in mask_shapes]

    nshapes = len(alpha_chains)
    if nshapes > 1:
        # 1b. if multiple shapes, mix'em together (if opque in one shape, stays opaque)
        infgs = "".join([f"{fc}[a{i}];" for i, fc in enumerate(alpha_chains)])
        inp = "".join([f"[a{i}];" for i in range(nshapes)])
        alpha_fg = f"{infgs}{inp}mix={nshapes}:1:1[ain];"
    else:
        # 1b. if one shape, ready to go
        alpha_fg = f"{alpha_chains[0]}[ain];"

    # 2. carve a solid color frame to form the final mask
    return f"color=c={color}:s={vidw}x{vidh}[cin];{alpha_fg},[cin]alphamerge,trim=end_frame=1"


def masks_to_crop(vidw, vidh, mask_shapes):
    """find extent of unmasked area

    :param vidw: video frane width
    :type vidw: int
    :param vidh: video frame height
    :type vidh: int
    :param mask_shapes: mask shape specifications (keyword arguments for create_mask_alpha)
    :type mask_shapes: sequence of dicts
    :return: extent of unmasked area: (x0,y0,x1,y1)
    :rtype: tuple of 4 ints
    """    

    x0 = 0
    y0 = 0
    x1 = vidw
    y1 = vidh
    for d in mask_shapes:
        x = d["x0"]
        y = d["y0"]
        w = d["w"]
        h = d["h"]
        if x > x0:
            x0 = x
        if y > y0:
            y0 = y
        if (xnew := x + w) < x1:
            x1 = xnew
        if (ynew := y + h) < y1:
            y1 = ynew

    return x0, y0, x1-x0, y1-y0


def adjust_masks(width, height, mask_shapes, sar=1, square=None, crop=None):
    """adjust mask specs from pre to post video frame manipulation

    :param width: original video frame width
    :type width: int
    :param height: original video frame height
    :type height: int
    :param mask_shapes: mask shape specifications (keyword arguments for create_mask_alpha)
    :type mask_shapes: sequence of dicts
    :param sar: sample aspect ratio, defaults to 1
    :type sar: int or Fraction, optional
    :param square: non-None to square non-square pixels, defaults to None
    :type square: None, "upscale" or "downscale", optional
    :param crop: tuple (x0, y0, w, h) to crop, defaults to None
    :type crop: sequence of 4 ints, optional
    :return: adjusted mask_shapes
    :rtype: list of dicts
    """
    mask_shapes = deepcopy(mask_shapes)

    if crop is not None:
        x0, y0, width, height = crop
        for d in mask_shapes:
            d["x0"] -= x0
            d["y0"] -= y0

    if sar != 1 and square:
        w, h = scale_frame(width, height, sar, square, crop)
        sx = sy = 1.0
        if h != height:
            sy = h / height
            for d in mask_shapes:
                d["y0"] *= sy
                d["h"] *= sy
        else:
            sx = w / width
            for d in mask_shapes:
                d["x0"] *= sx
                d["w"] *= sx

    return mask_shapes


def scale_frame(width, height, sar=1, square=None, crop=None):

    if crop is not None:
        # if crop is specified, ignore the default frame size
        x0, y0, width, height = crop

    if not isinstance(sar, Fraction):
        sar = Fraction(sar)
    sarw, sarh = sar.as_integer_ratio()

    if sar != 1 and square:
        upscaling = square == "upscale"

        # add scale filter + setsar filter
        # round to a closest even number
        if (sarw < sarh) == upscaling:
            height = 2 * round(height * sarh / sarw / 2)
        else:
            width = 2 * round(width * sarw / sarh / 2)
    return width, height


def form_vf(width, height, sar=1, src=None, mask=None, square=None, crop=None):
    # square: None, 'upscale','downscale'
    # sar
    # crop
    # mask

    filt_specs = []

    if crop is not None:
        x0, y0, x1, y1 = crop
        width = x1 - x0
        height = y1 - y0
        filt_specs.append(f"crop={width}:{height}:{x0}:{y0}")

    if not isinstance(sar, Fraction):
        sar = Fraction(sar)

    if sar != 1 and square:
        w, h = scale_frame(width, height, sar, None, square)
        filt_specs.append(f"scale=h={h}" if height != h else f"scale=w={w}")
        filt_specs.append(f"setsar=1:1")
    else:
        sarw, sarh = sar.as_integer_ratio()
        filt_specs.append(f"setsar={sarw}:{sarh}")

    fg = ",".join(filt_specs)

    # configure masking setup
    if mask:
        # add labels to the main filter chain
        fg = f"[{src}]{fg}[main];[main][{mask}]overlay"

    return fg


def transcode(src, dst, mask_config, src_type=None, enc_config=None, audio_config=None):
    """apply mask to src video and transcode

    :param src: input video
    :type src: str
    :param mask_config: _description_
    :type mask_config: _type_
    :param enc_config: _description_, defaults to None
    :type enc_config: _type_, optional
    :param src_type: _description_, defaults to None
    :type src_type: _type_, optional
    :raises ValueError: _description_
    :raises ValueError: _description_
    :raises RuntimeError: _description_
    :return: _description_
    :rtype: _type_
    """

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
