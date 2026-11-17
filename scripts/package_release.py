from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release"
ARCHIVE = ROOT / "NeuralControl_Release.zip"
TEMP_ARCHIVE = ROOT / "NeuralControl_Release.zip.tmp"

REQUIRED_ENTRIES = {
    "NeuralControl.exe",
    "README.txt",
    "assets/hand_landmarker.task",
    "data/gesture_registry.json",
    "data/rules.json",
    "data/settings.json",
    "data/models/gesture_model.joblib",
    "data/samples/gesture_samples.npz",
}


def main():
    if not (RELEASE / "NeuralControl.exe").is_file():
        raise FileNotFoundError(f"Release executable is missing in {RELEASE}")

    TEMP_ARCHIVE.unlink(missing_ok=True)
    with ZipFile(TEMP_ARCHIVE, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(RELEASE.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(RELEASE).as_posix())

    with ZipFile(TEMP_ARCHIVE) as archive:
        entries = set(archive.namelist())
        missing = REQUIRED_ENTRIES - entries
        if missing:
            TEMP_ARCHIVE.unlink(missing_ok=True)
            raise FileNotFoundError(
                "Release ZIP is missing required entries: "
                + ", ".join(sorted(missing))
            )
        broken_entry = archive.testzip()
        if broken_entry is not None:
            TEMP_ARCHIVE.unlink(missing_ok=True)
            raise OSError(f"Release ZIP failed CRC validation: {broken_entry}")

    TEMP_ARCHIVE.replace(ARCHIVE)
    print(f"Release archive created and verified: {ARCHIVE}")


if __name__ == "__main__":
    main()
