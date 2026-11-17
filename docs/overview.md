# NeuralControl Overview

NeuralControl is a Windows desktop application for recognizing hand gestures
from a camera feed and mapping recognized gestures to user-defined actions.
The interface is built with PySide6, hand landmarks are detected with
MediaPipe, and a scikit-learn model classifies the landmark features.

## Architecture

- **Core** (`core/`) defines shared data types, paths, feature utilities, and
  hand-tracking integration.
- **Services** (`services/`) implement camera capture, hand tracking, neural
  inference, training, rule validation, and action execution.
- **UI** (`ui/`) contains the main window, tabs, dialogs, and video/HUD widgets.
- **External runtime data** (`assets/` and `data/`) is stored beside the
  executable in a portable release. It is intentionally not embedded in the
  one-file executable.

## Runtime flow

1. The camera service supplies frames to the gesture engine.
2. MediaPipe returns 21 landmarks for each detected hand.
3. NeuralPose builds a 126-value feature vector and evaluates the trained
   classifier.
4. Stable predictions are matched against `data/rules.json`.
5. The action runner executes the configured action sequence.

The application targets Windows. A camera and a writable extracted release
folder are required for normal operation. Some system actions depend on
Windows features and may require additional permissions.

## Portable layout

```text
release/
|-- NeuralControl.exe
|-- README.txt
|-- assets/
|   `-- hand_landmarker.task
|-- data/
|   |-- gesture_registry.json
|   |-- rules.json
|   |-- settings.json
|   |-- models/
|   |   `-- gesture_model.joblib
|   `-- samples/
|       `-- gesture_samples.npz
`-- docs/
```

Keep the folders beside `NeuralControl.exe`. The application resolves its
portable root from the executable location when frozen.
