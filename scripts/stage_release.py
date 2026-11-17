from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release"
EXECUTABLE = ROOT / "dist" / "NeuralControl.exe"

REQUIRED_FILES = (
    ROOT / "assets" / "hand_landmarker.task",
    ROOT / "data" / "gesture_registry.json",
    ROOT / "data" / "rules.json",
    ROOT / "data" / "settings.json",
    ROOT / "data" / "models" / "gesture_model.joblib",
    ROOT / "data" / "samples" / "gesture_samples.npz",
)

TEACHER_README = """\
NeuralControl — портативна версія

1. Розпакуйте весь архів у папку, до якої є право запису.
2. Запустіть NeuralControl.exe.
3. Перейдіть на вкладку «УПРАВЛІННЯ» та дозвольте програмі доступ до камери.
   Камера запускається автоматично; перевірте, що відео з'явилося.
4. Переконайтеся, що режим «НЕЙРОМЕРЕЖА» увімкнений, і покажіть руці камері.
   У поточній моделі є приклади жестів ЛІВА_ЛОДОНЬ, ЛІВИЙ_КУЛАК і
   ПРАВА_ЛОДОНЬ. Інші жести (наприклад, ВУЛКАН) потрібно спершу записати
   у вкладці «НАВЧАННЯ» та перенавчити модель.
5. Перейдіть у «НАЛАШТУВАННЯ», створіть правило для розпізнаного жесту
   та призначте йому дію.
6. Якщо потрібного жесту немає або він розпізнається неправильно, відкрийте
   «НАВЧАННЯ», запишіть кілька прикладів для кожного класу та натисніть
   «НАВЧИТИ НЕЙРОМЕРЕЖУ».

Поради:
- Для стабільної роботи добре освітліть руку та тримайте її в межах кадру.
- Не переміщуйте окремі файли або папки з архіву: EXE шукає assets/ та data/
  поруч із собою.
- Портативну папку слід зберігати у доступному для запису місці, оскільки
  налаштування, правила та навчальні приклади записуються у data/.
"""


def _validate_sources():
    if not EXECUTABLE.is_file():
        raise FileNotFoundError(
            f"PyInstaller executable not found: {EXECUTABLE}. "
            "Build neuralcontrol.spec first."
        )
    missing = [path for path in REQUIRED_FILES if not path.is_file()]
    if missing:
        paths = "\n".join(f"  - {path}" for path in missing)
        raise FileNotFoundError(f"Required release files are missing:\n{paths}")
    if not (ROOT / "docs").is_dir():
        raise FileNotFoundError(f"Documentation folder not found: {ROOT / 'docs'}")


def _clear_release_folder():
    expected_release = (ROOT / "release").resolve()
    if RELEASE.resolve() != expected_release or RELEASE.parent.resolve() != ROOT.resolve():
        raise RuntimeError(f"Refusing to clear unexpected release path: {RELEASE}")
    if RELEASE.exists():
        shutil.rmtree(RELEASE)
    RELEASE.mkdir(parents=True)


def main():
    _validate_sources()
    _clear_release_folder()

    shutil.copy2(EXECUTABLE, RELEASE / "NeuralControl.exe")

    shutil.copytree(ROOT / "assets", RELEASE / "assets")
    staged_model = RELEASE / "assets" / "hand_landmarker.task"
    if not staged_model.is_file() or staged_model.stat().st_size == 0:
        raise OSError(f"MediaPipe model was not staged: {staged_model}")

    data = RELEASE / "data"
    data.mkdir()
    for filename in ("gesture_registry.json", "rules.json", "settings.json"):
        shutil.copy2(ROOT / "data" / filename, data / filename)
    shutil.copytree(ROOT / "data" / "models", data / "models")
    shutil.copytree(ROOT / "data" / "samples", data / "samples")

    shutil.copytree(ROOT / "docs", RELEASE / "docs")
    (RELEASE / "README.txt").write_text(TEACHER_README, encoding="utf-8")
    print(f"Release staged at: {RELEASE}")


if __name__ == "__main__":
    main()
