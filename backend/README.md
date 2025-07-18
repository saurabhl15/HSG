# Real-Time Multilingual Sermon Translation Backend

This backend provides real-time audio translation for live sermons, converting English speech to Hindi, Telugu, and Kannada, and streaming the translated audio to clients.

## Architecture Overview

- **audio_input.py**: Handles real-time audio input (from mic, Zoom, etc.).
- **asr.py**: Integrates with Azure Speech SDK for real-time English transcription.
- **chunker.py**: Segments ASR output into translation-ready chunks.
- **translation.py**: Translates English text to target languages using Azure Translator API.
- **tts.py**: Converts translated text to audio using Azure Neural TTS.
- **streamer.py**: Streams audio to clients (HLS/WebRTC).
- **main.py**: Orchestrates the pipeline and exposes API endpoints (FastAPI).

Each module contains dummy functions with documented inputs and outputs for further development.

## Getting Started

### 1. Create a Conda Environment

```bash
conda create -n sermon-rt-translate python=3.10
conda activate sermon-rt-translate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the FastAPI App (Dev)

```bash
uvicorn main:app --reload
```

Run the above command from inside the `backend/` directory.
