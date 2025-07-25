#!/usr/bin/env python3
"""
Tests for voice_to_docs.py

This test suite mocks external dependencies (audio recording, Whisper, Anthropic API)
to test the core logic without requiring actual hardware or API calls.
"""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
import sys

# Add the current directory to Python path for importing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_to_docs import VoiceToDocs


class TestVoiceToDocsConfiguration(unittest.TestCase):
    """Test audio device configuration and validation"""

    @patch('voice_to_docs.pyaudio.PyAudio')
    def test_list_audio_devices(self, mock_pyaudio):
        """Test listing available audio devices"""
        mock_audio = Mock()
        mock_pyaudio.return_value = mock_audio
        mock_audio.get_device_count.return_value = 3
        
        # Mock device info for 3 devices (2 input, 1 output-only)
        device_infos = [
            {'name': 'Built-in Microphone', 'maxInputChannels': 1, 'defaultSampleRate': 44100},
            {'name': 'USB Headset', 'maxInputChannels': 2, 'defaultSampleRate': 48000},
            {'name': 'Speakers', 'maxInputChannels': 0, 'defaultSampleRate': 44100}  # Output only
        ]
        mock_audio.get_device_info_by_index.side_effect = device_infos
        
        devices = VoiceToDocs.list_audio_devices()
        
        # Should only return input devices (first 2)
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0]['name'], 'Built-in Microphone')
        self.assertEqual(devices[1]['name'], 'USB Headset')
        self.assertEqual(devices[1]['channels'], 2)

    @patch('voice_to_docs.pyaudio.PyAudio')
    def test_validate_audio_device_valid(self, mock_pyaudio):
        """Test validation of a valid audio device"""
        mock_audio = Mock()
        mock_pyaudio.return_value = mock_audio
        mock_audio.get_device_info_by_index.return_value = {
            'name': 'Test Microphone',
            'maxInputChannels': 1
        }
        
        # Create instance with mocked dependencies
        with patch('voice_to_docs.whisper.load_model'), \
             patch('voice_to_docs.Anthropic'), \
             patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            
            voice_to_docs = VoiceToDocs(audio_device=0)
            result = voice_to_docs._validate_audio_device(0)
            
            self.assertEqual(result, 0)

    @patch('voice_to_docs.pyaudio.PyAudio')
    def test_validate_audio_device_invalid(self, mock_pyaudio):
        """Test validation of an invalid audio device"""
        mock_audio = Mock()
        mock_pyaudio.return_value = mock_audio
        mock_audio.get_device_info_by_index.side_effect = OSError("Device not found")
        
        with patch('voice_to_docs.whisper.load_model'), \
             patch('voice_to_docs.Anthropic'), \
             patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            
            voice_to_docs = VoiceToDocs()
            
            with self.assertRaises(ValueError) as context:
                voice_to_docs._validate_audio_device(999)
            
            self.assertIn("Invalid audio device 999", str(context.exception))

    @patch('voice_to_docs.VoiceToDocs.list_audio_devices')
    def test_auto_detect_audio_device_usb_priority(self, mock_list_devices):
        """Test that USB devices are prioritized in auto-detection"""
        mock_list_devices.return_value = [
            {'index': 0, 'name': 'Built-in Microphone'},
            {'index': 1, 'name': 'USB Audio Device'},
            {'index': 2, 'name': 'HyperX SoloCast'}
        ]
        
        with patch('voice_to_docs.whisper.load_model'), \
             patch('voice_to_docs.Anthropic'), \
             patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            
            voice_to_docs = VoiceToDocs()
            result = voice_to_docs._auto_detect_audio_device()
            
            # Should pick HyperX device (index 2) due to keyword matching
            self.assertEqual(result, 2)


class TestVoiceToDocsCore(unittest.TestCase):
    """Test core functionality with mocked dependencies"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_transcript = "Hello, this is a test transcript for processing."
        self.test_processed = "# Test Documentation\n\nThis is processed engineering documentation."

    @patch('voice_to_docs.whisper.load_model')
    @patch('voice_to_docs.Anthropic')
    @patch('voice_to_docs.VoiceToDocs._configure_audio_device')
    def test_initialization(self, mock_config_device, mock_anthropic, mock_whisper):
        """Test VoiceToDocs initialization"""
        mock_config_device.return_value = 0
        mock_whisper.return_value = Mock()
        mock_anthropic.return_value = Mock()
        
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            voice_to_docs = VoiceToDocs()
            
            self.assertIsNotNone(voice_to_docs.client)
            self.assertIsNotNone(voice_to_docs.whisper_model)
            self.assertEqual(voice_to_docs.input_device, 0)

    @patch('voice_to_docs.whisper.load_model')
    @patch('voice_to_docs.Anthropic')
    @patch('voice_to_docs.VoiceToDocs._configure_audio_device')
    def test_process_with_claude(self, mock_config_device, mock_anthropic, mock_whisper):
        """Test Claude API processing"""
        mock_config_device.return_value = 0
        mock_whisper.return_value = Mock()
        
        # Mock Anthropic client
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        
        # Mock API response
        mock_response = Mock()
        mock_response.content = [Mock(text=self.test_processed)]
        mock_client.messages.create.return_value = mock_response
        
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            voice_to_docs = VoiceToDocs()
            result = voice_to_docs.process_with_claude(self.test_transcript)
            
            self.assertEqual(result, self.test_processed)
            mock_client.messages.create.assert_called_once()

    @patch('voice_to_docs.whisper.load_model')
    @patch('voice_to_docs.Anthropic')
    @patch('voice_to_docs.VoiceToDocs._configure_audio_device')
    @patch('voice_to_docs.os.unlink')
    def test_transcribe_audio(self, mock_unlink, mock_config_device, mock_anthropic, mock_whisper):
        """Test audio transcription with Whisper"""
        mock_config_device.return_value = 0
        mock_anthropic.return_value = Mock()
        
        # Mock Whisper model
        mock_model = Mock()
        mock_model.transcribe.return_value = {"text": self.test_transcript}
        mock_whisper.return_value = mock_model
        
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            voice_to_docs = VoiceToDocs()
            
            # Create a temporary file for testing
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_path = temp_file.name
            
            result = voice_to_docs.transcribe_audio(temp_path)
            
            self.assertEqual(result, self.test_transcript)
            mock_model.transcribe.assert_called_once()
            mock_unlink.assert_called_once_with(temp_path)

    def test_initialization_missing_api_key(self):
        """Test that initialization fails without API key"""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as context:
                VoiceToDocs()
            
            self.assertIn("ANTHROPIC_API_KEY", str(context.exception))


class TestEnvironmentConfiguration(unittest.TestCase):
    """Test environment variable configuration"""

    @patch('voice_to_docs.whisper.load_model')
    @patch('voice_to_docs.Anthropic')
    @patch('voice_to_docs.VoiceToDocs._validate_audio_device')
    def test_audio_device_env_var(self, mock_validate, mock_anthropic, mock_whisper):
        """Test audio device configuration via environment variable"""
        mock_validate.return_value = 3
        mock_whisper.return_value = Mock()
        mock_anthropic.return_value = Mock()
        
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key', 'AUDIO_DEVICE': '3'}):
            voice_to_docs = VoiceToDocs()
            
            mock_validate.assert_called_once_with(3)
            self.assertEqual(voice_to_docs.input_device, 3)

    @patch('voice_to_docs.whisper.load_model')
    @patch('voice_to_docs.Anthropic')
    @patch('voice_to_docs.VoiceToDocs._auto_detect_audio_device')
    def test_custom_system_prompt(self, mock_auto_detect, mock_anthropic, mock_whisper):
        """Test custom system prompt via environment variable"""
        mock_auto_detect.return_value = 0
        mock_whisper.return_value = Mock()
        mock_anthropic.return_value = Mock()
        
        custom_prompt = "You are a specialized documentation assistant."
        
        with patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': 'test-key',
            'SYSTEM_PROMPT': custom_prompt
        }):
            voice_to_docs = VoiceToDocs()
            
            self.assertEqual(voice_to_docs.system_prompt, custom_prompt)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)