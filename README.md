# NeuralControl

NeuralControl is a Windows desktop application that recognizes hand gestures
from a webcam and maps them to user-configured actions. It uses MediaPipe for
hand-landmark tracking, a scikit-learn neural model for gesture classification,
and PySide6 for the HUD-style interface.

## Features

- Real-time recognition of single-hand and two-hand gestures.
- Gesture sample recording and model training in the Training tab.
- Rules for individual gestures, simultaneous combinations, and action sequences.
- Gesture-controlled cursor mode and interactive drawing.
- Dataset statistics and model evaluation metrics.

## Requirements

- Windows 10/11.
- Python 3.10 or newer.
- A webcam.
- The MediaPipe hand-landmarker model at `assets/hand_landmarker.task`.

## Run from source

Create and activate a virtual environment from the project root, install the
dependencies, and start the application:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Ensure that `assets/hand_landmarker.task` is present before launching. The
camera starts automatically in the Control tab. To recognize a new gesture,
record examples and train the model in the Training tab.

## Build the portable release

After installing the dependencies, run this command from the project root:

```powershell
.\build_release.bat
```

The script builds the application with PyInstaller, stages the EXE, assets,
and data in `release/`, and creates `NeuralControl_Release.zip`. Extract the
entire archive into one folder; keep `assets/` and `data/` beside the EXE.

## Documentation

- [Architecture overview](docs/overview.md)
- [Gesture catalog](docs/gestures.md)
- [Model training](docs/training.md)
- [Rules and actions](docs/rules.md)

## Project structure

```text
core/       Shared types, hand tracking, features, and filters
services/   Camera, recognition, training, rules, and action execution
ui/         PySide6 windows, tabs, dialogs, and HUD widgets
assets/     MediaPipe hand-landmarker model
data/       Gesture registry, rules, model, and training samples
docs/       Project, gesture, training, and rules documentation
scripts/    Release staging and packaging helpers
```
