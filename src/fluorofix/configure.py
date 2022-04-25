import json
import cerberus


def writeOptionJSON(filename, ctx):
    with open(filename, "w") as outfile:
        json.dump(ctx, outfile, indent=2)


def readOptionJSON(filename):
    try:
        with open(filename, "r") as json_file:
            userctx = json.load(json_file)
        # validate
        validateOptions(userctx)
    except:
        return None
    return userctx


def mergeOptionJSON(userctx, basectx={}):
    if not basectx:
        basectx = defaultOption()
    return {**basectx, **userctx}


def saveOptionJSON(filename, ctx):
    # save if user set is missing any option
    writeOptionJSON(filename, ctx)


def defaultOption():

    return {
        "Profiles": {
            "Toshiba Kalare (1080p)": (
                {"height": 1080},
                {"sar": [9, 10], "circ": [396, 92, 1140]},
            ),
            "Siemens Axiom (480p)": ({"height": 480}, {"circ": [45, 8, 530]}),
        },
        "SquarePixel": 1,
        "OutputFolder": None,
        "OutputSuffix": "_fixed",
        "OutputExt": ".mp4",
        "OutputOptions": {"preset": "slow", "crf": 22, "pix_fmt": "yuv420p"},
        "Overwrite": False,
    }


def validateOptions(ctx):
    pos_int = {"type": "integer", "min": 0}
    v = cerberus.Validator(
        {
            "Profiles": {
                "type": "dict",
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
                            },
                        },
                    ],
                },
                "empty": False,
            },
            "SquarePixel": {"type": "integer"},
            "OutputFolder": {"type": "string", "nullable": True, "empty": True},
            "OutputSuffix": {"type": "string", "empty": True},
            "OutputExt": {"type": "string", "empty": False},
            "OutputOptions": {"type": "dict"},
            "Overwrite": {"type": "boolean", "empty": False},
        }
    )
    if not v.validate(ctx):
        raise ValueError(v.errors)
