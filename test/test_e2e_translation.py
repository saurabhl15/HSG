import asyncio
import websockets
import sounddevice as sd
import numpy as np
import wave
import io

INPUT_WS_URL = "ws://localhost:8000/ws/audio-in"
OUTPUT_WS_URL = "ws://localhost:8000/ws/audio-out"
AUDIO_FILE = "test/test_audio_5m.wav"
CHUNK_SIZE = 4096  # Adjust as needed

# Set these to match your TTS output!
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16 bits (2 bytes per sample)

IDLE_TIMEOUT = 15  # seconds

async def stream_audio_file(input_ws_url, audio_path):
    async with websockets.connect(input_ws_url, max_size=None) as ws:
        with open(audio_path, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                await ws.send(chunk)
                await asyncio.sleep(0.02)
        await ws.close()

async def receive_audio_output(output_ws_url, wav_save_path="output_audio.wav"):
    # Prepare to save output
    wav_file = wave.open(wav_save_path, 'wb')
    wav_file.setnchannels(CHANNELS)
    wav_file.setsampwidth(SAMPLE_WIDTH)
    wav_file.setframerate(SAMPLE_RATE)
    print(f"Connected to output stream. Saving and playing output to: {wav_save_path}")
    async with websockets.connect(output_ws_url, max_size=None) as ws:
        try:
            while True:
                try:
                    audio_chunk = await asyncio.wait_for(ws.recv(), timeout=IDLE_TIMEOUT)
                except asyncio.TimeoutError:
                    print(f"No audio received for {IDLE_TIMEOUT} seconds. Assuming end of stream.")
                    break
                if isinstance(audio_chunk, bytes):
                    # Play live audio (PCM 16-bit)
                    np_audio = np.frombuffer(audio_chunk, dtype=np.int16)
                    sd.play(np_audio, samplerate=SAMPLE_RATE, blocking=False)
                    # Save to WAV file
                    wav_file.writeframes(audio_chunk)
                    print(f"Received and played audio chunk of {len(audio_chunk)} bytes")
        except websockets.exceptions.ConnectionClosed:
            print("Output websocket closed.")
        finally:
            wav_file.close()
            print("WAV file closed.")

async def main():
    # Start both coroutines concurrently
    stream_task = asyncio.create_task(stream_audio_file(INPUT_WS_URL, AUDIO_FILE))
    receive_task = asyncio.create_task(receive_audio_output(OUTPUT_WS_URL))
    await asyncio.gather(stream_task, receive_task)

if __name__ == "__main__":
    asyncio.run(main())
