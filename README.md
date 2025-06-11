# 🎙️ Real-Time Voice Assistant with Deepgram + OpenAI 🧠🔊

A real-time conversational voice assistant using **Deepgram** for speech-to-text 🗣️➡️📝 and **OpenAI GPT-3.5 Turbo** for intelligent responses 📝➡️🧠 — powered by **Python** and **asyncio** for non-blocking performance 🚀.

---

## 📦 Features

✅ Live microphone input and transcription  
✅ Seamless integration with OpenAI's GPT model  
✅ Real-time Text-to-Speech (TTS) responses  
✅ Multi-tasking with `asyncio`  
✅ Modular design for easy maintenance and scaling  

---

## 🧠 LLMHandler: Core Class

> Located in: `llm_handler.py`  
A class for handling interaction with OpenAI's language model.

### Key Methods
- `add_user_message(message)` ➕ Add user input  
- `get_llm_response()` 🧠 Get assistant’s response  
- `clear_history()` 🧽 Reset conversation (keep system prompt)

---

## 🧰 Main App Logic

> Located in: `main.py`  
Handles:
- 🎤 Audio capture using `pyaudio`
- 🌐 WebSocket streaming to Deepgram
- 🧠 LLM interaction and 💬 response
- 🔊 Speaking the assistant's response back

---

## 🛠️ Installation & Setup

1. 🔁 Clone the repo
```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```
🧪 Create a .env File with Your API Keys
```
DEEPGRAM_API_KEY=your_deepgram_key_here
OPENAI_API_KEY=your_openai_key_here
```
🧩 Project Structure
```
📁 your-project/
├── main.py                # Main program for managing audio stream and logic
├── llm_handler.py         # GPT conversation handler class
├── speak.py               # (Assumed) Text-to-speech helper
├── requirements.txt       # Python dependencies
└── .env                   # API keys (not committed)
```
