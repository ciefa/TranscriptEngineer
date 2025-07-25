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

import pyaudio
import whisper
import click
from colorama import init, Fore, Style
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize colorama
init()

class VoiceToDocs:
    def __init__(self, api_key=None, audio_device=None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self.client = Anthropic(api_key=self.api_key)
        
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
        
        # Load system prompt
        custom_prompt = os.getenv('SYSTEM_PROMPT')
        if custom_prompt:
            self.system_prompt = custom_prompt
        else:
            self.system_prompt = """You are an expert software engineer who helps convert casual speech into clear, actionable engineering requirements.

Your task is to take my spoken transcript and transform it into:
- Clear bug reports with steps to reproduce
- Structured feature requirements 
- Technical specifications
- Implementation tasks
- Code review feedback

Focus on making the speech more precise, organized, and actionable for engineering work. Preserve the technical intent but make it more structured and professional."""

    @staticmethod
    def list_audio_devices():
        """List all available audio input devices"""
        audio = pyaudio.PyAudio()
        devices = []
        
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

    def record_audio(self):
        """Record audio until user presses Enter"""
        print(f"{Fore.YELLOW}🎤 Recording started...{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Press ENTER to stop recording{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}(Ignore ALSA warnings below - they're normal on Linux){Style.RESET_ALL}")
        
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
            print(f"\n{Fore.CYAN}🔧 Engineering Requirements:{Style.RESET_ALL}")
            print(f"{Fore.WHITE}{processed}{Style.RESET_ALL}")
            
            return transcript, processed
            
        except Exception as e:
            print(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
            return None, None

@click.command()
@click.option('--api-key', '-k', help='Anthropic API key (or set ANTHROPIC_API_KEY env var)')
@click.option('--device', '-d', type=int, help='Audio input device index (use --list-devices to see options)')
@click.option('--list-devices', is_flag=True, help='List available audio input devices and exit')
def main(api_key, device, list_devices):
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
    
    print(f"{Fore.GREEN}🚀 Voice to Docs Starting...{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Note: ALSA audio warnings are normal on Linux and don't affect functionality{Style.RESET_ALL}")
    
    try:
        voice_to_docs = VoiceToDocs(api_key, device)
        
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