
# VisionGrabber

> Autonomous vision-guided pick-and-place system built on a Voron V0 — integrating custom STM32 firmware, dual-camera OpenCV detection, Hailo-8L ML inference, and hazard-aware path planning into a single self-contained demonstrator.

<img src="CAD_machine_screenshot.png" alt="CAD Machine Model" width="700"/>

![STM32 Build](https://img.shields.io/github/actions/workflow/status/eddnshoulders/VisionGrabber2/STM32-Build.yml?label=STM32%20build&logo=stmicroelectronics)
![STM32 Unit Tests](https://img.shields.io/github/actions/workflow/status/eddnshoulders/VisionGrabber2/stm32-unit-tests.yml?label=STM32%20unit%20tests&logo=github)
![Language: C++](https://img.shields.io/badge/firmware-C%2B%2B-blue)
![Platform: STM32](https://img.shields.io/badge/platform-STM32F103-lightgrey)
![Python](https://img.shields.io/badge/host-Python%203-yellow)
![Status: Active Development](https://img.shields.io/badge/status-active%20development-orange)

---

## Overview

VisionGrabber repurposes a Voron V0 CoreXY printer as a gantry robot for autonomous hazard-aware object retrieval. The system locates a target cylinder on a 120×120 mm bed, identifies any hazard markers placed alongside it, constructs keepout zones, plans a safe path, and executes a pick-and-place sequence — entirely without manual intervention after the initial button press.

The project was developed in five stages of increasing capability, each adding a new layer to the architecture. The final system combines custom embedded firmware with a dual-camera vision pipeline, on-device ML inference via a Hailo-8L accelerator, and A\*-based path planning — all running on a Raspberry Pi 4 mounted on the machine itself.

---

## Project Setup
Please see setup.txt in the repo root for setup instructions

---

## Final System Architecture
```

┌────────────────────────────────────────────────────────────────────┐
│                        Raspberry Pi 4                              │
│                                                                    │
│  ┌─────────────────┐   ┌──────────────────┐   ┌────────────────┐   │
│  │   UART Button   │   │      Flask app   │   │                │   │
│  │    with LED     │   │  + Hailo-8L      │   │   + OpenCV     │   │
│  └────────┬────────┘   │  ML inference    │   │ fine localise  │   │
│           │            └────────┬─────────┘   └───────┬────────┘   │
│           │  USB CDC            │ object locations    │ pixel XY   │
│  ┌────────▼─────────────────────▼─────────────────────▼─────────┐  │
│  │                      launcher.py                             │  │
│  │   hazard map → keepout zones → A* path plan → pick sequence  │  │
│  └────────────────────────────┬─────────────────────────────────┘  │
│                               │  serial G-code                     │
└───────────────────────────────┼────────────────────────────────────┘
                                │
                   ┌────────────▼─────────────┐
                   │   Custom STM32 Firmware  │
                   │   (SKR Mini E3 / voronMC)│
                   │                          │
                   │  CoreXY motion control   │
                   │  TMC2209 UART config     │
                   │  Sensorless homing X/Y   │
                   │  Mid-move stop support   │
                   │  Servo gripper control   │
                   └──────────────────────────┘
```
---

## Development Stages

The system was built incrementally. Each stage is a coherent, functional milestone on top of the last.

### Stage 1 — Bed-scanning pick-and-place (Python + Klipper)

The first working end-to-end loop. Manually-run Python scripts command Klipper over its JSON-RPC socket to scan the bed in a snake pattern, polling a Flask-served OpenCV circle detection endpoint after each move. On detection, the script applies a pixel-to-machine coordinate transform and issues G-code to move to the pick position and actuate the servo gripper.

- OpenCV HSV threshold + Hough circle transform for cylinder top detection
- Tunable parameters exposed via browser UI, persisted to JSON
- Pixel-to-machine coordinate transform calibrated at bed-down Z height

### Stage 2 — Hardware button trigger and systemd integration

The manual script invocation is replaced by a physical pushbutton. A SparkFun Pro Micro connected over USB CDC serial relays button events to the Pi. The host software is restructured into three modules and deployed as a pair of systemd services.

- `serial_manager.py` owns the serial port and pushes events to a `multiprocessing.Queue`
- `launcher.py` owns orchestration and is the systemd entry point
- `scan_and_grab.py` owns the machine sequence
- `udev` rule assigns a stable device name; systemd service ordering ensures correct startup sequence

### Stage 3 — Custom STM32 firmware replaces Klipper

Klipper is removed and replaced with custom C++ firmware running directly on the SKR Mini E3's STM32F103. This gives direct control over motion execution, enabling the firmware to stop mid-move in response to a detection signal — which Klipper's architecture does not support. The firmware reimplements the motion control functions previously provided by Klipper.

- CoreXY kinematics, motion planning, and acceleration profiles
- TMC2209 stepper driver configuration over UART
- Sensorless homing on X and Y axes using stallGuard
- Servo gripper control
- Mid-move stop: firmware halts and reports position on command, allowing the host to redirect to the detected target without completing the current move
- HAL abstraction layer (`ITimer`, `IGPIO`, `IUART`, etc.) isolates hardware dependencies for testability
- 100+ passing GoogleTest unit tests; CI runs on every push

### Stage 4 — Overhead static camera for scene-level detection

A second camera is mounted in a fixed overhead position, giving a full view of the bed without requiring the toolhead to move. This separates scene understanding (where is everything on the bed?) from pick precision (exactly where is the target?). The toolhead camera is retained for final position confirmation before pickup.

- Overhead camera runs a separate OpenCV instance for initial cylinder localisation
- Toolhead camera fine-tunes the pick coordinate at close range
- Two-stage detection: coarse from overhead, precise from toolhead

### Stage 5 — Hailo-8L ML inference and hazard-aware path planning

A Hailo-8L ML accelerator attached to the Pi enables on-device object detection at inference speeds not achievable with CPU-only OpenCV. Additional cylinders are placed on the bed carrying hazard signs on their tops. The ML model classifies each marker and assigns a hazard level. From the detected hazard locations, keepout zones are constructed and an A\* path planner finds a collision-free route to the target cylinder.

- Hailo-8L runs a trained object detection model on the overhead camera feed
- Hazard classification assigns severity levels to detected markers
- Keepout zones are expanded around each hazard proportional to severity
- A\* path planner operates on the resulting occupancy grid
- The planned path is executed as a sequence of moves to the custom firmware

---

## CI

| Workflow | Trigger | What it does |
|---|---|---|
| `stm32-unit-tests.yml` | Push to `Core/**` | Builds and runs GoogleTest suite on `ubuntu-latest` |
| `stm32-build.yml` | Push to `Core/**` | Cross-compiles Debug + Release with `gcc-arm-none-eabi` |

---

## Skills Demonstrated

Built as a portfolio piece targeting embedded systems and controls engineering roles.

| Area | Detail |
|---|---|
| Mechanical Design & Rapid Prototyping | Toolhead design in Fusion360 and printing on the Voron V0 |
| Embedded C++ | Custom STM32 firmware with HAL abstraction, TMC2209 UART, sensorless homing, mid-move interrupt |
| Unit testing | GoogleTest suite, HAL mock pattern, 100+ tests, CMake build |
| CI/CD | GitHub Actions: unit tests on Linux, firmware cross-compile for ARM |
| Host software architecture | Python multiprocessing, systemd/udev integration, REST API |
| Computer vision | OpenCV HSV detection, Hough transform, dual-camera pipeline, coordinate calibration |
| ML deployment | Hailo-8L accelerator, object detection model, on-device inference |
| Path planning | A\* on occupancy grid, hazard-aware keepout zone construction |
| Requirements management | sphinx-needs requirements desk with traceability |
| Systems integration | Full-stack integration from firmware through OS services to vision and planning |

---

