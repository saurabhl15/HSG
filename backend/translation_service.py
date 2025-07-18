"""
translation.py
Translates English text to target languages using Azure Translator API.
"""

import os
import requests
import uuid
import re
from typing import List, Callable
from azure_auth import AzureAuth
import time

class AzureTranslatorService:
    """
    Provides sentence segmentation and real-time translation from English to target languages using Azure Translator API.
    """
    def __init__(self):
        """
        Initialize the translator with Azure credentials and API configuration.
        """
        # You may want to add these to AzureAuth or a config file
        self.key = os.getenv('AZURE_TRANSLATION_KEY') # ask for key from hsg tech team 
        self.endpoint = "https://api.cognitive.microsofttranslator.com"
        self.location = "centralindia"  # or your Azure region
        self.path = '/translate'
        self.url = self.endpoint + self.path
        self.params = {
            'api-version': '3.0',
            'from': 'en',
            'to': ['hi']
        }
        self.headers = {
            'Ocp-Apim-Subscription-Key': self.key,
            'Ocp-Apim-Subscription-Region': self.location,
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }
        print(f"[TRANSLATOR] Initialized with endpoint: {self.endpoint}")

    def chunk_text(self, text: str) -> List[str]:
        """
        Split input text into sentences for chunked, real-time translation.
        """
        # Simple sentence splitter (can be improved)
        sentences = re.split(r'(?<=[.!?]) +', text)
        return [s for s in sentences if s.strip()]

    def translate_text(self, text: str) -> str:
        """
        Translate a single sentence from English to Hindi using Azure Translator API.
        """
        try:
            print(f"[TRANSLATOR] Starting translation for: '{text}'")
            api_start = time.time()
            
            body = [{ 'text': text }]
            response = requests.post(self.url, params=self.params, headers=self.headers, json=body)
            
            api_time = time.time() - api_start
            print(f"[TRANSLATOR] API call took {api_time:.3f}s, status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[TRANSLATOR] API error: {response.text}")
                return ""
                
            result = response.json()
            print(f"[TRANSLATOR] API response: {result}")
            
            translated_text = result[0]['translations'][0]['text']
            total_time = time.time() - api_start
            print(f"[TRANSLATOR] Total translation time: {total_time:.3f}s -> '{translated_text}'")
            return translated_text
        except Exception as e:
            print(f"[TRANSLATOR] Exception during translation: {e}")
            return ""

    def translate_stream(self, text_stream: List[str], on_translation: Callable[[str, str], None]):
        """
        Translate a stream of text chunks, invoking a callback for each original and translated pair.
        """
        for text in text_stream:
            if text.strip():
                translated = self.translate_text(text)
                on_translation(text, translated)

