import pyaudio
import argparse
import asyncio
import json
import os
import sys
import websockets
from dotenv import load_dotenv
from llm_handler import LLMHandler
from speak import AsyncSpeaker, text_to_speech
import aiohttp
load_dotenv()

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 8000

audio_queue = asyncio.Queue()
#Called repeatedly when audio data is available from the microphone
def mic_callback(input_data, frame_count, time_info, status_flag):
    audio_queue.put_nowait(input_data)
    return (input_data, pyaudio.paContinue)

#Manages sending microphone audio data over the WebSocket.
async def sender(ws):
    print("🟢 (2/3) Ready to stream microphone audio to Deepgram. Speak into your microphone to transcribe.")
    try:
        while True:
            mic_data = await audio_queue.get()
            await ws.send(mic_data)
    except websockets.exceptions.ConnectionClosedOK:
        await ws.send(json.dumps({"type": "CloseStream"}))
        print("🟢 (3/3) Successfully closed Deepgram connection")
    except Exception as e:
        print(f"Error while sending: {str(e)}")
        raise

#Handles incoming messages (transcriptions) from Deepgram.
async def receiver(ws):
    first_message = True
    first_transcript = True
    llm = LLMHandler()
    speaker = AsyncSpeaker()
    is_playing_tts = False
    last_transcript = ""  # Add this to track the last transcript
    
    async with aiohttp.ClientSession() as session:
        async for msg in ws:
            if is_playing_tts:  # Skip processing while TTS is playing
                continue
                
            res = json.loads(msg)
            if first_message:
                print("🟢 (3/3) Successfully receiving Deepgram messages, waiting for transcription...")
                first_message = False
            try:
                #is_final is a Built-in Flag from Deepgram
                if res.get("is_final"):
                    transcript = (
                        res.get("channel", {})
                        .get("alternatives", [{}])[0]
                        .get("transcript", "")
                    ).strip()
                    
                    # Prevent processing the same transcript or LLM's generated speech
                    if transcript and transcript != last_transcript:
                        last_transcript = transcript
                        
                        if first_transcript:
                            print("🟢 Transcription started:")
                            first_transcript = False
                        print(f"You: {transcript}")
                        
                        # Send user transcript to LLM
                        llm.add_user_message(transcript)
                        response = llm.get_llm_response()
                        if response:
                            print(f"Assistant: {response}")
                            # Speak the LLM's response
                            is_playing_tts = True  # Set flag before TTS
                            await text_to_speech(response, speaker, session)
                            is_playing_tts = False  # Clear flag after TTS
                        
                        if "stop listening" in transcript.lower():
                            await ws.send(json.dumps({"type": "CloseStream"}))
                            print("🟢 Stopping transcription as requested")
                            speaker.stop()
            except KeyError:
                print(f"🔴 ERROR: Received unexpected API response! {msg}")
            except Exception as e:
                print(f"🔴 Error in receiver: {e}")
                speaker.stop()
                raise

#Captures audio from the microphone continuously
async def microphone():
    #Creates a new PyAudio instance for handling audio streams.
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK,
        stream_callback=mic_callback,
    )

    stream.start_stream()

    while stream.is_active():
        await asyncio.sleep(0.1)

    stream.stop_stream()
    stream.close()

#Sets up and manages the overall connection and execution of streaming tasks.
async def run(key, model=None, tier=None, host="wss://api.deepgram.com"):
    deepgram_url = f'{host}/v1/listen?punctuate=true&encoding=linear16&sample_rate=16000'

    if model:
        deepgram_url += f"&model={model}"

    if tier:
        deepgram_url += f"&tier={tier}"

    async with websockets.connect(
        deepgram_url, extra_headers={"Authorization": f"Token {key}"}
    ) as ws:
        print(f'ℹ️  Request ID: {ws.response_headers.get("dg-request-id")}')
        if model:
            print(f'ℹ️  Model: {model}')
        if tier:
            print(f'ℹ️  Tier: {tier}')
        print("🟢 (1/3) Successfully opened Deepgram streaming connection")
#Runs the three main coroutines concurrently
        await asyncio.gather(
            sender(ws),
            receiver(ws),
            microphone(),
        )

def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract text from microphone audio using Deepgram API"
    )
    parser.add_argument(
        "-m", "--model",
        help="Deepgram model to use (default: general)",
        default="general"
    )
    parser.add_argument(
        "-t", "--tier",
        help="Deepgram tier to use",
        default=""
    )
    parser.add_argument(
        "--host",
        help="Deepgram API host",
        default="wss://api.deepgram.com"
    )
    return parser.parse_args()

#Acts as the entry point of the program
def main():
    args = parse_args()
    
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        print("🔴 ERROR: DEEPGRAM_API_KEY not found in environment variables")
        print("Please create a .env file with your API key: DEEPGRAM_API_KEY=your_api_key_here")
        return 1

    try:
        asyncio.run(run(
            api_key,
            model=args.model,
            tier=args.tier,
            host=args.host
        ))
    except websockets.InvalidHandshake as e:
        print(f'🔴 ERROR: Could not connect to Deepgram! {e.headers.get("dg-error")}')
        print(f'🔴 Please contact Deepgram Support with request ID {e.headers.get("dg-request-id")}')
        return 1
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"🔴 ERROR: Deepgram connection unexpectedly closed with code {e.code} and payload {e.reason}")
        return 1
    except websockets.exceptions.ConnectionClosedOK:
        return 0
    except Exception as e:
        print(f"🔴 ERROR: Something went wrong! {e}")
        return 1
    
#Ensures that main() is only executed when the script is run directly, not when imported as a module.
if __name__ == "__main__":
    sys.exit(main() or 0)