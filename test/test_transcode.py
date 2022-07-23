from fluorofix import transcode
import pytest
import ffmpegio
import numpy as np


@pytest.mark.parametrize("fill_in", [False, True])
@pytest.mark.parametrize("is_rect", [False, True])
def test_create_mask_alpha(fill_in, is_rect):
    vidw = 16
    vidh = 8
    x0 = 5
    y0 = 1
    w = h = 6

    lavfi = transcode.create_mask_alpha(vidw, vidh, x0, y0, w, h, fill_in, is_rect)
    ffmpegio.image.read(lavfi, f_in="lavfi", pix_fmt="y8")


@pytest.fixture()
def mask_shapes():
    return [
        dict(x0=1, y0=1, w=6, h=6),
        dict(x0=2.5, y0=2.5, w=3, h=3, fill_in=True),
    ]


def test_create_mask_n_crop(mask_shapes):
    vidw = 16
    vidh = 8

    for i in range(1, 3):
        lavfi = transcode.create_mask(vidw, vidh, mask_shapes[:i], color="orange")
        print(lavfi)
        I = ffmpegio.image.read(lavfi, f_in="lavfi", pix_fmt="rgba")
        Ix = np.where(np.logical_not(np.all(I[:, :, -1], axis=0)))[0]
        Iy = np.where(np.logical_not(np.all(I[:, :, -1], axis=1)))[0]
        crop0 = (Ix[0], Iy[0], Ix[-1] + 1 - Ix[0], Iy[-1] + 1 - Iy[0])
        crop = transcode.masks_to_crop(vidw, vidh, mask_shapes[:i])
        assert np.array_equal(crop, crop0)


@pytest.mark.parametrize(
    "sar, square, crop, outsize",
    [
        (1, None, None, (100, 100)),
        (1, None, (0, 0, 50, 50), (50, 50)),
        (0.5, None, None, (100, 100)),
        (0.5, "upscale", None, (100, 200)),
        (0.5, "downscale", None, (50, 100)),
        (2, "upscale", None, (200, 100)),
        (2, "downscale", None, (100, 50)),
    ],
)
def test_get_output_size(sar, square, crop, outsize):
    win = 100
    hin = 100
    assert transcode.get_output_size(win, hin, sar, square, crop) == outsize


@pytest.mark.parametrize(
    "sar, square, crop",
    [
        (1, None, None),
        (1, None, (0, 0, 50, 50)),
        (0.5, None, None),
        (0.5, "upscale", None),
        (0.5, "downscale", None),
        (2, "upscale", None),
        (2, "downscale", None),
    ],
)
def test_adjust_masks(sar, square, crop):
    win = 100
    hin = 100
    mask_shapes = [
        dict(x0=1, y0=1, w=6, h=6),
        dict(x0=2.5, y0=2.5, w=3, h=3, fill_in=True),
    ]
    transcode.adjust_masks(win, hin, mask_shapes, sar, square, crop)


if __name__ == "__main__":

    from matplotlib import pyplot as plt

    width = 100
    height = 100
    mask_shapes = [
        dict(x0=1, y0=1, w=6, h=6),
        dict(x0=2.5, y0=2.5, w=3, h=3, fill_in=True),
    ]
    sar = 0.75
    square = "upscale"
    crop = (10, 10, 80, 80)
    src = "0:v"
    mask = "1:v"
    print(transcode.form_vf(width, height, sar, src, mask, square, crop))
