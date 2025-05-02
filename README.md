# Webcam Eyes - Hair Pulling Detection

Webcam Eyes is a Python application designed to detect hair-pulling behavior using computer vision and provide audio feedback to help users manage trichotillomania. It uses a webcam to track hand and facial landmarks, detecting when a hand approaches the head and potentially engages in hair-pulling motions. The application offers motivational audio feedback, either through text-to-speech (TTS) or pre-recorded stock audio files.

# Features





Real-time hand and face tracking using MediaPipe



Configurable detection sensitivity and audio feedback



Support for both TTS and stock audio files



Visual feedback with on-screen controls and settings



Adjustable parameters for detection cooldown, duration, and movement threshold



Statistics tracking for daily hair-pulling triggers

# Prerequisites





Python 3.8 or higher



A webcam (USB or integrated)



Speakers or headphones for audio feedback

# Dependencies

The application relies on the following Python packages. Install them using pip:

pip install opencv-python mediapipe pygame numpy gTTS

Dependency Details





opencv-python: For webcam access and image processing



mediapipe: For hand and face landmark detection



pygame: For audio playback



numpy: For numerical computations and array operations



gTTS: For text-to-speech functionality

Optional Setup for Stock Audio

If you prefer using pre-recorded audio files instead of TTS:





Create a folder named static/stock_audio in the project directory.



Place .mp3 or .wav audio files in this folder.



The application will automatically detect and use these files if present.

Installation





Clone or download this repository to your local machine.



Install the required dependencies:

pip install opencv-python mediapipe pygame numpy gTTS



Ensure your webcam is connected and functional.



(Optional) Set up the static/stock_audio folder with audio files if using stock audio.

Usage





Run the script:

python webcam_eyes.py



If stock audio files are found, choose between:





1: Text-to-speech feedback



2: Stock audio files (default)



The application will initialize the webcam and start tracking.



Use the following controls:





Q: Quit the application



S: Toggle the settings window



A: Apply settings changes (when settings window is active)



R: Reset settings to default



Adjust detection parameters in the settings window using trackbars.

Configuration

The application uses a config.json file (auto-generated) to store settings. Key parameters include:





Detection:





hand_confidence: Minimum confidence for hand detection (default: 0.7)



face_confidence: Minimum confidence for face detection (default: 0.5)



trigger_cooldown: Minimum time between alerts (default: 3 seconds)



required_duration: Time hand must be near head to trigger (default: 0.75 seconds)



pull_threshold: Sensitivity for detecting pulling motion (default: 1)



max_head_distance: Maximum distance between hand and head (default: 150 pixels)



Audio:





volume: Audio playback volume (default: 1.0)



language: TTS language (default: "fr" for French)



Camera:





device: Camera index (default: 0)



flip: Flip camera feed horizontally (default: True)

Troubleshooting





No camera found: Ensure your webcam is connected and not in use by another application. Check available cameras with the script's camera detection.



Audio issues: Verify that speakers are connected and not muted. Ensure audio files are valid if using stock audio.



Performance issues: Adjust process_every_n_frames in the code (default: 3) to skip more frames and reduce CPU load.



Overexposure: The application automatically adjusts exposure, but you may need to tweak lighting conditions for optimal detection.

Notes





The application is optimized for a single user facing the webcam.



For best results, ensure good lighting and minimal background movement.



The static/generated_audio folder is used for caching TTS audio files.



The application may require a short delay (2 seconds) at startup to initialize the webcam.

License

This project is licensed under the MIT License. See the LICENSE file for details.
