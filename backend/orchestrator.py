import asyncio
from translation_service import AzureTranslatorService
from tts_service import AzureTTSService
import re

class Orchestrator:
    """
    Controls the pipeline: receives audio, runs ASR → translation → TTS,
    and broadcasts TTS audio to all connected clients via the broadcast manager.
    """
    def __init__(self, asr_service, translator_service, tts_service, broadcast_manager):
        self.asr = asr_service
        self.translator = translator_service
        self.tts = tts_service
        self.broadcast = broadcast_manager
        self.buffer = ""

    async def process(self, audio_chunk: bytes):
        print(f"[Orchestrator] Processing audio chunk of size {len(audio_chunk)} bytes")

        async def asr_callback(text):
            print(f"[Orchestrator] ASR recognized: '{text}'")
            if not text:
                print("[Orchestrator] No text recognized from ASR.")
                return

            # 2. Buffer & sentence segmentation
            self.buffer += (" " if self.buffer else "") + text
            sentences = re.split(r'(?<=[.!?]) +', self.buffer)
            complete = [s for s in sentences if re.search(r'[.!?]$', s.strip())]
            last = sentences[-1] if sentences else ""

            for sent in complete:
                sent = sent.strip()
                if not sent:
                    continue

                # 3. Translate
                try:
                    translated = self.translator.translate_text(sent)
                    print(f"[Orchestrator] Translated: '{translated}'")
                except Exception as e:
                    print(f"[Orchestrator] Translation error: {e}")
                    continue

                # 4. TTS
                try:
                    audio_data = self.tts.text_to_speech(translated)
                    print(f"[Orchestrator] TTS audio data size: {len(audio_data) if audio_data else 0} bytes")
                except Exception as e:
                    print(f"[Orchestrator] TTS error: {e}")
                    continue

                if audio_data:
                    # 5. Broadcast to all connected clients
                    asyncio.create_task(self.broadcast.broadcast_audio(audio_data))
                else:
                    print(f"[Orchestrator] No audio generated for: '{sent}'")

            # 6. Retain only the incomplete sentence fragment
            self.buffer = last if not re.search(r'[.!?]$', last.strip()) else ""

    async def process_text(self, text: str):
        print(f"[Orchestrator] ASR recognized: '{text}'")
        if not text:
            print("[Orchestrator] No text recognized from ASR.")
            return

        # 2. Buffer & sentence segmentation
        self.buffer += (" " if self.buffer else "") + text
        sentences = re.split(r'(?<=[.!?]) +', self.buffer)
        complete = [s for s in sentences if re.search(r'[.!?]$', s.strip())]
        last = sentences[-1] if sentences else ""

        for sent in complete:
            sent = sent.strip()
            if not sent:
                continue

            # 3. Translate
            try:
                translated = self.translator.translate_text(sent)
                print(f"[Orchestrator] Translated: '{translated}'")
            except Exception as e:
                print(f"[Orchestrator] Translation error: {e}")
                continue

            # 4. TTS
            try:
                audio_data = self.tts.text_to_speech(translated)
                print(f"[Orchestrator] TTS audio data size: {len(audio_data) if audio_data else 0} bytes")
            except Exception as e:
                print(f"[Orchestrator] TTS error: {e}")
                continue

            if audio_data:
                # 5. Broadcast to all connected clients
                asyncio.create_task(self.broadcast.broadcast_audio(audio_data))
            else:
                print(f"[Orchestrator] No audio generated for: '{sent}'")

        # 6. Retain only the incomplete sentence fragment
        self.buffer = last if not re.search(r'[.!?]$', last.strip()) else ""

    def flush(self):
        """
        Processes any leftover buffered text at end of stream/session.
        """
        remaining = self.buffer.strip()
        print(f"[Orchestrator] Flushing buffer: '{remaining}'")
        if not remaining:
            return
        try:
            translated = self.translator.translate_text(remaining)
            print(f"[Orchestrator] Flushed translation: '{translated}'")
            audio_data = self.tts.text_to_speech(translated)
            print(f"[Orchestrator] Flushed TTS audio data size: {len(audio_data) if audio_data else 0} bytes")
            if audio_data:
                asyncio.create_task(self.broadcast.broadcast_audio(audio_data))
        except Exception as e:
            print(f"[Orchestrator] Flush error: {e}")
        self.buffer = ""
