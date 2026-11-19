<div align="center">

# NeuralControl

### Real-time hand gesture recognition and customizable desktop control

Turn webcam hand gestures into desktop actions with a trainable recognition
model, a configurable rule engine, and a PySide6 HUD interface.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![UI](https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![Vision](https://img.shields.io/badge/Vision-MediaPipe-4285F4?logo=google&logoColor=white)](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker)
[![Computer Vision](https://img.shields.io/badge/CV-OpenCV-5C3EE8?logo=opencv&logoColor=white)](https://opencv.org/)
[![ML](https://img.shields.io/badge/ML-scikit--learn-F7931E?logo=scikitlearn&logoColor=white)](https://scikit-learn.org/)

</div>

---

## ✨ Overview

**NeuralControl** is a Windows desktop application that recognizes hand
gestures from a webcam and maps them to user-defined actions. MediaPipe tracks
21 landmarks per hand; a trainable scikit-learn MLP classifies the resulting
features, and a rule engine connects recognized gestures to actions.

The project combines real-time computer vision with a desktop interface for
training custom gestures, creating action rules, controlling the pointer, and
drawing with hand movement.

## 🚀 Features

- **Live hand tracking** — detect and track up to two hands through a webcam.
- **Custom gesture training** — record examples and train a model in the app.
- **Rule builder** — bind gestures or two-hand combinations to actions and
  ordered action sequences with configurable hold times.
- **Desktop control** — trigger supported keyboard, mouse, media, window,
  screenshot, and system actions.
- **Mouse mode** — move the pointer with the index fingertip.
- **Drawing canvas** — draw with a hand or mouse, with camera and hologram views.
- **HUD interface** — monitor camera tracking, recognition, FPS, and events.
- **Portable Windows build** — package the app and its runtime data with
  PyInstaller.

## 🧰 Technology

| Area | Technologies |
| --- | --- |
| Language | Python |
| Desktop UI | PySide6 |
| Hand tracking | MediaPipe Tasks |
| Image processing | OpenCV, NumPy |
| Model training and inference | scikit-learn, Joblib |
| Data visualization | Matplotlib |
| Desktop input automation | PyAutoGUI |
| Packaging | PyInstaller |

## ⚙️ Getting Started

### Requirements

- Windows 10/11
- Python 3.10 or newer
- A webcam
- MediaPipe hand-landmarker model at `assets/hand_landmarker.task`

### Run from source

```powershell
git clone https://github.com/Solipsist-crypto/NeuralControl.git
cd NeuralControl

python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

The camera starts automatically in the **Control** tab. To recognize a custom
gesture, record examples and train the model in **Training**. The trained
model and examples are stored under `data/`.

## 📦 Build a Portable Release

With the project dependencies installed, run the build script from the
repository root:

```powershell
.\build_release.bat
```

The script builds the Windows executable with PyInstaller, stages the runtime
files in `release/`, and creates `NeuralControl_Release.zip`. Extract the
entire archive into one writable folder; keep `assets/` and `data/` beside
`NeuralControl.exe`.

## 🧠 How It Works

```text
Webcam
  └─> Camera service
       └─> MediaPipe hand landmarks
            └─> 126-value feature vector
                 └─> Trained gesture model
                      └─> Gesture rules and hold timers
                           └─> Action sequences
```

The model input contains 126 values: 21 three-dimensional landmarks for each
of the left and right hand slots. Missing hands are zero-filled. Gesture
examples are stored in `data/samples/gesture_samples.npz`, the trained model
in `data/models/gesture_model.joblib`, and configurable actions in
`data/rules.json`.

## 🗂️ Project Structure

```text
core/       Shared types, hand tracking, features, and filters
services/   Camera, recognition, training, rules, and action execution
ui/         PySide6 windows, tabs, dialogs, and HUD widgets
assets/     MediaPipe hand-landmarker model
data/       Gesture registry, rules, model, and training samples
docs/       Architecture, gestures, training, and rules documentation
scripts/    Release staging and packaging helpers
```

## 📚 Documentation

- [Architecture overview](docs/overview.md)
- [Gesture catalog](docs/gestures.md)
- [Training the model](docs/training.md)
- [Action rules](docs/rules.md)

## 🔐 Notes

NeuralControl can send input and system commands to your desktop. Review
configured actions before using them; actions marked as sensitive require
confirmation. Some actions depend on Windows features or additional
permissions.

---

<div align="center">

Built with Python, computer vision, and a little bit of gesture magic. ✋

</div>
