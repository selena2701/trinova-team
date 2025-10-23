import requests
import base64
from typing import Optional, List, Dict, Any

from .base import BaseService, ServiceConfig

class TTSService(BaseService):
    """
    Text-to-Speech service using Google Gemini TTS API.
    
    Uses the correct endpoint: /gemini/v1beta/models/{model}:generateContent
    with x-goog-api-key authentication as per documentation.
    """
    
    def __init__(self, config: ServiceConfig):
        super().__init__(config)
        self.default_model = "gemini-2.5-flash-preview-tts"

    def synthesize(self, text: str, voice_name: str = "Kore", model: Optional[str] = None) -> bytes:
        """
        Synthesize text to speech using Google Gemini TTS.
        
        Args:
            text: Text to convert to speech
            voice_name: Prebuilt voice name (e.g., "Kore", "Puck")
            model: TTS model to use (defaults to gemini-2.5-flash-preview-tts)
            
        Returns:
            Audio data as bytes
        """
        model = model or self.default_model
        url = f"{self.config.base_url}/gemini/v1beta/models/{model}:generateContent"
        
        payload = {
            "contents": [{
                "parts": [{"text": text}]
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": voice_name
                        }
                    }
                }
            }
        }
        
        try:
            response = requests.post(url, headers=self.google_headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract base64 audio data from response
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates in TTS response")
                
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                raise ValueError("No parts in TTS response")
                
            inline_data = parts[0].get("inlineData", {})
            if not inline_data:
                raise ValueError("No inlineData in TTS response")
                
            base64_data = inline_data.get("data")
            if not base64_data:
                raise ValueError("No base64 data in TTS response")
            
            # Decode base64 audio data
            audio_bytes = base64.b64decode(base64_data)
            return audio_bytes
            
        except requests.exceptions.RequestException as e:
            raise requests.HTTPError(f"TTS API request failed: {e}")
        except (KeyError, ValueError) as e:
            raise ValueError(f"TTS response parsing failed: {e}")

    def synthesize_multi_speaker(self, text: str, speakers: List[Dict[str, str]], model: Optional[str] = None) -> bytes:
        """
        Synthesize text with multiple speakers.
        
        Args:
            text: Text with speaker markers (e.g., "Speaker1: Hello. Speaker2: Hi there!")
            speakers: List of speaker configs [{"speaker": "Speaker1", "voice": "Kore"}, ...]
            model: TTS model to use
            
        Returns:
            Audio data as bytes
        """
        model = model or self.default_model
        url = f"{self.config.base_url}/gemini/v1beta/models/{model}:generateContent"
        
        speaker_configs = []
        for speaker in speakers:
            speaker_configs.append({
                "speaker": speaker["speaker"],
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": speaker["voice"]
                    }
                }
            })
        
        payload = {
            "contents": [{
                "parts": [{"text": text}]
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "multiSpeakerVoiceConfig": {
                        "speakerVoiceConfigs": speaker_configs
                    }
                }
            }
        }
        
        try:
            response = requests.post(url, headers=self.google_headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract base64 audio data (same as single speaker)
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates in multi-speaker TTS response")
                
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                raise ValueError("No parts in multi-speaker TTS response")
                
            inline_data = parts[0].get("inlineData", {})
            if not inline_data:
                raise ValueError("No inlineData in multi-speaker TTS response")
                
            base64_data = inline_data.get("data")
            if not base64_data:
                raise ValueError("No base64 data in multi-speaker TTS response")
            
            # Decode base64 audio data
            audio_bytes = base64.b64decode(base64_data)
            return audio_bytes
            
        except requests.exceptions.RequestException as e:
            raise requests.HTTPError(f"Multi-speaker TTS API request failed: {e}")
        except (KeyError, ValueError) as e:
            raise ValueError(f"Multi-speaker TTS response parsing failed: {e}")


