from dis import show_code
import ffmpegio

file = r"data\Pt9569_Visit1_fixed_nsq.mp4"

ffmpegio.ffmpegprocess.run(
    {
        "inputs": [(file, {"t": 5})],
        "outputs": [("-", {"vf": "freezedetect=d=0.05", "f": "null"})],
        "global_options": {"loglevel": "info"},
    },
    capture_log=None,
)
