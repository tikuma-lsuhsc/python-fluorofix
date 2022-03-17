import json
import cerberus


def writeOptionJSON(filename, opts):
    with open(filename, "w") as outfile:
        json.dump(opts, outfile, indent=2)


def readOptionJSON(filename, baseopts={}, update_file=True):
    try:
        with open(filename, "r") as json_file:
            useropts = json.load(json_file)
    except:
        opts = defaultOption()
        if update_file:
            writeOptionJSON(filename, opts)
        return opts

    # validate
    validateOptions(useropts)

    if not baseopts:
        baseopts = defaultOption()
    opts = {**baseopts, **useropts}

    # save if user set is missing any option
    if set(opts.keys()) - set(useropts.keys()) and update_file:
        writeOptionJSON(filename, opts)
    return opts


def defaultOption():

    return {
        "Profiles": {
            "height=1080": {"sar": [9, 10], "circ": [396, 92, 1140]},
            "height=480": {"circ": [45, 8, 530]},
        },
        "SquarePixel": 1,
        "OutputFolder": None,
        "OutputSuffix": "_fixed",
        "OutputExt": ".mp4",
        "OutputOptions": {"preset": "slow", "crf": 8, "pix_fmt": "yuv420p"},
        "Overwrite": False,
    }


def validateOptions(opts):
    pos_int = {"type": "integer", "min": 0}
    v = cerberus.Validator(
        {
            "Profiles": {
                "type": "dict",
                "valuesrules": {
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
                    "empty": False,
                },
            },
            "SquarePixel": {"type": "integer"},
            "OutputFolder": {"type": "string", "nullable": True, "empty": True},
            "OutputSuffix": {"type": "string", "empty": True},
            "OutputExt": {"type": "string", "empty": False},
            "OutputOptions": {"type": "dict"},
            "Overwrite": {"type": "boolean", "empty": False},
        }
    )
    if not v.validate(opts):
        raise ValueError(v.errors)
