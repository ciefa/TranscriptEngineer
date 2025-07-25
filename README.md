# Voice to Docs

A terminal application that records your voice, transcribes it with Whisper, and processes it through Claude AI to transform casual speech into professional engineering documentation.

## Features

- 🎤 Record audio from your microphone with flexible controls
- ⌨️ Simple recording: Press Enter to start, Enter again to stop
- 🔄 Transcribe speech to text using OpenAI Whisper (offline)
- 🤖 Process transcripts with Claude AI using an engineering-focused prompt
- 🎨 Colored terminal output for better UX
- 🔁 Interactive session mode

## Setup

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set your Anthropic API key (choose one method):

   **Option A - Environment variable:**
   ```bash
   export ANTHROPIC_API_KEY='your-api-key-here'
   ```

   **Option B - .env file:**
   ```bash
   echo "ANTHROPIC_API_KEY=your-api-key-here" > .env
   ```

4. (Optional) Customize the AI prompt by adding to your .env file:
   ```bash
   echo 'SYSTEM_PROMPT=You are an expert [your role]. Transform transcripts into [your desired output format].' >> .env
   ```

5. Run the application:
```bash
source venv/bin/activate  # if not already activated
python voice_to_docs.py
```

## Usage

- Press Enter to start recording
- Speak as long as you want  
- Press Enter again to stop recording
- View your original transcript and the AI-processed engineering documentation
- Type 'q' to quit

## Options

- `--api-key`, `-k`: Provide API key directly instead of using environment variable
- `--device`, `-d`: Specify audio input device index (use `--list-devices` to see options)
- `--list-devices`: List all available audio input devices and exit

## Audio Device Configuration

The application automatically detects the best available audio input device, but you can customize this:

**List available devices:**
```bash
python voice_to_docs.py --list-devices
```

**Use specific device:**
```bash
python voice_to_docs.py --device 2
```

**Set device via environment variable:**
```bash
export AUDIO_DEVICE=2
python voice_to_docs.py
```

The auto-detection prioritizes USB and external microphones (HyperX, Blue, Rode, Shure) over built-in devices for better audio quality.

## Example

```bash
source venv/bin/activate
python voice_to_docs.py
```

## Testing

Run the test suite to verify functionality:

```bash
source venv/bin/activate
python test_voice_to_docs.py
```

The tests use mocking to verify core logic without requiring actual hardware or API calls.

## System Requirements

- Python 3.7+
- Microphone access
- Internet connection (for Claude AI only - Whisper transcription works offline)
- Anthropic API key