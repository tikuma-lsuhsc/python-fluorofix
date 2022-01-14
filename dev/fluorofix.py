import sys
from os import environ, path
from configure import readOptionJSON
import regFFmpeg
import ffmpeg
import numpy as np
from scipy import signal

import matplotlib.pyplot as plt

if not getattr(sys, "frozen", False):
    print("non-exe run")
    sys.argv = [
        "trimvideo",
        # "C:\\Users\\tikum\\Documents\\Research\\Samlan 2019\\57_B2.mp4"
        "C:\\Users\\tikum\\Documents\\Research\\Samlan 2019\\23_B2.mp4",
    ]

print("Input arguments: ", sys.argv)

try:
    if path.basename(sys.executable).startswith("python"):
        optfile = path.splitext(__file__)[0] + ".json"
    else:
        optfile = path.splitext(sys.executable)[0] + ".json"

    opts = readOptionJSON(optfile)

    del sys.argv[0]
    nfiles = len(sys.argv)  # number of input files

    if nfiles == 0:
        print("No files to process. Exiting...")
        sys.exit(0)

    outFormat = opts["OutputFormat"].lower()
    outputOptions = opts["OutputOptions"]

    def analyzeVideo(infile):
        # lookup video size
        N = 128
        info = ffmpeg.probe(infile, select_streams="v")["streams"][0]

        ss = float(info["duration"]) / 2
        h = info["height"]
        w = info["width"]

        # run FFmpeg to resize video pixels and accumulate
        out, _ = (
            ffmpeg.input(infile, ss=ss)
            .output("pipe:", format="rawvideo", pix_fmt="gray", vframes=N)
            .run(capture_stdout=True, capture_stderr=True, quiet=True)
        )
        videoShape = (N, h, w)
        video = np.frombuffer(out, np.uint8).reshape(videoShape)

        def detectBound(video, axis):
            vminAll = np.reshape(
                np.moveaxis(video, axis, 0), (videoShape[axis], -1)
            ).min(1).flatten()
            
            i0 = np.argwhere(vminAll > 3).reshape(-1)[0]  # .flatten()
            i1 = vminAll.size - np.argwhere(vminAll[::-1] > 3).flatten()[0]
            vmin = vminAll[i0 + 1 : i1 - 1]
            return (i0, vmin)

        def detectGlottis(video):
            # exclude the out-of-viewport columns
            i0, vmin = detectBound(video, 2)

            # use detrended data for edge detection
            wmin = signal.detrend(vmin)

            # find the rising & falling edges
            def findEdges(wmin, thresh, Jmin):
                mindelta = 3  # allowed valley width
                Bthhi = wmin > thresh
                Bthlo = wmin <= thresh
                Jlohi = np.argwhere(np.logical_and(Bthhi[1:], Bthlo[:-1]))
                Jhilo = np.argwhere(np.logical_and(Bthhi[:-1], Bthlo[1:]))
                Jlohi.resize((Jlohi.size,))
                Jhilo.resize((Jhilo.size,))

                # find index pairs to form convex regions
                if Jlohi[0] < Jhilo[0]:
                    Jlohi = Jlohi[1:]
                Nc = min(Jlohi.size, Jhilo.size)

                Jhilo, Jlohi = Jhilo[:Nc], Jlohi[:Nc]
                pick = Jlohi - Jhilo > mindelta

                # if Jmin is in the too-narrow valley, recompute
                if (
                    Jmin < Jhilo[0]
                    or Jmin > Jlohi[-1]
                    or not pick[np.logical_and(Jhilo < Jmin, Jlohi > Jmin)]
                ):
                    Jmin = np.min(wmin[Jhilo[0] + 1 : Jlohi[-1]]) + Jhilo[0]

                return (Jlohi[pick], Jhilo[pick], Jmin)

            # find initial threshold level
            thresh = np.median(wmin)
            Jlohi, Jhilo, Jmin = findEdges(wmin, thresh, np.argmin(vmin))

            # if threshold too low to detect glottis, readjust as needed
            if Jlohi.size == 0:
                # arbitrary raise by 10% at a time
                while Jlohi.size == 0:
                    thresh *= 1.1
                    Jlohi, Jhilo, Jmin = findEdges(wmin, thresh, Jmin)
            elif Jmin < Jlohi[0] or Jmin > Jhilo[-1]:
                # Failed to capture the lowest point, lower threshold
                thresh = (
                    np.median(wmin[: Jlohi[0] + 1])
                    if Jmin < Jlohi[0]
                    else np.median(wmin[Jhilo[-1] :])
                )
                Jlohi, Jhilo, Jmin = findEdges(wmin, thresh, Jmin)

            # find the regions with the lowest 1st quartile value
            Vmins = np.asarray(
                [
                    np.quantile(vmin[Jhilo[k] : Jlohi[k]], 0.25)
                    for k in range(Jhilo.size)
                ]
            )
            k = np.argmin(Vmins)

            # detect the lowest point in
            imin = int(i0 + (Jhilo[k] + Jlohi[k]) / 2)

            return imin

        if w > h:
            try:
                x = detectGlottis(video)
                print("glottis at %d" % x)
            except Exception as err:
                print(
                    f"Could not find glottis. Keeping the middle of the frame: \n{err}"
                )
                x = int(w / 2)
            return {
                "w": "%f*in_h" % (opts["CropFrameAspectRatio"],),
                "x": "%d-out_w/2" % (x,),
            }

        else:
            (j0, vmin) = detectBound(video, 1)
            return {"h": "%d" % (vmin.size), "y": "%d" % (j0,)}

    def transcodeVideo(infile):

        (root, _) = path.splitext(infile)
        outfile = root + "_trimmed" + outFormat

        cropData = analyzeVideo(infile)
        print("crop arguments:", cropData)

        # set up the ffmpeg operation chain
        stream = ffmpeg.input(infile)
        stream = ffmpeg.filter(stream, "crop", **cropData)
        stream = ffmpeg.output(stream, outfile, **outputOptions)

        # run FFmpeg process
        ffmpeg.run(stream, overwrite_output=True)

    success = []
    failed = []
    for file in sys.argv:

        if not path.isfile(file):
            print("Invalid file: %s" % file)
            continue

        ext = path.splitext(file)[1].lower()
        if ext == ".json":
            opts = readOptionJSON(file, opts)
        else:
            try:
                transcodeVideo(file)
                success.append(file)
            except Exception as err:
                print(err)
                failed.append(file)

    if success:
        print("\nSuccessfully Trimmed:")
        print(*success, sep="\n")
    if failed:
        print("\nFailed to trim:")
        print(*failed, sep="\n")
except Exception as err:
    print(f"Unexpected Failure: \n{err}")
finally:
    input("\nPress Enter to Exit...")
