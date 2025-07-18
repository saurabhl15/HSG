"""
tts.py
Converts translated text to audio using Azure Neural TTS with connection optimization.
"""

import azure.cognitiveservices.speech as speechsdk
from azure_auth import AzureAuth
import io
import time

class AzureTTSService:
    """
    Converts translated text to audio using Azure Neural TTS, optimizing for low-latency, persistent connections.
    """
    def __init__(self):
        """
        Initialize the TTS service, configure Azure credentials, and warm up the synthesizer connection.
        """
        self.auth = AzureAuth()
        self.speech_config = self.auth.get_speech_config()
        
        # Use the original neural voice
        self.speech_config.speech_synthesis_voice_name = "hi-IN-MadhurNeural"
        
        # Optimize for streaming and long-lived connections
        self.speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Raw16Khz16BitMonoPcm
        )
        
        print(f"[TTS] Initialized with voice: {self.speech_config.speech_synthesis_voice_name}")
        
        # Create a persistent synthesizer instance
        self.synthesizer = None
        self._warm_up_connection()
    
    def _warm_up_connection(self):
        """
        Establish and warm up the TTS connection to minimize cold-start latency for future synthesis requests.
        """
        try:
            print("[TTS] Warming up connection...")
            warmup_start = time.time()
            
            # Create synthesizer instance
            self.synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config)
            
            # Send a very short warm-up request
            warmup_text = "नमस्ते"
            result = self.synthesizer.speak_text_async(warmup_text).get()
            
            warmup_time = time.time() - warmup_start
            print(f"[TTS] Warm-up completed in {warmup_time:.3f}s")
            
            if result and result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                print("[TTS] Connection warmed up successfully")
            else:
                print(f"[TTS] Warm-up failed: {result.reason if result else 'None'}")
                # Recreate synthesizer if warm-up failed
                self.synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config)
                
        except Exception as e:
            print(f"[TTS] Warm-up error: {e}")
            # Ensure synthesizer is created even if warm-up fails
            self.synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config)

    def text_to_speech(self, text: str) -> bytes:
        """
        Synthesize the given text to audio bytes using a persistent TTS connection.
        """
        try:
            print(f"[TTS] Starting synthesis for text: '{text[:50]}...'")
            tts_start = time.time()
            
            # Use the persistent synthesizer instance
            if not self.synthesizer:
                print("[TTS] Recreating synthesizer...")
                self.synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config)
            
            # Synthesize text to speech using the persistent connection
            result = self.synthesizer.speak_text_async(text).get()
            
            tts_time = time.time() - tts_start
            
            if result is None:
                print("[TTS] Synthesis returned None")
                return b""

            print(f"[TTS] Synthesis completed in {tts_time:.3f}s, result reason: {result.reason}")
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                # Get audio data
                audio_data = result.audio_data
                total_time = time.time() - tts_start
                print(f"[TTS] Successfully generated {len(audio_data)} bytes in {total_time:.3f}s")
                return audio_data
            else:
                print(f"[TTS] Synthesis failed: {result.reason}")
                if hasattr(result, 'error_details'):
                    print(f"[TTS] Error details: {result.error_details}")
                
                # If synthesis failed, try recreating the synthesizer
                print("[TTS] Attempting to recreate synthesizer...")
                self.synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config)
                return b""
        except Exception as e:
            print(f"[TTS] Exception during synthesis: {e}")
            # Recreate synthesizer on exception
            self.synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config)
            return b""

    def synthesize_to_stream(self, text: str, audio_stream):
        """
        Synthesize text to audio and write the result to a provided stream object.
        """
        audio_data = self.text_to_speech(text)
        if audio_data:
            audio_stream.write(audio_data)
    
    def close(self):
        """
        Release the TTS synthesizer connection and clean up resources.
        """
        if self.synthesizer:
            self.synthesizer = None
            print("[TTS] Connection closed")

