# Liquid Audio - Pinokio

A Gradio interface for [Liquid AI's LFM2.5-Audio-1.5B](https://huggingface.co/LiquidAI/LFM2.5-Audio-1.5B), with speech-to-speech chat, automatic speech recognition (ASR), and text-to-speech (TTS).

## Requirements

- Python 3.12; the Pinokio installer creates `app/env`.
- PyTorch and torchaudio 2.8.0, Liquid Audio 1.3.0, and Gradio 5.50 (below 6).
- A CUDA-capable NVIDIA GPU on Windows/Linux, or a compatible ROCm GPU on Linux. The launcher selects CUDA 12.8 or ROCm 6.4 wheels respectively; compatible drivers are required.
- CPU, Apple MPS, Intel Macs, and Windows DirectML are not supported for inference. The upstream LFM2.5 audio decoder explicitly uses CUDA (also exposed by ROCm). CPU wheels allow development and UI tests; they do not enable audio inference.
- Internet access for installation and the first model download. Model weights are downloaded lazily from Hugging Face.

## Installation

### Pinokio

1. Click **Install**.
2. Click **Start**, then **Open Web UI**.
3. Submit a request to load the model. The first request includes the model download.

**Update** pulls repository changes with `git pull --ff-only` and reruns installation. Local divergent commits must be reconciled before updating. **Reset** removes `app/env`; **Save Disk Space** deduplicates that environment. Stop the app before maintenance.

If upgrading from an older launcher, rerun **Install**. Older versions could create an unused `env` directory in the repository root as well as `app/env`. Reset now targets `app/env`; the legacy directory is left intact.

### Manual installation

Create and activate a Python 3.12 virtual environment, then run these commands from `app`:

```bash
# NVIDIA on Windows or Linux:
python -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128

# For supported AMD hardware on Linux, use this command instead:
# python -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/rocm6.4

python -m pip install -r requirements.txt
python -m pip check
python app.py
```

Open the local URL printed by Gradio. It normally starts at port 7860 and chooses another port if that one is occupied. The server binds to `127.0.0.1`.

## Usage

- **Speech-to-Speech Chat:** upload or record audio, enter text, or provide both. Optionally change the system prompt, then click **Send**. The default prompt is `Respond with interleaved text and audio.`
- **Automatic Speech Recognition:** upload or record audio and click **Transcribe**.
- **Text-to-Speech:** enter text, select US Male, US Female, UK Male, or UK Female, and click **Synthesize**.
- **New conversation:** clears chat history and responses for the current session.

Chat history is session-local and retains the most recent 10 exchanges (20 user/assistant turns). Uploaded audio is retained in memory for those turns; assistant responses retain their generated tokens and modality order. Reloading the page starts a new session. All inference endpoints share one queue to avoid simultaneous access to the model.

Audio uploads are converted to mono. Generated audio is 24 kHz. Gradio manages output files and checks hourly for cached files older than an hour; downloads should be saved if needed later. Generation is limited to 512 tokens, so long responses may be truncated.

## Programmatic access

Use the URL printed at startup in place of the example below. Gradio manages chat history on the server; **do not pass `chat_history` as an API argument**. Reuse a client instance to keep its conversation and call `/reset_chat` to clear it.

### Python

Install `gradio_client`, then:

```python
from gradio_client import Client, handle_file

client = Client("http://127.0.0.1:7860/")

text, audio = client.predict(
    audio_input=None,  # or handle_file("input.wav")
    text_input="Hello, how are you?",
    system_prompt="Respond with interleaved text and audio.",
    api_name="/speech_to_speech_chat",
)

transcription = client.predict(
    audio_input=handle_file("speech.wav"),
    api_name="/asr_transcription",
)

audio = client.predict(
    text_input="Hello world",
    voice_selection="US Female",
    api_name="/tts_synthesis",
)
client.predict(api_name="/reset_chat")
client.close()
```

### JavaScript

Install `@gradio/client` and use the official client to handle the queued API:

```javascript
import { Client } from "@gradio/client";

const client = await Client.connect("http://127.0.0.1:7860/");
const result = await client.predict("/speech_to_speech_chat", {
  audio_input: null,
  text_input: "Hello!",
  system_prompt: "Respond with interleaved text and audio."
});
console.log(result.data);
await client.predict("/reset_chat", {});
```

### curl

The Gradio 5 API uses a submission followed by a server-sent event stream. This Bash example synthesizes speech:

```bash
curl -X POST 'http://127.0.0.1:7860/gradio_api/call/tts_synthesis' \
  -H 'Content-Type: application/json' \
  -d '{"data": ["Hello world", "US Female"]}'
```

The response contains `{"event_id":"..."}`. Replace `EVENT_ID` with that value:

```bash
curl -N 'http://127.0.0.1:7860/gradio_api/call/tts_synthesis/EVENT_ID'
```

Read the `complete` event for the result, or the `error` event on failure. For audio uploads and stateful conversations, the official clients handle file upload and session identifiers. The running UI's **Use via API** page provides endpoint-specific examples.

## Development checks

From the repository root, with app dependencies installed:

```bash
node --test tests/launcher.test.js
python -m unittest discover -s tests -p 'test_*.py' -v
```

The tests use real PyTorch tensors, Liquid Audio chat state, and a live local Gradio server with simulated model outputs. They do not download weights or verify GPU inference or audio quality. The HTTP test starts and closes a loopback server automatically.

## Model and license

The model and upstream Liquid Audio code use the [LFM Open License v1.0](https://github.com/Liquid4All/liquid-audio/blob/main/LICENSE). Consult the upstream license and model repository for their terms; this repository does not contain a separate launcher license file.

References: [Liquid Audio source and usage](https://github.com/Liquid4All/liquid-audio), [model card](https://huggingface.co/LiquidAI/LFM2.5-Audio-1.5B), [PyTorch platform wheels](https://pytorch.org/get-started/previous-versions/).
