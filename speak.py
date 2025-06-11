import pyaudio
import numpy as np
import asyncio
import aiohttp
import os
import json
class AsyncSpeaker:
    def __init__(self, rate=48000, chunk_size=8000, channels=1, output_device_index=None):
        self._audio = pyaudio.PyAudio()
        self._chunk = chunk_size
        self._rate = rate
        self._format = pyaudio.paInt16
        self._channels = channels
        self._output_device_index = output_device_index
        self._stream = None
        self._audio_queue = asyncio.Queue(maxsize=100)
        self._is_playing = False
        self._stop_event = asyncio.Event()

    def start(self) -> bool:
        try:
            self._stream = self._audio.open(
                format=self._format,
                channels=self._channels,
                rate=self._rate,
                input=False,
                output=True,
                frames_per_buffer=self._chunk,
                output_device_index=self._output_device_index,
            )
            self._is_playing = True
            self._stop_event.clear()
            return True
        except Exception as e:
            print(f"Error opening audio stream: {e}")
            return False

    def stop(self):
        self._is_playing = False
        self._stop_event.set()
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception as e:
                print(f"Error closing audio stream: {e}")
            finally:
                self._stream = None
        
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
                self._audio_queue.task_done()
            except asyncio.QueueEmpty:
                break

    async def play(self, data):
        try:
            await asyncio.wait_for(self._audio_queue.put(data), timeout=0.5)
        except asyncio.QueueFull:
            print("Audio queue is full. Dropping audio chunk.")
        except Exception as e:
            print(f"Error adding audio to queue: {e}")

    async def _play_audio(self):
        buffer = np.array([], dtype=np.int16)
        
        while self._is_playing and not self._stop_event.is_set():
            try:
                if len(buffer) < self._chunk:
                    try:
                        new_data = await asyncio.wait_for(
                            self._audio_queue.get(), 
                            timeout=0.1
                        )
                        buffer = np.concatenate([buffer, new_data])
                        self._audio_queue.task_done()
                    except asyncio.TimeoutError:
                        if len(buffer) == 0:
                            buffer = np.zeros(self._chunk, dtype=np.int16)
                
                if len(buffer) >= self._chunk:
                    chunk_to_play = buffer[:self._chunk]
                    self._stream.write(chunk_to_play.tobytes())
                    buffer = buffer[self._chunk:]
                
                if not self._is_playing or self._stop_event.is_set():
                    break
            
            except Exception as e:
                print(f"Audio playback error: {e}")
                break

        print("Audio playback stopped.")
        self.stop()


async def text_to_speech(text: str, speaker: AsyncSpeaker, session):
    url = f"wss://api.deepgram.com/v1/speak?encoding=linear16&sample_rate=48000&model=aura-asteria-en"
    headers = {
        "Authorization": f"Token {os.getenv('DEEPGRAM_API_KEY')}",
    }
    
    async with session.ws_connect(url, headers=headers) as ws:
        print("Starting text-to-speech...")
        
        async def send_text():
            words_per_chunk = 8
            words = text.split()
            for i in range(0, len(words), words_per_chunk):
                chunk = " ".join(words[i:i + words_per_chunk])
                await ws.send_str(json.dumps({"type": "Speak", "text": chunk}))
                await asyncio.sleep(0.2)
            await ws.send_str(json.dumps({"type": "Flush"}))
            await ws.send_str(json.dumps({"type": "CloseStream"}))

        async def receive_audio():
            if not speaker.start():
                print("Failed to start audio speaker.")
                return

            audio_player = asyncio.create_task(speaker._play_audio())
            try:
                while True:
                    message = await ws.receive(timeout=10)
                    if message.type == aiohttp.WSMsgType.BINARY:
                        audio_data = np.frombuffer(message.data, dtype=np.int16)
                        await speaker.play(audio_data)
                    elif message.type == aiohttp.WSMsgType.CLOSE:
                        break
            except Exception as e:
                print(f"Error receiving audio: {e}")
            finally:
                await asyncio.sleep(3)  # Let remaining audio play
                speaker.stop()

        await asyncio.gather(send_text(), receive_audio())