from copy import deepcopy
import itertools
import json
import cerberus


def writeOptionJSON(filename, ctx):
    with open(filename, "w") as outfile:
        json.dump(ctx, outfile, indent=2)


def readOptionJSON(filename, basectx=None):
    with open(filename, "r") as json_file:
        userctx = json.load(json_file)

    # merge if base context is given
    if basectx is not None:
        userctx = mergeOptionJSON(userctx, basectx)

    # validate
    validateOptions(userctx)

    return userctx


def mergeOptionJSON(userctx, basectx={}):
    if not basectx:
        basectx = defaultOption()
    ctx = deepcopy(basectx)
    for k, v in userctx.items():
        if k == "Profiles":
            ctx[k] |= v
        else:
            ctx[k] = v
    return ctx


def saveOptionJSON(filename, ctx):
    # save if user set is missing any option
    writeOptionJSON(filename, ctx)


def defaultOption():

    return {
        "Profiles": {
            "Toshiba Kalare (1080p)": [
                {"height": 1080},
                {"sar": [8, 9], "circ": [396, 92, 1144]},
            ],
            "Siemens Axiom (480p)": [{"height": 480}, {"circ": [45, 8, 530]}],
        },
        "SquarePixel": True,
        "Scaling": "up",
        "CropVideo": True,
        "ApplyMask": True,
        "KeepAudio": True,
        "OutputFolder": None,
        "OutputSuffix": "_fixed",
        "OutputExt": ".mp4",
        "OutputOptions": {"preset": "slow", "crf": 18, "pix_fmt": "yuv420p"},
        "Overwrite": False,
    }


def validateOptions(ctx):
    pos_int = {"type": "integer", "min": 0}
    pos_real = {"type": "float", "min": 0}
    v = cerberus.Validator(
        {
            "Profiles": {
                "type": "dict",
                "keysrules": {"type": "string"},
                "valuesrules": {
                    "type": "list",
                    "items": [
                        {"type": "dict", "keysrules": {"type": "string"}},
                        {
                            "type": "dict",
                            "schema": {
                                "sar": {
                                    "type": "list",
                                    "items": [pos_int, pos_int],
                                },
                                "circ": {
                                    "type": "list",
                                    "items": [pos_int, pos_int, pos_int],
                                },
                                "inkscape-page": {
                                    "type": "list",
                                    "items": [pos_real, pos_real],
                                },
                                "inkscape-circ": {
                                    "type": "list",
                                    "items": [
                                        {"type": "float"},
                                        {"type": "float"},
                                        pos_real,
                                        pos_real,
                                    ],
                                },
                            },
                        },
                    ],
                },
                "empty": False,
            },
            "SquarePixel": {"type": "boolean"},
            "Scaling": {"type": "string", "allowed": ["up", "down"]},
            "CropVideo": {"type": "boolean"},
            "ApplyMask": {"type": "boolean"},
            "KeepAudio": {"type": "boolean"},
            "OutputFolder": {"type": "string", "nullable": True, "empty": True},
            "OutputSuffix": {"type": "string", "empty": True},
            "OutputExt": {"type": "string", "empty": False},
            "OutputOptions": {"type": "dict"},
            "Overwrite": {"type": "boolean", "empty": False},
        }
    )
    if not v.validate(ctx):
        raise ValueError(v.errors)


def convert_inkscape(format, height):
    try:
        circ = format["inkscape-circ"]
    except:
        # no inkscape def or incomplete spec
        return format

    sar = circ[3] / circ[2]  # w/h
    if sar != 1:
        pred = (
            (lambda i: (i + 1) * sar > i) if sar < 1 else (lambda i: (i + 1) > i * sar)
        )

        *_, i = itertools.takewhile(pred, itertools.count(1))
        sar = (
            (
                [i, i + 1]
                if (sar - (i / (i + 1))) < (((i + 1) / (i + 2)) - sar)
                else [i + 1, i + 2]
            )
            if sar < 1
            else (
                [i + 1, i]
                if (((i + 1) / i) - sar) < (sar - ((i + 2) / (i + 1)))
                else [i + 2, i + 1]
            )
        )
        format["sar"] = sar
        sar = sar[0] / sar[1]

    try:
        page = format["inkscape-page"]
        assert height > 0
    except:
        # no page def or height given to compute the de-id circle
        return format

    width = round(height * page[0] / page[1])

    x0 = circ[0] / page[0] * width
    y0 = circ[1] / page[1] * height

    if sar < 1:  # stretch in y
        y0 /= sar
        dia = circ[2] / page[0] * width
    else:
        x0 *= sar
        dia = circ[3] / page[1] * height

    format["circ"] = [round(x0), round(y0), round(dia / 2) * 2]
    return format
