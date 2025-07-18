import asyncio

class BroadcastManager:
    def __init__(self):
        self.clients = set()  # Set of (websocket, queue) pairs
        self._lock = asyncio.Lock()

    async def register(self, websocket):
        queue = asyncio.Queue()
        async with self._lock:
            self.clients.add((websocket, queue))
        return queue

    async def unregister(self, websocket):
        async with self._lock:
            self.clients = { (ws, q) for (ws, q) in self.clients if ws != websocket }

    async def broadcast_audio(self, audio_bytes: bytes):
        async with self._lock:
            for ws, queue in self.clients:
                # Queue audio for each client
                try:
                    queue.put_nowait(audio_bytes)
                except Exception:
                    pass  # Optionally handle full queues
