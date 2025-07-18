import azure.cognitiveservices.speech as speechsdk
from azure_auth import AzureAuth
from azure.cognitiveservices.speech import CancellationDetails
import asyncio

class AzureASRService:
    """
    Handles real-time speech recognition using Azure Speech SDK.
    Provides methods to create a persistent recognizer and push stream for streaming audio.
    """

    def __init__(self, azure_auth: AzureAuth, language: str = "en-US"):
        self.speech_key = azure_auth.speech_key
        self.region = azure_auth.speech_region
        self.language = language

    def create_streaming_recognizer(self, on_recognized):
        """
        Creates a persistent push stream and recognizer for streaming audio.
        Registers the provided callback for recognized text.
        Returns (push_stream, recognizer).
        """
        speech_config = speechsdk.SpeechConfig(subscription=self.speech_key, region=self.region)
        push_stream = speechsdk.audio.PushAudioInputStream()
        audio_input = speechsdk.AudioConfig(stream=push_stream)
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input, language=self.language)

        def recognized_handler(evt):
            text = getattr(evt.result, 'text', '')
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech and text:
                on_recognized(text)
            elif evt.result.reason == speechsdk.ResultReason.Canceled:
                print("Speech Recognition canceled: {}".format(evt.result.cancellation_details.reason))
                print("Error details: {}".format(evt.result.cancellation_details.error_details))
            elif evt.result.reason != speechsdk.ResultReason.NoMatch:
                print("Speech Recognition failed: {}".format(evt.result.reason))

        recognizer.recognized.connect(recognized_handler)
        return push_stream, recognizer
