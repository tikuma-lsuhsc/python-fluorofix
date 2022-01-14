import json
import cerberus


def writeOptionJSON(filename, opts):
    with open(filename, "w") as outfile:
        json.dump(opts, outfile, indent=2)


def readOptionJSON(filename, baseopts={}):
    try:
        with open(filename, "r") as json_file:
            useropts = json.load(json_file)
    except:
        opts = defaultOption(True)
        writeOptionJSON(filename, opts)
        return opts

    # validate
    validateOptions(useropts)

    if not baseopts:
        baseopts = defaultOption(False)
    opts = {**baseopts, **useropts}

    if not "OutputOptions" in opts or not opts["OutputOptions"]:
        if opts["OutputFormat"] == ".mp4":
            opts["OutputOptions"] = defaultMP4Options()
        elif opts["OutputFormat"] == ".avi":
            opts["OutputOptions"] = defaultAVIOptions()
        else:
            raise Exception(
                "Unknown OutputFormat specified. It must be either '.mp4' or '.avi'"
            )
        writeOptionJSON(filename, opts)
    return opts


def defaultOption(include_output_opts=False):

    opts = {
        "CropFrameAspectRatio": 1,
        "OutputFormat": ".mp4",
        "OutputOptions": defaultMP4Options() if include_output_opts else {},
    }

    return opts


def defaultMP4Options():
    return {"c:v": "libx264", "preset": "slow", "crf": 22, "pix_fmt": "yuv420p"}


def defaultAVIOptions():
    return {"c:v": "huffyuv", "pix_fmt": "rgb24"}


def validateOptions(opts):
    v = cerberus.Validator(
        {
            "CropFrameAspectRatio": {"type": "float", "min": 0, "empty": False},
            "OutputFormat": {"type": "string", "empty": False, "regex": r"^\.\S+$"},
            "OutputOptions": {"type": "dict", "empty": True},
        }
    )
    if not v.validate(opts):
        raise ValueError(v.errors)
