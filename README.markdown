# Trichotillomania Reminder

<video width="640" height="360" controls>
  <source src="assets/demo.gif" type="video/mp4">
  Your browser does not support the gif tag. View a screenshot below.
</video>

![Trichotillomania Reminder UI](UI.png) <!-- Fallback screenshot -->

**Trichotillomania Reminder** is a computer vision-based application designed to assist individuals with trichotillomania (compulsive hair-pulling) by detecting hair-pulling gestures and providing audio feedback to interrupt the behavior. The program leverages real-time webcam input, MediaPipe for hand and face tracking, and a Tkinter-based user interface with a scalable video feed, customizable settings, and detailed statistics tracking. It includes a calendar for monitoring daily triggers and supports both text-to-speech (TTS) and stock audio for motivational messages, making it a powerful tool for self-awareness and behavior management.

## Table of Contents
- [Features](#features)
- [What's New](#whats-new)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [UI Overview](#ui-overview)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Features
- **Real-Time Detection**: Utilizes MediaPipe for precise hand and face landmark detection to identify potential hair-pulling gestures, with configurable full-head or above-eye detection modes.
- **Audio Feedback**: Supports motivational phrases via Google Text-to-Speech (gTTS) with caching or user-uploaded stock audio files (.mp4, .wav) for interruption alerts.
- **Scalable UI**: Tkinter-based interface with a resizable video feed (default 640x480, 4:3 aspect ratio), dynamic font sizing, and dark/light theme support.
- **Settings Tab**: Adjust detection parameters (trigger cooldown, required duration, pull threshold, max head distance), camera settings (exposure, brightness, contrast, gamma), and audio settings (TTS cache limit) using sliders and checkboxes.
- **Camera Settings Tab**: Fine-tune webcam settings for optimal performance under varying lighting conditions.
- **Triggers Tab**: Interactive calendar (`tkcalendar`) highlighting days with triggers, displaying daily trigger counts upon selection.
- **Statistics Tab**: Visualizes daily trigger trends and hourly distribution using matplotlib graphs, updated in real-time.
- **Phrases Tab**: Manage motivational phrases for TTS or upload stock audio files with drag-and-drop support (via `tkinterdnd2`).
- **Persistent Storage**: Saves settings in `config.json`, trigger statistics in `hair_stats.json`, and motivational phrases in `phrases.json`.
- **Cross-Platform**: Tested on Windows 10/11 (Linux/macOS might require minor adjustments)
- **Customizable**: Extensive configuration options for detection sensitivity, audio preferences, and camera settings via the UI or configuration files.

## What's New
The updated version of Trichotillomania Reminder introduces significant enhancements and new features to improve usability, flexibility, and performance:

- **New Camera Settings Tab**: Added a dedicated tab for adjusting camera parameters, including exposure (-10 to 10), brightness (-100 to 100), contrast (0.1 to 3.0), and gamma (0.1 to 5.0), allowing users to optimize video feed quality for different lighting conditions.
- **Enhanced Detection Options**:
  - Added `full_head_detection` toggle to detect hand proximity across the entire head (e.g., beard, eyebrows) or restrict to above-eye level.
  - Introduced `max_head_distance` setting (10-200 pixels) to adjust the proximity threshold for gesture detection, improving accuracy.
- **Statistics Visualization**: New Statistics tab with two matplotlib graphs:
  - **Daily Triggers Trend**: Bar chart showing trigger counts for the past week.
  - **Hourly Triggers Distribution**: Bar chart displaying trigger frequency by hour, with peak time annotation.
- **Phrases Management**:
  - Added Phrases tab to manage motivational messages, supporting both TTS phrases (editable via a listbox) and stock audio files (drag-and-drop upload).
  - Toggle between TTS and stock audio modes, with automatic cache management for TTS audio (configurable limit: 10-1000 MB).
- **UI Improvements**:
  - Added dark/light theme toggle for better accessibility.
  - Improved layout with resizable tabs and dynamic video feed sizing.
  - Enhanced status feedback with real-time FPS, detection status, and camera error messages.
- **Configuration Enhancements**:
  - Expanded `config.json` with new settings for `full_head_detection`, `show_meshes`, `max_head_distance`, and `tts_cache_limit`.
  - Added `phrases.json` for persistent storage of user-defined motivational phrases.
- **Camera Management**: Improved `CameraManager` with robust initialization, automatic retry for camera connection, and overexposure adjustment.
- **Performance Optimizations**:
  - Optimized MediaPipe model complexity (`model_complexity=0`) for faster hand detection.
  - Reduced FPS to 15 for better performance on lower-end hardware.
- **Bug Fixes**:
  - Fixed calendar selected day text visibility issue (work in progress for full resolution).
  - Improved error handling for camera initialization and audio playback.

## Requirements
- **Operating System**: Windows 10/11 (tested); Linux/macOS may require adjustments.
- **Hardware**:
  - Webcam (USB or built-in).
  - Microphone/speakers for audio feedback.
  - At least 4GB RAM and a modern CPU for real-time processing.
- **Software**:
  - Python 3.8+ (via Anaconda or your prefered distribution).
  - Conda environment named "tricho" (for example) with required packages (see [Installation](#installation)).
- **Dependencies** (installed in Conda environment):
  - `opencv-python`: For webcam capture and image processing.
  - `mediapipe`: For hand and face landmark detection.
  - `pygame`: For audio playback.
  - `gTTS`: For text-to-speech motivational phrases.
  - `Pillow`: For image handling in Tkinter.
  - `sv-ttk`: For Sun Valley theme (modern UI look).
  - `tkcalendar`: For calendar-based trigger monitoring.
  - `tkinterdnd2`: For drag-and-drop audio file support (optional).
  - `matplotlib`: For statistics visualization.
  - `numpy`: For numerical computations in detection and visualization.

## Installation
The program is designed to run in a Conda environment named "tricho" located at `C:\PATH`.

### Step 1: Install Anaconda
1. Download and install Anaconda from [anaconda.com](https://www.anaconda.com/products/distribution).
2. Verify installation:
   ```bash
   conda --version
   ```
   Expected output: most recent version or similar.

### Step 2: Set Up the Conda Environment
1. Open Anaconda Prompt or a terminal.
2. Create the "tricho" environment:
   ```bash
   conda create -n tricho python=3.8
   ```
3. Activate the environment:
   ```bash
   conda activate tricho
   ```
4. Install required packages:
   ```bash
   pip install opencv-python mediapipe pygame gTTS Pillow sv-ttk tkcalendar tkinterdnd2 matplotlib numpy
   ```

### Step 3: Download the Program
1. Save the program files (e.g., `main.py`, `camera_manager.py`, `hair_pulling_detector.py`, etc.) to `C:\PATH` (you can clone the git or download it by clicking on the green "CODE" button in the top right, then select "Download ZIP").
2. Create a batch file (`lancer_tricho.bat`) in the same directory with the following content:
   ```bat
   @echo off
   cd /d "C:\PATH"
   call "%USERPROFILE%\Anaconda3\Scripts\activate.bat" %USERPROFILE%\Anaconda3
   call conda activate tricho
   start cmd /k python main.py
   ```
   This batch file activates the "tricho" environment and runs the program. **Change the "PATH" to the path of your folder and if anaconda is not detected, change the detection path to where your python is located.**

## Usage
1. **Run the Program**:
   - Double-click `lancer_tricho.bat`.
   - Alternatively, in Anaconda Prompt:
     ```bash
     cd C:\PATH
     conda activate tricho
     python main.py
     ```
2. **Interact with the UI**:
   - **Video Feed**: Displays webcam input with hand (green) and face (red) landmarks, eye-level line (blue), and detection status.
   - **Settings Tab**:
     - Adjust **Trigger Cooldown** (0-10s), **Required Duration** (0-5s), **Pull Threshold** (0-30), and **Max Head Distance** (10-200px).
     - Toggle **Full Head Detection** and **Show MediaPipe Meshes**.
     - Click **Save Settings** to apply changes or **Reset to Default** to restore defaults.
   - **Camera Settings Tab**:
     - Adjust **Exposure**, **Brightness**, **Contrast**, and **Gamma** for optimal video quality.
   - **Triggers Tab**:
     - View a calendar with triggers per days.
     - Select a day to display the trigger count (e.g., "Triggers on 2025-05-06: 2").
   - **Statistics Tab**:
     - View daily trigger trends (past week) and hourly distribution graphs.
   - **Phrases Tab**:
     - In **Text Phrases** mode, add, edit, or delete motivational phrases for TTS.
     - In **Audio Files** mode, drag-and-drop `.mp3`/`.wav` files or delete existing ones.
     - Adjust **TTS Cache Limit** (10-1000 MB) for cached audio to avoid too much data being stored if you are tight on disk space.
   - **Theme Toggle**: Switch between dark and light themes via the Settings tab.
3. **Trigger Detection**:
   - Move your hand near your head (within `max_head_distance`) for the specified `required_duration`.
   - The program detects the gesture, plays a motivational phrase, logs the trigger in `hair_stats.json`, and updates the calendar.
4. **Exit**:
   - Click Quit in the Settings tab (for some reason I can't get this to work), **close the window**, **or press `Ctrl+C` in the terminal**.
   - The program saves settings (`config.json`), stats (`hair_stats.json`), and phrases (`phrases.json`) before exiting.

## UI Overview
The UI is divided into two main sections:
- **Left Panel**: Scalable video feed (default 640x480, 4:3 aspect ratio) showing:
  - Webcam input with hand (green) and face (red) landmarks.
  - Blue eye-level line for gesture reference.
  - Camera error messages with a retry button if initialization fails.
- **Right Panel**: Tabbed interface with:
  - **Settings Tab**:
    - Sliders for detection parameters and checkboxes for detection modes.
    - Save/Reset buttons, theme toggle, and quit button.
    - Status labels for detection mode, FPS, and system messages.
  - **Camera Settings Tab**:
    - Sliders for exposure, brightness, contrast, and gamma adjustments.
  - **Triggers Tab**:
    - Calendar with daily trigger count.
    - Label displaying trigger count for the selected date.
  - **Statistics Tab**:
    - Daily trend graph (bar chart) for the past week.
    - Hourly distribution graph with peak time annotation.
  - **Phrases Tab**:
    - Listbox for managing TTS phrases or stock audio files.
    - Entry field for adding/editing phrases (TTS mode only).
    - Buttons for adding, editing, deleting, and saving phrases.
    - Slider for TTS cache limit.

## Configuration
The program uses three configuration files:
- **config.json**:
  - Stores detection, audio, and camera settings.
  - Default values:
    ```json
    {
      "detection": {
        "hand_confidence": 0.7,
        "face_confidence": 0.5,
        "trigger_cooldown": 3,
        "required_duration": 0.75,
        "pull_threshold": 1,
        "max_head_distance": 100,
        "full_head_detection": false,
        "show_meshes": true
      },
      "audio": {
        "volume": 1.0,
        "language": "en",
        "tts_cache_limit": 50.0
      },
      "camera": {
        "device": 0,
        "flip": true
      }
    }
    ```
  - Modified via the Settings, Camera Settings, or Phrases tabs or by editing the file directly.
- **hair_stats.json**:
  - Stores daily trigger counts and timestamps.
  - Example:
    ```json
    {
      "daily_stats": {"2025-05-06": 2, "2025-05-05": 1},
      "triggers": [1651804800.0, 1651804860.0]
    }
    ```
  - Updated automatically when triggers are detected.
- **phrases.json**:
  - Stores TTS motivational phrases.
  - Default:
    ```json
    [
      "You're stronger than this urge!",
      "Keep your hands free!",
      "You’ve got this, stay strong!",
      "Take a deep breath and relax."
    ]
    ```
  - Modified via the Phrases tab.

## Troubleshooting
- **Camera Not Found**:
  - Error: `"Error: Could not open camera"`.
  - Fix: Ensure the webcam is connected and not in use. Check `config.json` for correct `camera.device` (default: 0). Retry using the "Retry Camera" button in the UI.
  - Verify: Run `python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"`. Should output `True`.
- **Poor Video Quality**:
  - Issue: Video feed is too dark, bright, or low-contrast.
  - Fix: Adjust exposure, brightness, contrast, or gamma in the Camera Settings tab.
- **Calendar Not Displaying**:
  - Error: `"No module named 'tkcalendar'"`.
  - Fix: Install `tkcalendar`:
    ```bash
    conda activate tricho
    pip install tkcalendar
    ```
- **No Triggers Recorded**:
  - Check: Open `hair_stats.json`. If empty, trigger a detection by moving your hand near your head.
  - Verify: Ensure `required_duration`, `pull_threshold`, and `max_head_distance` in the Settings tab are reasonable.
- **Audio Not Playing**:
  - Error: `"Audio playback error"`.
  - Fix: Ensure speakers are connected. Check `stock_audio` for valid `.mp3`/`.wav` files or enable TTS in the Phrases tab. Verify `phrases.json` has valid phrases.
- **Drag-and-Drop Not Working**:
  - Error: `"tkinterdnd2 not installed"`.
  - Fix: Install `tkinterdnd2`:
    ```bash
    conda activate tricho
    pip install tkinterdnd2
    ```

- **Conda Environment Issues**:
  - Error: `"conda not recognized"` or `"environment tricho not found"`.
  - Fix: Verify Anaconda installation (`conda --version`) and environment (`conda env list`). Recreate the environment if needed:
    ```bash
    conda create -n tricho python=3.8
    ```

## Contributing
Contributions are welcome! To contribute:
1. Fork the repository (if hosted on GitHub).
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Make changes and test thoroughly.
4. Submit a pull request with a clear description of changes.

Suggested improvements:
- Add monthly/yearly trigger summaries or CSV export for stats.
- Support additional languages for TTS.
- Optimize MediaPipe for lower-end hardware.
- Enhance drag-and-drop with multi-file upload validation.
- Improve video embedding compatibility for non-GitHub Markdown renderers.

## License
This project is licensed under the GPL-3.0 license. See the `LICENSE` file for details.

## Acknowledgments
- **MediaPipe**: For robust hand and face tracking.
- **tkcalendar**: For the calendar widget in the Triggers tab.
- **sv-ttk**: For the modern Sun Valley theme.
- **gTTS**: For text-to-speech functionality.
- **OpenCV**: For webcam capture and image processing.
- **matplotlib**: For statistics visualization.
- **tkinterdnd2**: For drag-and-drop audio file support.

---

**Contact**: For support or feature requests, contact the developer via email or GitHub issues (if hosted).

**Version**: 2.0.0 (May 2025)

**Happy monitoring, and stay strong in managing trichotillomania!**
