"""
azure_auth.py
Reusable AzureAuth class for authentication with Azure services.

Hardcoded credentials for development/testing:
    Replace the values below with your Azure Speech service subscription key and region.
"""

import os
import azure.cognitiveservices.speech as speechsdk

class AzureAuth:
    """
    Centralizes Azure authentication for Speech, Translator, and TTS services in the pipeline.
    """
    def __init__(self):
        """
        Initialize with Azure Speech credentials for use by downstream services.
        """
        # TODO: Replace with your actual Azure Speech key and region
        self.speech_key = os.getenv('AZURE_SPEECH_KEY') # ask for key from hsg tech team 
        self.speech_region = "centralindia"
        if not self.speech_key or not self.speech_region:
            raise ValueError("Azure Speech credentials not set in AzureAuth class.")

    def get_speech_config(self):
        """
        Return a configured Azure SpeechConfig object for use in ASR and TTS.
        """
        config = speechsdk.SpeechConfig(subscription=self.speech_key, region=self.speech_region)
        config.speech_recognition_language = "en-US"
        return config 