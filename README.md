# Liquid Audio - Pinokio

🎙️ **Liquid Audio - LFM2.5-Audio-1.5B** - A Gradio web interface for Liquid AI's multimodal audio model, packaged for Pinokio.

## Overview

Liquid Audio is an advanced multimodal audio model that seamlessly handles multiple tasks:
- **Speech-to-Speech Chat**: Engage in multi-turn conversations with both text and audio input/output
- **Automatic Speech Recognition (ASR)**: Convert speech to text with high accuracy
- **Text-to-Speech (TTS)**: Generate natural-sounding speech with multiple voice options

The LFM2.5-Audio-1.5B model supports interleaved text and audio generation, enabling rich, natural conversations.

## Features

- 🎙️ **Speech-to-Speech Chat**: Multi-turn conversations with audio and text
- 📝 **Automatic Speech Recognition**: Accurate speech-to-text transcription
- 🔊 **Text-to-Speech**: Multiple voice options (US/UK, Male/Female)
- 🔄 **Interleaved Output**: Generate combined text and audio responses
- 💬 **Customizable System Prompts**: Control response behavior
- 🎚️ **Voice Selection**: Choose from multiple voice profiles
- 🖥️ **Web Interface**: User-friendly Gradio interface accessible via browser
- 💾 **Chat History**: Preserve conversation context across turns

## Installation

### Using Pinokio

1. **Install** the app through Pinokio
2. Click **"Start"** to launch the Gradio interface
3. Open the web UI from the Pinokio interface

### Manual Installation

1. **Clone or download this repository**

2. **Install dependencies** (from the `app` folder):
```bash
cd app
pip install -r requirements.txt
```

3. **Run the interface**:
```bash
python app.py
```
(Still inside the `app` directory.)

4. **Access the interface**:
Open your browser and navigate to `http://localhost:7860`

## Usage

### Speech-to-Speech Chat

1. Upload audio or record a message using your microphone
2. Optionally add text input alongside audio
3. (Optional) Customize the system prompt for specific behaviors
4. Click **"Send"** to get a response with both text and audio
5. Continue the conversation - your chat history is preserved

**Example system prompts:**
- `Respond with interleaved text and audio.` (default)
- `Respond only with audio.`
- `Respond only with text.`

### Automatic Speech Recognition (ASR)

1. Upload an audio file or record speech using your microphone
2. Click **"Transcribe"**
3. View the transcribed text

### Text-to-Speech (TTS)

1. Enter text in the input field
2. Select a voice:
   - **US Male** / **US Female**
   - **UK Male** / **UK Female**
3. Click **"Synthesize"**
4. Listen to the generated audio

## Model Information

- **Model**: LFM2.5-Audio-1.5B
- **Provider**: Liquid AI
- **Repository**: [Hugging Face - LiquidAI/LFM2.5-Audio-1.5B](https://huggingface.co/LiquidAI/LFM2.5-Audio-1.5B)
- **License**: LFM Open License v1.0

## Technical Details

### Audio Processing
- **Sample Rate**: 24,000 Hz
- **Audio Format**: WAV
- **Generation Parameters**:
  - Text temperature: 1.0 (default)
  - Audio temperature: 1.0 (speech-to-speech), 0.8 (TTS)
  - Max tokens: 512
  - Audio top-k: 4 (speech-to-speech), 64 (TTS)

### Architecture
The interface uses Gradio with PyTorch and torchaudio to load and run the LFM2.5-Audio-1.5B model. The model automatically downloads from Hugging Face on first use.

## Requirements

- Python 3.12
- PyTorch 2.7+ (installed automatically by Pinokio based on your GPU)
- CUDA-capable GPU (recommended for faster inference)
- torchaudio
- Gradio 5.50+
- liquid-audio library

## Pinokio Commands

- **Install**: Sets up the Python environment and installs dependencies
- **Start**: Launches the Gradio web interface
- **Update**: Updates the repository
- **Reset**: Removes the virtual environment
- **Save Disk Space**: Deduplicates redundant library files

## Programmatic Access (API)

The Gradio interface exposes the core functions via its built-in API. You can call them programmatically from Python, JavaScript, or curl.

### 1. Python (using `gradio_client`)

```bash
pip install gradio_client
```

```python
from gradio_client import Client, handle_file

client = Client("http://127.0.0.1:7860/")

# Speech-to-Speech Chat
result = client.predict(
    audio_input=handle_file("input.wav"),   # or None
    text_input="Hello, how are you?",
    chat_history=[],
    system_prompt="Respond with interleaved text and audio.",
    api_name="/speech_to_speech_chat"       # or check the API tab in the UI
)
print(result)

# Automatic Speech Recognition (ASR)
transcription = client.predict(
    audio_input=handle_file("speech.wav"),
    api_name="/asr_transcription"
)
print(transcription)

# Text-to-Speech (TTS)
audio = client.predict(
    text_input="Hello world",
    voice_selection="US Female",
    api_name="/tts_synthesis"
)
print(audio)
```

### 2. JavaScript (fetch)

```js
const response = await fetch("http://127.0.0.1:7860/api/predict", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    fn_index: 0,           // Check the API docs in the running UI for correct indices
    data: [null, "Hello", [], "Respond with interleaved text and audio."]
  })
});
const result = await response.json();
console.log(result);
```

### 3. Curl

```bash
curl -X POST "http://127.0.0.1:7860/api/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "fn_index": 0,
    "data": [null, "Hello there", [], "Respond with interleaved text and audio."]
  }'
```

**Tip:** When the app is running, click the **"Use via API"** button in the bottom of the Gradio interface for the exact current `fn_index` values and full OpenAPI-style documentation.

## Notes

- First model load may take longer as the weights are downloaded from Hugging Face
- GPU is strongly recommended for real-time performance
- The model supports multi-turn conversations with full history preservation
- Audio files are temporarily stored during processing and cleaned up afterward

## License

This project is licensed under the LFM Open License v1.0. See the original model license for more details.

## References

- [Liquid AI on Hugging Face](https://huggingface.co/LiquidAI)
- [LFM2.5-Audio-1.5B Model](https://huggingface.co/LiquidAI/LFM2.5-Audio-1.5B)

## Contact

For questions about the Liquid Audio model, visit the Liquid AI Hugging Face repository.
