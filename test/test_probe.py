from fluorofix import probe, configure
from os import path


def test_is_video():

    profiles = configure.defaultOption()["Profiles"]

    entries = (
        ("colorchart.mp4", False, None),
        ("colorchart_720x480.mp4", True, "Siemens Axiom (480p)"),
        ("colorchart_1280x720.mp4", True, None),
        ("colorchart_1920x1080.mp4", True, "Toshiba Kalare (1080p)"),
    )

    for file, valid, actual_prof in entries:

        filepath = path.join(path.dirname(__file__), "assets", file)
        tf, prof = probe.is_video(filepath)
        assert tf == valid and prof is None

        tf, prof = probe.is_video(filepath, profiles)
        print(file, tf, prof, actual_prof)
        assert tf == valid and prof == actual_prof

if __name__ == "__main__":
    test_is_video()
