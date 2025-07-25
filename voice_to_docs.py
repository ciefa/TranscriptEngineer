#!/usr/bin/env python3
"""
Voice to Engineering Requirements - Transform speech into actionable engineering tasks
Record voice → Transcribe with Whisper → Convert to structured requirements with Claude AI
"""

import os
import sys
import time
import tempfile
import wave
import threading
import contextlib

import pyaudio
import whisper
import click
from colorama import init, Fore, Style
from anthropic import Anthropic
from dotenv import load_dotenv
from github import Github

# Load environment variables
load_dotenv()

# Initialize colorama
init()

@contextlib.contextmanager
def suppress_stderr():
    """Suppress stderr output temporarily (for ALSA/JACK warnings)"""
    with open(os.devnull, "w") as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr

class VoiceToDocs:
    def __init__(self, api_key=None, audio_device=None, mode="normal", github_token=None, github_repo=None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self.client = Anthropic(api_key=self.api_key)
        self.mode = mode
        
        # GitHub integration setup
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self.github_repo = github_repo or os.getenv('GITHUB_REPO')
        self.github_client = None
        self.repo = None
        
        if self.github_token and self.github_repo:
            try:
                self.github_client = Github(self.github_token)
                self.repo = self.github_client.get_repo(self.github_repo)
                print(f"{Fore.GREEN}✓ GitHub integration enabled for {self.github_repo}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}⚠ GitHub integration failed: {e}{Style.RESET_ALL}")
        
        # Load Whisper model
        print(f"{Fore.YELLOW}Loading Whisper model...{Style.RESET_ALL}")
        self.whisper_model = whisper.load_model("base")
        print(f"{Fore.GREEN}✓ Whisper model loaded{Style.RESET_ALL}")
        
        # Audio settings
        self.sample_rate = 44100
        self.chunk_size = 4096
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        
        # Configure audio device
        self.input_device = self._configure_audio_device(audio_device)
        
        # Load system prompt based on mode
        self.system_prompt = self._get_system_prompt()

    @staticmethod
    def list_audio_devices():
        """List all available audio input devices"""
        devices = []
        
        with suppress_stderr():
            audio = pyaudio.PyAudio()
            try:
                for i in range(audio.get_device_count()):
                    device_info = audio.get_device_info_by_index(i)
                    if device_info['maxInputChannels'] > 0:  # Only input devices
                        devices.append({
                            'index': i,
                            'name': device_info['name'],
                            'channels': device_info['maxInputChannels'],
                            'sample_rate': int(device_info['defaultSampleRate'])
                        })
            except Exception as e:
                print(f"{Fore.RED}Error listing audio devices: {e}{Style.RESET_ALL}")
            finally:
                audio.terminate()
        
        return devices

    def _configure_audio_device(self, device_param):
        """Configure audio device with fallback logic"""
        # Try device parameter first (CLI option)
        if device_param is not None:
            return self._validate_audio_device(device_param)
        
        # Try environment variable
        env_device = os.getenv('AUDIO_DEVICE')
        if env_device:
            try:
                device_index = int(env_device)
                return self._validate_audio_device(device_index)
            except ValueError:
                print(f"{Fore.YELLOW}Warning: Invalid AUDIO_DEVICE value '{env_device}', using auto-detection{Style.RESET_ALL}")
        
        # Auto-detect suitable device
        return self._auto_detect_audio_device()

    def _validate_audio_device(self, device_index):
        """Validate that the specified device exists and supports input"""
        with suppress_stderr():
            audio = pyaudio.PyAudio()
            try:
                device_info = audio.get_device_info_by_index(device_index)
                if device_info['maxInputChannels'] == 0:
                    raise ValueError(f"Device {device_index} doesn't support audio input")
                
                print(f"{Fore.GREEN}✓ Using audio device {device_index}: {device_info['name']}{Style.RESET_ALL}")
                return device_index
                
            except (OSError, ValueError) as e:
                raise ValueError(f"Invalid audio device {device_index}: {e}")
            finally:
                audio.terminate()

    def _auto_detect_audio_device(self):
        """Auto-detect the best available audio input device"""
        devices = self.list_audio_devices()
        
        if not devices:
            raise ValueError("No audio input devices found")
        
        # Try to find a USB or external device first (often better quality)
        for device in devices:
            name_lower = device['name'].lower()
            if any(keyword in name_lower for keyword in ['usb', 'hyperx', 'blue', 'rode', 'shure']):
                print(f"{Fore.GREEN}✓ Auto-detected audio device {device['index']}: {device['name']}{Style.RESET_ALL}")
                return device['index']
        
        # Fall back to default input device (usually index 0 or system default)
        default_device = devices[0]
        print(f"{Fore.YELLOW}Using default audio device {default_device['index']}: {default_device['name']}{Style.RESET_ALL}")
        return default_device['index']

    def _get_system_prompt(self):
        """Get system prompt based on mode"""
        # Check for custom prompt first
        custom_prompt = os.getenv('SYSTEM_PROMPT')
        if custom_prompt:
            return custom_prompt
        
        if self.mode == "agile-pm":
            return """You are an expert Agile Product Manager who creates comprehensive GitHub issues from casual speech.

Your task is to take spoken descriptions and transform them into professionally formatted GitHub issues with:

**User Story Format:**
- As a [user type]
- I want [functionality] 
- So that [benefit/value]

**Required Sections:**
1. **User Story** - Clear user-focused narrative
2. **Acceptance Criteria** - Specific, testable requirements (use checkboxes)
3. **Technical Requirements** - Implementation details, standards, tools
4. **Implementation Checklist** - Step-by-step tasks (use checkboxes)
5. **Dependencies** - What's needed before starting
6. **Effort Estimate** - Size (XS/S/M/L/XL) and time estimate

**Formatting Guidelines:**
- Use GitHub markdown with headers (##), checkboxes (- [ ]), code blocks
- Include specific examples and code snippets when relevant
- Make acceptance criteria measurable and testable
- Break down complex features into clear implementation steps
- Add labels suggestions like `enhancement`, `bug`, `accessibility`, etc.

Focus on creating issues that are immediately actionable for developers while maintaining product management best practices."""

        else:  # normal mode
            return """You are an expert software engineer who helps convert casual speech into clear, actionable engineering requirements.

Your task is to take my spoken transcript and transform it into:
- Clear bug reports with steps to reproduce
- Structured feature requirements 
- Technical specifications
- Implementation tasks
- Code review feedback

Focus on making the speech more precise, organized, and actionable for engineering work. Preserve the technical intent but make it more structured and professional."""

    def record_audio(self):
        """Record audio until user presses Enter"""
        print(f"{Fore.YELLOW}🎤 Recording started...{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Press ENTER to stop recording{Style.RESET_ALL}")
        
        frames = []
        recording = True
        
        def stop_recording():
            nonlocal recording
            input()  # Wait for Enter
            recording = False
        
        # Start stop listening thread
        stop_thread = threading.Thread(target=stop_recording)
        stop_thread.daemon = True
        stop_thread.start()
        
        # Initialize audio
        with suppress_stderr():
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.input_device,
                frames_per_buffer=self.chunk_size
            )
        
        print(f"{Fore.GREEN}🔴 Recording... Press ENTER to stop{Style.RESET_ALL}")
        
        # Record until Enter is pressed
        while recording:
            try:
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                frames.append(data)
            except Exception:
                continue
        
        # Clean up
        stream.stop_stream()
        stream.close()
        audio.terminate()
        
        if not frames:
            print(f"{Fore.YELLOW}No audio recorded{Style.RESET_ALL}")
            return None
        
        print(f"{Fore.GREEN}✓ Recording complete!{Style.RESET_ALL}")
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        with wave.open(temp_file.name, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(frames))
        
        return temp_file.name

    def transcribe_audio(self, audio_file_path):
        """Transcribe audio to text using Whisper"""
        print(f"{Fore.YELLOW}🔄 Transcribing audio with Whisper...{Style.RESET_ALL}")
        
        try:
            result = self.whisper_model.transcribe(
                audio_file_path,
                language='en',
                task='transcribe',
                fp16=False,
                verbose=False
            )
            transcript = result["text"].strip()
            
            # Clean up temp file
            os.unlink(audio_file_path)
            
            if not transcript or len(transcript) < 3:
                raise Exception("No clear speech detected - try speaking louder or closer to the microphone")
            
            print(f"{Fore.GREEN}✓ Transcription complete!{Style.RESET_ALL}")
            return transcript
            
        except Exception as e:
            try:
                os.unlink(audio_file_path)
            except:
                pass
            raise Exception(f"Transcription failed: {e}")

    def process_with_claude(self, transcript):
        """Process transcript with Claude AI"""
        print(f"{Fore.YELLOW}🤖 Processing with Claude AI...{Style.RESET_ALL}")
        
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=self.system_prompt,
                messages=[
                    {
                        "role": "user", 
                        "content": f"Please convert this casual speech into clear, actionable engineering requirements:\n\n{transcript}"
                    }
                ]
            )
            
            processed_text = response.content[0].text
            print(f"{Fore.GREEN}✓ Claude processing complete!{Style.RESET_ALL}")
            return processed_text
            
        except Exception as e:
            raise Exception(f"Error calling Claude API: {e}")

    def create_github_issue(self, title, body, labels=None):
        """Create a GitHub issue from the processed requirements"""
        if not self.repo:
            print(f"{Fore.YELLOW}⚠ GitHub integration not configured{Style.RESET_ALL}")
            return None
        
        try:
            # Create the issue
            issue = self.repo.create_issue(
                title=title,
                body=body,
                labels=labels or []
            )
            
            print(f"{Fore.GREEN}✓ Created GitHub issue: {issue.html_url}{Style.RESET_ALL}")
            return issue
            
        except Exception as e:
            print(f"{Fore.RED}❌ Failed to create GitHub issue: {e}{Style.RESET_ALL}")
            return None

    def extract_title_from_requirements(self, requirements):
        """Extract a suitable title from the processed requirements"""
        lines = requirements.split('\n')
        
        # Look for common patterns in the first few lines
        for line in lines[:10]:
            line = line.strip()
            if not line:
                continue
                
            # Remove markdown formatting
            clean_line = line.replace('#', '').replace('*', '').replace('`', '').strip()
            
            # Skip if it's a section header we don't want
            if any(skip in clean_line.lower() for skip in ['user story', 'acceptance criteria', 'technical requirements']):
                continue
            
            # If it looks like a good title (reasonable length, not too technical)
            if 10 <= len(clean_line) <= 100 and not clean_line.startswith('As a'):
                return clean_line
        
        # Fallback: try to extract from user story
        for line in lines:
            if 'I want' in line:
                # Extract the "I want" part
                want_part = line.split('I want')[1].split('So that')[0].strip()
                return f"Implement: {want_part}"
        
        # Last resort
        return "New requirement from voice input"

    def run_session(self):
        """Run a complete recording and processing session"""
        try:
            # Record audio
            audio_file = self.record_audio()
            
            if audio_file is None:
                print(f"{Fore.YELLOW}No audio recorded{Style.RESET_ALL}")
                return None, None
            
            # Transcribe
            transcript = self.transcribe_audio(audio_file)
            
            # Display original transcript
            print(f"\n{Fore.MAGENTA}📝 Original Transcript:{Style.RESET_ALL}")
            print(f"{Fore.WHITE}{transcript}{Style.RESET_ALL}")
            
            # Process with Claude
            processed = self.process_with_claude(transcript)
            
            # Display processed result
            mode_label = "Agile PM Issue" if self.mode == "agile-pm" else "Engineering Requirements"
            print(f"\n{Fore.CYAN}🔧 {mode_label}:{Style.RESET_ALL}")
            print(f"{Fore.WHITE}{processed}{Style.RESET_ALL}")
            
            # Ask about GitHub issue creation
            if self.repo and self.mode == "agile-pm":
                print(f"\n{Fore.YELLOW}Create GitHub issue? (y/n):{Style.RESET_ALL}")
                create_issue = input().strip().lower()
                
                if create_issue in ['y', 'yes']:
                    title = self.extract_title_from_requirements(processed)
                    self.create_github_issue(title, processed, ['enhancement'])
            
            return transcript, processed
            
        except Exception as e:
            print(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
            return None, None

@click.command()
@click.option('--api-key', '-k', help='Anthropic API key (or set ANTHROPIC_API_KEY env var)')
@click.option('--device', '-d', type=int, help='Audio input device index (use --list-devices to see options)')
@click.option('--list-devices', is_flag=True, help='List available audio input devices and exit')
@click.option('--mode', '-m', 
              type=click.Choice(['normal', 'agile-pm']), 
              default='normal',
              help='Processing mode: normal (default) or agile-pm for GitHub issues')
@click.option('--github-token', '-gt', help='GitHub personal access token (or set GITHUB_TOKEN env var)')
@click.option('--github-repo', '-gr', help='GitHub repository in format owner/repo (or set GITHUB_REPO env var)')
def main(api_key, device, list_devices, mode, github_token, github_repo):
    """Voice to Engineering Requirements - Record, transcribe, and convert speech to actionable engineering tasks"""
    
    # Handle --list-devices flag
    if list_devices:
        print(f"{Fore.CYAN}📋 Available Audio Input Devices:{Style.RESET_ALL}")
        devices = VoiceToDocs.list_audio_devices()
        
        if not devices:
            print(f"{Fore.RED}❌ No audio input devices found{Style.RESET_ALL}")
            sys.exit(1)
        
        for dev in devices:
            print(f"{Fore.GREEN}  {dev['index']}: {dev['name']} "
                  f"({dev['channels']} channels, {dev['sample_rate']} Hz){Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}Usage: python voice_to_docs.py --device <index>{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}   or: export AUDIO_DEVICE=<index>{Style.RESET_ALL}")
        return
    
    print(f"{Fore.GREEN}🚀 Voice to Engineering Requirements Starting...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Mode: {mode.upper()}{' (GitHub Issues)' if mode == 'agile-pm' else ''}{Style.RESET_ALL}")
    
    try:
        voice_to_docs = VoiceToDocs(
            api_key=api_key, 
            audio_device=device,
            mode=mode,
            github_token=github_token,
            github_repo=github_repo
        )
        
        while True:
            print(f"\n{Fore.YELLOW}Press Enter to start recording (or 'q' to quit):{Style.RESET_ALL}")
            user_input = input().strip().lower()
            
            if user_input == 'q':
                print(f"{Fore.GREEN}👋 Goodbye!{Style.RESET_ALL}")
                break
            
            voice_to_docs.run_session()
            
    except ValueError as e:
        print(f"{Fore.RED}❌ Configuration Error: {e}{Style.RESET_ALL}")
        if "ANTHROPIC_API_KEY" in str(e):
            print(f"{Fore.YELLOW}💡 Set your API key in .env file: ANTHROPIC_API_KEY=your-key-here{Style.RESET_ALL}")
        elif "audio device" in str(e).lower():
            print(f"{Fore.YELLOW}💡 List available devices: python voice_to_docs.py --list-devices{Style.RESET_ALL}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n{Fore.GREEN}👋 Goodbye!{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}❌ Unexpected error: {e}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == '__main__':
    main()