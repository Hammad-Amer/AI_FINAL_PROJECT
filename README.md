# TORCS Neural-Network Racing Driver

> A self-driving controller for the TORCS racing simulator that learns to drive by cloning human behavior with a deep neural network — with a live keyboard toggle between AI and manual control.

## Overview

This project implements an autonomous driving agent for **TORCS** (The Open Racing Car Simulator) using its **SCRC** (Simulated Car Racing Championship) interface. A Python client connects to the TORCS server over UDP, reads the car's sensor stream, and sends back control commands every simulation step.

The controller runs in two modes:

- **AI mode** — a trained neural network predicts acceleration, braking, clutch, and steering directly from the game's sensor state (behavioral cloning).
- **Manual mode** — drive the car yourself with `W`/`A`/`S`/`D`, which also records telemetry for training new models.

Press **`m`** at any time to switch between the two.

The model is trained offline via **behavioral cloning**: telemetry is recorded from human laps, combined and normalized, used to train a deep neural network in Keras, then exported to **TensorFlow Lite** for low-latency inference that fits inside TORCS' ~50 ms decision cycle.

## Tech Stack

- **Language:** Python 3
- **ML / inference:** TensorFlow / Keras (training), TensorFlow Lite (real-time inference)
- **Data:** pandas, NumPy, scikit-learn (`StandardScaler`, preprocessing pipelines), joblib
- **I/O & control:** UDP sockets, `keyboard` (live key input)
- **Simulator:** TORCS with the SCRC / `snakeoil` server interface (external — see Prerequisites)

## Key Features

- **Behavioral-cloning driver** — a 5-layer DNN (512-128-64-32, ReLU + dropout) maps 73 game-state features to 4 continuous control outputs.
- **Live AI ↔ manual toggle** — hot-swap control mid-race with the `m` key; manual mode doubles as a data recorder.
- **Rule-based gear management** — RPM-based shifting with hysteresis and shift cooldown layered on top of the model's outputs, plus automatic reverse recovery when the car gets stuck.
- **Real-time inference** — the Keras model is quantized to TFLite so forward passes stay within the simulator's timing budget.
- **Full training pipeline** — reproducible scripts to combine, clean, normalize, and train from raw telemetry.

## Project Structure

```
pyScrcClient-master/
├── src/
│   ├── pyclient.py          # Entry point — connects to the TORCS server over UDP
│   ├── driver.py            # Driver: AI-mode (TFLite) + manual-mode control & telemetry logging
│   ├── carState.py          # Parses the incoming sensor message into car state
│   ├── carControl.py        # Builds the outgoing control message
│   ├── msgParser.py         # SCRC UDP message (de)serialization
│   ├── combinedataset.py    # Merges per-track telemetry CSVs into one dataset
│   ├── normalizedata.py     # Cleans & scales the combined dataset for training
│   ├── model_train.ipynb    # Trains the DNN and exports Keras / TFLite models
│   ├── trainingdata/        # Raw recorded telemetry (git-ignored, kept locally)
│   └── newtrainingdata/     # Additional recorded telemetry (git-ignored, kept locally)
├── models/                  # Trained model + scaler artifacts used at inference
└── Report/REPORT.pdf        # Project report
```

## How It Works

```
        TORCS server  ──UDP──▶  pyclient.py  ──▶  Driver.drive()
              ▲                                        │
              │                              ┌─────────┴─────────┐
              │                          AI mode             Manual mode
              │                     (TFLite model)        (W/A/S/D keys)
              │                              │                   │
              └──────────UDP control◀────────┴───────────────────┘
```

Each step, `Driver.drive()` parses the sensor message into a `CarState`, produces controls (model prediction or keyboard input), applies rule-based gear logic, logs telemetry, and returns a control message to the server.

## Prerequisites

- **TORCS** installed with the **SCRC / `snakeoil` server** patch that exposes the UDP sensor interface (this is external to the repo and must be installed separately).
- **Python 3.9+** with the dependencies below.

```bash
pip install tensorflow scikit-learn pandas numpy joblib keyboard
```

> The `keyboard` library may require elevated privileges (e.g. `sudo` on Linux) to capture key events.

## Running the AI Driver

1. Launch TORCS, start a race that uses an **`scr_server`** bot, and wait for it to listen (default UDP port `3001`).
2. From the `src/` directory (the model paths are relative to it), start the client:

```bash
cd pyScrcClient-master/src
python pyclient.py --host localhost --port 3001
```

Useful flags: `--port` (server port), `--id` (bot ID, default `SCR`), `--maxEpisodes`, `--maxSteps`, `--stage` (0 Warm-Up, 1 Qualifying, 2 Race, 3 Unknown).

The car starts in **AI mode**. Press **`m`** to switch to manual (`W` accelerate, `S` brake/reverse, `A`/`D` steer); press `m` again to return to AI.

## Retraining the Model

1. **Record telemetry** — drive manually (`m` to manual mode); each session is logged to a timestamped CSV.
2. **Combine** the per-track CSVs:
   ```bash
   python combinedataset.py      # -> combined_data.csv
   ```
3. **Normalize / clean** the dataset:
   ```bash
   python normalizedata.py       # -> normalized_telemetry_data.csv + scaler
   ```
4. **Train** by running `model_train.ipynb`, which trains the DNN and exports the Keras and TFLite models plus the `means`/`stds` scaling parameters into `models/`.

## Results

- **Architecture:** 73 input features → 512 → 128 → 64 → (dropout 0.2) → 32 → 4 outputs (acceleration, braking, clutch, steering).
- **Training:** ~141k samples, Adam (lr = 0.007), 200 epochs, mean-squared-error loss.
- **Validation MAE: 0.0316.**
- Behavioral cloning was chosen over reinforcement learning for sample efficiency and to avoid unsafe exploration, and over classic control for its ability to model the non-linear sensor-to-control mapping while meeting real-time latency requirements.

See [`Report/REPORT.pdf`](pyScrcClient-master/Report/REPORT.pdf) for the full write-up.

## Author

**Hammad Amer**

Developed as an Artificial Intelligence course project.
