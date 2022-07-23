from copy import deepcopy
from fractions import Fraction
import logging
from ffmpegio import probe, ffmpegprocess, FFConcat
from tempfile import TemporaryDirectory
from os import path, makedirs


def create_mask_alpha(vidw, vidh, x0, y0, w, h, fill_in=False, is_rect=False):
    """create a filterchain to form the alpha channel of a rectangular or ellipstical mask

    :param vidw: video frame width
    :type vidw: int
    :param vidh: video frame height
    :type vidh: int
    :param x0: left edge of the mask
    :type x0: int
    :param y0: upper edge of the mask
    :type y0: int
    :param w: width of the mask
    :type w: int
    :param h: height of the mask
    :type h: int
    :param fill_in: True to mask inside, False to mask outside, defaults to False
    :type fill_in: bool, optional
    :param is_rect: True for rectangular mask, False for elliptical mask, defaults to False
    :type is_rect: bool, optional
    :return: ffmpeg filterchain expression
    :rtype: str
    """

    if is_rect:
        astr = f"gte(X,{x0})*lt(X,{x0+w})*gte(Y,{y0})*lt(Y,{y0+h})"
        if not fill_in:
            astr = f"not({astr})"
    else:
        ieq = "lte" if fill_in else "gt"
        rx = w / 2
        ry = h / 2
        xe = x0 + rx - 0.5
        ye = y0 + ry - 0.5
        rx2 = rx**2
        ry2 = ry**2
        astr = f"{ieq}((X-{xe})^2/{rx2}+(Y-{ye})^2/{ry2},1)"

    return f"nullsrc=s={vidw}x{vidh},format=y8,geq=lum='if({astr},255,0)'"


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

    nshapes = len(mask_shapes)

    if not nshapes:
        return ""

    # 1. define filtergraph to form mask's alpha channel
    # 1a: generate individual alpha shapes
    alpha_chains = [create_mask_alpha(vidw, vidh, **args) for args in mask_shapes]

    if nshapes > 1:
        # 1b. if multiple shapes, mix'em together (if opque in one shape, stays opaque)
        infgs = "".join([f"{fc}[a{i}];" for i, fc in enumerate(alpha_chains)])
        inp = "".join([f"[a{i}]" for i in range(nshapes)])
        alpha_fg = f"{infgs}{inp}mix={nshapes}:1:1"
    else:
        # 1b. if one shape, ready to go
        alpha_fg = f"{alpha_chains[0]}"

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

    if not len(mask_shapes):
        return None

    x0 = 0
    y0 = 0
    x1 = vidw
    y1 = vidh
    for d in mask_shapes:
        if d.get("fill_in", False):
            continue
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

    return x0, y0, x1 - x0, y1 - y0


def get_output_size(width, height, sar=1, square=None, crop=None):
    """get output video frame size

    :param width: input video width
    :type width: int
    :param height: input video height
    :type height: int
    :param sar: input sample aspect ratio, defaults to 1
    :type sar: int or Fraction, optional
    :param square: None to keep SAR, 'upscale' to square pixels by increasing size,
                   'downscale' to square pixels by decreasing size, defaults to None
    :type square: None, 'upscale' 'downscale', optional
    :param crop: (x0,y0,w,h) to crop or None to keep the full view, defaults to None
    :type crop: tuple of 4 ints, optional
    :return: _description_
    :rtype: _type_
    """
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
        w, h = get_output_size(width, height, sar, square, crop)
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


def form_vf(width, height, sar=None, src=None, mask=None, square=None, crop=None):
    # square: None, 'upscale','downscale'
    # sar
    # crop
    # mask

    filt_specs = []

    if crop is not None:
        x0, y0, width, height = crop
        filt_specs.append(f"crop={width}:{height}:{x0}:{y0}")

    if not isinstance(sar, Fraction):
        sar = Fraction(sar)

    if sar is None:
        if square:
            logging.warning("square option is set but SAR is undefined")
    elif sar != 1 and square:
        w, h = get_output_size(width, height, sar, square, None)
        filt_specs.append(f"scale=h={h}" if height != h else f"scale=w={w}")
        filt_specs.append(f"setsar=1:1")
    else:
        sarw, sarh = sar.as_integer_ratio()
        filt_specs.append(f"setsar={sarw}:{sarh}")

    fg = ",".join(filt_specs)

    # configure masking setup
    if mask:
        # add labels to the main filter chain
        fg = (
            f"[{src}]{fg}[main];[main][{mask}]overlay[vout]"
            if fg
            else f"[{src}][{mask}]overlay[vout]"
        )

    return fg


def concat_videos(urls, infos=None):

    ffconcat = FFConcat()
    ffconcat.add_files(urls)

    if infos is not None:

        t = 0.0
        for i, entry in enumerate(infos):
            t1 = t + entry.duration
            ffconcat.add_chapter(i, t, t1)
            t = t1

        # "-f", "concat",
        # '-safe','0',
        # '-map_metadata', '1'

    return ffconcat


def transcode(
    src,
    dst,
    tstart=None,
    tend=None,
    mask_shapes=None,
    src_info=None,
    sar=None,
    square=None,
    crop=None,
    color="black",
    enc_config=None,
    progress=None,
    overwrite=False,
):
    """apply mask to src video and transcode

    :param src: input video
    :type src: str
    :param mask_config: _description_
    :type mask_config: _type_
    :param enc_config: _description_, defaults to None
    :type enc_config: _type_, optional
    :param progress: progress monitor object, defaults to None
    :type progress: ProgressMonitorThread, optional
    :return: _description_
    :rtype: _type_
    """

    if src_info is None:
        try:
            src_info = probe.video_streams_basic(src)[0]
        except:
            raise ValueError("not a video file")

    width = src_info["width"]
    height = src_info["height"]
    if sar is None and square is not None:
        sar = Fraction(src_info.get("sar", 1.0))
    if crop is None:
        crop = masks_to_crop(width, height, mask_shapes)

    args = {
        "inputs": [(src, {})],
        "outputs": [(dst, {**enc_config})],
        "global_options": {},
    }

    if tstart is not None:
        args["inputs"][0][1]["ss"] = tstart
    if tend is not None:
        args["inputs"][0][1]["to"] = tend

    nmasks = 0 if mask_shapes is None else len(mask_shapes)
    if nmasks > 0:
        mask_shapes = adjust_masks(width, height, mask_shapes, sar, square, crop)
        mask_lavfi = create_mask(width, height, mask_shapes, color)
        args["inputs"].append((mask_lavfi, {"f": "lavfi"}))

    fg = form_vf(width, height, sar, "0:v", "1:v" if nmasks else False, square, crop)
    if fg:
        if nmasks:
            args["global_options"]["filer_complex"] = fg
            args["outputs"][0][1]["map"] = ["vout", "0:a?"]
        else:
            args["outputs"][0][1]["vf"] = fg

    # makedirs(path.split(dst)[0], exist_ok=True)
    if ffmpegprocess.run(
        args, capture_log=None, progress=progress, overwrite=overwrite
    ).returncode:
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
