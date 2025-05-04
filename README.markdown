# Trichotillomania Reminder

![Trichotillomania Reminder UI](UI.png) <!-- Placeholder for screenshot -->

**Trichotillomania Reminder** is a computer vision-based application designed to help individuals with trichotillomania (compulsive hair-pulling) by detecting hair-pulling gestures and providing audio feedback to interrupt the behavior. The program uses real-time webcam input, MediaPipe for hand and face tracking, and a Tkinter-based user interface with scalable video feed and settings. It includes a calendar to monitor daily triggers, making it a valuable tool for self-awareness and behavior management.

## Table of Contents
- [Features](#features)
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
- **Real-Time Detection**: Uses MediaPipe to detect hand gestures near the head, identifying potential hair-pulling behavior.
- **Audio Feedback**: Plays motivational phrases via text-to-speech (gTTS) or stock audio files to interrupt detected hair-pulling.
- **Scalable UI**: Tkinter-based interface with a resizable video feed (4:3 aspect ratio) and dynamic font sizing.
- **Settings Tab**: Adjust detection parameters (trigger cooldown, required duration, pull threshold) with sliders and apply/reset buttons.
- **Triggers Tab**: Calendar view (`tkcalendar`) to monitor daily hair-pulling triggers, with red highlights for days with events.
- **Statistics Tracking**: Saves trigger counts in `hair_stats.json` for persistent daily statistics.
- **Cross-Platform**: Runs on Windows (tested) with potential for Linux/macOS (with minor adjustments).
- **Customizable**: Configurable via camera settings, detection sensitivity, and audio preferences.

## Requirements
- **Operating System**: Windows 10/11 (tested); Linux/macOS may require adjustments.
- **Hardware**:
  - Webcam (USB or built-in).
  - Microphone/speakers for audio feedback.
  - At least 4GB RAM and a CPU for real-time processing.
- **Software**:
  - Python 3.8+ (via Anaconda for exemple).
  - Conda environment named with required packages (see [Installation](#installation)).
- **Dependencies** (installed in Conda environment):
  - `opencv-python`: For webcam capture and image processing.
  - `mediapipe`: For hand and face landmark detection.
  - `pygame`: For audio playback.
  - `gTTS`: For text-to-speech motivational phrases.
  - `Pillow`: For image handling in Tkinter.
  - `sv-ttk`: For Sun Valley theme (modern UI look).
  - `tkcalendar`: For calendar-based trigger monitoring.

## Installation
The program is designed to run in a Conda environment with all dependencies.

### Step 1: Install Anaconda
1. Download and install Anaconda from [anaconda.com](https://www.anaconda.com/products/distribution).
2. Verify installation:
   ```bash
   conda --version
   ```
   Expected output: `conda 4.x.x` or similar.

### Step 2: Set Up the Conda Environment
1. Open Anaconda Prompt or a terminal.
2. Create the "name_of_your_env" environment:
   ```bash
   conda create -n name_of_your_env python=3.8
   ```
3. Activate the environment:
   ```bash
   conda activate name_of_your_env
   ```
4. Install required packages:
   ```bash
   pip install opencv-python mediapipe pygame gTTS Pillow sv-ttk tkcalendar
   ```

### Step 3: Download the Program
1. Save `tricho-reminder.py` to the path you want `C:\PATH`.
2. Create a batch file (`lancer_tricho.bat`) in the same directory with the following content:
   ```bat
   @echo off
   cd /d "C:\PATH"
   call "%USERPROFILE%\Anaconda3\Scripts\activate.bat" %USERPROFILE%\Anaconda3
   call conda activate "name_of_your_env"
   start cmd /k python tricho-reminder.py
   ```
   This batch file activates the environment and runs the program.

### Step 4: Prepare Resources
1. Ensure the following directories exist (created automatically on first run):
   - `C:\PATH\audio`: For generated TTS audio files.
   - `C:\PATH\stock_audio`: For optional stock audio files (e.g., `.mp3`, `.wav`).
2. (Optional) Place a custom icon (`icon.ico`) in the project directory for the Tkinter window.

## Usage
1. **Run the Program**:
   - Double-click `lancer_tricho.bat` in `C:\PATH`.
   - Alternatively, in Anaconda Prompt:
     ```bash
     cd C:\PATH
     conda activate name_of_env
     python tricho-reminder.py
     ```
2. **Interact with the UI**:
   - **Video Feed**: Displays webcam input with hand/face landmarks and detection overlays.
   - **Settings Tab**:
     - Adjust **Trigger Cooldown** (seconds between alerts).
     - Adjust **Required Duration** (seconds for detection confirmation).
     - Adjust **Pull Threshold** (sensitivity for gesture detection).
     - Click **Apply** to save changes or **Reset** to restore defaults.
   - **Triggers Tab**:
     - View a calendar with red highlights for days with hair-pulling triggers.
     - Click a day to see the trigger count (e.g., "Triggers on 2025-05-04: 3").
   - **Keyboard Shortcuts**:
     - Press `Q` to quit.
     - Press `R` to reset settings to defaults.
3. **Trigger Detection**:
   - Move your hand near your head (within configured distance) for the specified duration.
   - The program detects the gesture, plays a motivational phrase, and logs the trigger in `hair_stats.json`.
   - The calendar updates with a red highlight for the current day.
4. **Exit**:
   - Press `Q`, close the window, or press `Ctrl+C` in the terminal.
   - The program saves settings (`config.json`) and stats (`hair_stats.json`) before exiting.

## UI Overview
The UI is divided into two main sections:
- **Left Panel**: Scalable video feed (640x480 default, maintains 4:3 aspect ratio) showing:
  - Webcam input with hand and face landmarks (green for hands, red for face contours).
  - Detection progress bar (green) during potential hair-pulling.
  - Eye-level line (yellow) for gesture reference.
  - Overexposure warnings (red text) if lighting is too bright.
- **Right Panel**: Tabbed interface with:
  - **Settings Tab**:
    - Sliders for trigger cooldown (0-10s), required duration (0-5s), and pull threshold (0-30).
    - Apply/Reset buttons.
    - Status labels for FPS, depth ratio (green/red based on hand-head proximity), and controls.
  - **Triggers Tab**:
    - Calendar showing daily triggers (red background for days with triggers, white text).
    - Label displaying trigger count for the selected date.
    - Selected day has a black background with black text (known issue, fix in progress).

## Configuration
The program allows you to modify the camera and detection config
  - Stores detection, audio, and camera settings.
  - Default values:
    {
      "detection": {
        "hand_confidence": 0.7,
        "face_confidence": 0.5,
        "trigger_cooldown": 3,
        "required_duration": 0.75,
        "pull_threshold": 1,
        "max_head_distance": 150
      },
      "audio": {"volume": 1.0, "language": "en"},
      "camera": {"device": 0, "flip": true}
    }
    ```
  - Modified via the Settings tab or by editing the file directly.
- **hair_stats.json**:
  - Stores daily trigger counts.
  - Example:
    ```json
    {"daily_stats": {"2025-05-04": 3, "2025-05-03": 1}}
    ```
  - Updated automatically when triggers are detected.

## Troubleshooting
- **Camera Not Found**:
  - Error: `"Error: Could not open camera"`.
  - Fix: Ensure the webcam is connected and not in use by another application.
  - Verify: Run `python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"`. Should output `True`.
- **Calendar Not Displaying**:
  - Error: `"No module named 'tkcalendar'"`.
  - Fix: Install `tkcalendar` in the "name_of_env" environment:
    ```bash
    conda activate name_of_env
    pip install tkcalendar
    ```
- **Selected Day Text Invisible**:
  - Issue: Selected day in the calendar has black text on a black background.
  - Status: Known issue. A fix is in progress to set the selected day’s text to white.
  - Workaround: Use the trigger count label below the calendar to confirm the selected date’s triggers.
- **No Triggers Recorded**:
  - Check: Open `hair_stats.json`. If empty or missing, trigger a detection by moving your hand near your head.
  - Verify: Ensure `required_duration` and `pull_threshold` in the Settings tab are not too high.
- **Audio Not Playing**:
  - Error: `"Audio playback error"`.
  - Fix: Ensure speakers are connected and not muted. Check `stock_audio` for valid `.mp3`/`.wav` files or enable TTS in `AudioManager` (`use_tts=True`).
- **Conda Environment Issues**:
  - Error: `"conda not recognized"` or `"environment name_of_your_env not found"`.
  - Fix: Verify Anaconda installation (`conda --version`) and environment (`conda env list`). Recreate the environment if needed:
    ```bash
    conda create -n name_of_your_env python=3.8
    ```
- **Logs**:
  - Check the terminal for `ERROR` or `WARNING` messages (e.g., `Invalid date format in daily_stats`).
  - Share logs with support for assistance.

## Contributing
Contributions are welcome! To contribute:
1. Fork the repository (if hosted on GitHub).
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Make changes and test thoroughly.
4. Submit a pull request with a clear description of changes.

Suggested improvements:
- Fix the calendar’s selected day text color (black on black).
- Add monthly trigger summaries or CSV export for stats.
- Support multiple languages for TTS.
- Optimize MediaPipe performance for lower-end hardware.

## License
This project is licensed under the GPL-3.0 license. See the `LICENSE` file for details.

## Acknowledgments
- **MediaPipe**: For robust hand and face tracking.
- **tkcalendar**: For the calendar widget in the Triggers tab.
- **sv-ttk**: For the modern Sun Valley theme.
- **gTTS**: For text-to-speech functionality.
- **OpenCV**: For webcam capture and image processing.

---

**Contact**: For support or feature requests, contact the developer via email or GitHub issues (if hosted).

**Version**: 1.0.0 (May 2025)

**Happy monitoring, and stay strong in managing trichotillomania!**
