import asyncio
from fastapi import FastAPI, WebSocket
from asr_service import AzureASRService
from translation_service import AzureTranslatorService
from tts_service import AzureTTSService
from broadcast_manager import BroadcastManager
from orchestrator import Orchestrator
from azure_auth import AzureAuth

app = FastAPI()

# --- Initialize pipeline dependencies at startup ---
azure_auth = AzureAuth()
asr_service = AzureASRService(azure_auth)
translator_service = AzureTranslatorService()
tts_service = AzureTTSService()
broadcast_manager = BroadcastManager()

orchestrator = Orchestrator(
    asr_service=asr_service,
    translator_service=translator_service,
    tts_service=tts_service,
    broadcast_manager=broadcast_manager
)

@app.websocket("/ws/audio-in")
async def websocket_audio_in(websocket: WebSocket):
    """
    Accepts incoming audio chunks and pushes them into the orchestrator.
    No response is sent back; output is broadcast to connected listeners.
    """
    await websocket.accept()
    loop = asyncio.get_event_loop()
    done = asyncio.Event()

    def on_recognized(text):
        # Schedule orchestrator.process_text on the event loop
        loop.create_task(orchestrator.process_text(text))

    push_stream, recognizer = asr_service.create_streaming_recognizer(on_recognized)
    recognizer.start_continuous_recognition()

    try:
        while True:
            audio_chunk = await websocket.receive_bytes()
            push_stream.write(audio_chunk)
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
    finally:
        push_stream.close()
        recognizer.stop_continuous_recognition()
        # Only flush if there is leftover buffer
        if orchestrator.buffer.strip():
            await asyncio.to_thread(orchestrator.flush)

@app.websocket("/ws/audio-out")
async def websocket_audio_out(websocket: WebSocket):
    await websocket.accept()
    queue = await broadcast_manager.register(websocket)
    try:
        while True:
            audio_bytes = await queue.get()
            await websocket.send_bytes(audio_bytes)
    except Exception as e:
        print(f"[audio-out] Client disconnected: {e}")
    finally:
        await broadcast_manager.unregister(websocket)


