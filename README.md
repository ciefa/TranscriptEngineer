# Voice to Engineering Requirements

A terminal application that records your voice, transcribes it with Whisper, and processes it through Claude AI to transform casual speech into clear, actionable engineering requirements. Now with **multiple modes** and **GitHub integration**!

## Features

- Record audio from your microphone with flexible controls
- Simple recording: Press Enter to start, Enter again to stop
- Transcribe speech to text using OpenAI Whisper (offline)
- Convert casual speech into structured engineering requirements with Claude AI
- Colored terminal output for better UX
- Interactive session mode
- Perfect for describing bugs, features, or technical tasks verbally
- **Multiple processing modes** (Normal + Agile Product Manager)
- **GitHub integration** - automatically create issues from speech
- **Professional issue formatting** with user stories, acceptance criteria, and checklists
- **Interactive mode switching** - press 'a' for Agile-PM, 'n' for Normal
- **Smart GitHub detection** - just say "make a GitHub issue" in your speech!

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

### Interactive Controls
- **[Enter]** - Start recording
- **[a]** - Switch to Agile Product Manager mode
- **[n]** - Switch to Normal mode  
- **[q]** - Quit

### Recording Flow
- Describe your bug, feature request, or technical task naturally
- Press Enter again to stop recording
- View your original transcript and the structured requirements
- For GitHub issues, just say "**make a GitHub issue**" or "**create an issue**" in your speech!

### Smart GitHub Integration
The app automatically detects when you want a GitHub issue created:
- "I found a bug in the login system, **make a GitHub issue** for it"
- "We need dark mode support, **create an issue** for this"
- "The API is slow, **put this in GitHub** as a performance issue"

**See it in action!** Check out this [sample GitHub issue](https://github.com/ciefa/TranscriptEngineer/issues/1) created entirely from voice input using Agile-PM mode - complete with user story, acceptance criteria, technical requirements, and implementation checklist!

## Modes

### Normal Mode (Default)
Converts speech into structured engineering requirements, bug reports, and technical specifications.

### Agile Product Manager Mode
Creates comprehensive GitHub issues with:
- **User Stories** in "As a... I want... So that..." format
- **Acceptance Criteria** with testable requirements
- **Technical Requirements** and implementation details
- **Implementation Checklists** with step-by-step tasks
- **Dependencies** and effort estimates
- **Professional formatting** ready for development teams

## GitHub Integration

When using Agile PM mode with GitHub configured, you can automatically create issues:

1. **Setup GitHub integration:**
   ```bash
   export GITHUB_TOKEN=your-personal-access-token
   export GITHUB_REPO=username/repository-name
   ```

2. **Record your feature/bug description**

3. **Choose to create GitHub issue** when prompted

4. **Issue appears in your repository** with professional formatting!

## Options

- `--api-key`, `-k`: Provide API key directly instead of using environment variable
- `--device`, `-d`: Specify audio input device index (use `--list-devices` to see options)
- `--list-devices`: List all available audio input devices and exit
- `--mode`, `-m`: Processing mode (`normal` or `agile-pm`)
- `--github-token`, `-gt`: GitHub personal access token
- `--github-repo`, `-gr`: GitHub repository in format `owner/repo`

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

## Example Usage

```bash
# Basic usage (normal mode)
./run.sh

# Agile Product Manager mode for GitHub issues
./run.sh --mode agile-pm

# With GitHub integration
./run.sh --mode agile-pm --github-repo username/my-project

# List available audio devices  
./run.sh --list-devices

# Use specific audio device
./run.sh --device 2

# Traditional python execution
source venv/bin/activate
python voice_to_docs.py --mode agile-pm --github-repo username/repo
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
- GitHub personal access token (optional, for issue creation)