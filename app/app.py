import threading

import gradio as gr
import numpy as np
import soundfile as sf
import torch
from liquid_audio import ChatState, LFM2AudioModel, LFM2AudioProcessor, LFMModality

MODEL_REPO = "LiquidAI/LFM2.5-Audio-1.5B"
SAMPLE_RATE = 24_000
MAX_HISTORY_TURNS = 20
model = None
processor = None
# The processor lazily initializes its decoder; serialize all model operations.
model_lock = threading.RLock()


def load_models():
    """Publish the model pair only after both components load successfully."""
    global model, processor
    with model_lock:
        if model is None or processor is None:
            if not torch.cuda.is_available():
                raise gr.Error(
                    "Liquid Audio's decoder requires a CUDA or ROCm GPU. CPU and MPS are not supported."
                )
            dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float32
            new_processor = LFM2AudioProcessor.from_pretrained(
                MODEL_REPO, device="cuda"
            ).eval()
            new_model = LFM2AudioModel.from_pretrained(
                MODEL_REPO, device="cuda", dtype=dtype
            ).eval()
            model, processor = new_model, new_processor
        return model, processor


def read_audio(filename):
    """Read uploads as mono float32; ChatState rejects stereo inputs."""
    samples, sample_rate = sf.read(filename, dtype="float32", always_2d=True)
    if not samples.size:
        raise gr.Error("The audio file is empty.")
    return torch.from_numpy(samples.mean(axis=1)).unsqueeze(0), sample_rate


def decode_audio(processor, tokens):
    """Remove end markers without dropping a valid frame at the token limit."""
    frames = [token for token in tokens if token[0].item() != 2048]
    if not frames:
        return None
    with torch.inference_mode():
        waveform = processor.decode(torch.stack(frames, 1).unsqueeze(0))
    samples = waveform.detach().float().cpu().numpy().reshape(-1)
    return SAMPLE_RATE, np.clip(samples, -1.0, 1.0)


def new_chat(model, processor, system_prompt):
    chat = ChatState(processor, dtype=next(model.parameters()).dtype)
    chat.new_turn("system")
    chat.add_text(system_prompt)
    chat.end_turn()
    return chat


def speech_to_speech_chat(audio_input, text_input, chat_history, system_prompt):
    """Replay assistant output tokens, preserving their original modalities."""
    text_input = (text_input or "").strip()
    if audio_input is None and not text_input:
        raise gr.Error("Upload audio or enter a message.")
    history = list(chat_history or [])
    with model_lock:
        model, processor = load_models()
        chat = new_chat(
            model,
            processor,
            system_prompt or "Respond with interleaved text and audio.",
        )
        for turn in history:
            chat.new_turn(turn["role"])
            if turn["role"] == "assistant":
                chat.append(**turn["tokens"])
            else:
                if turn["audio"] is not None:
                    chat.add_audio(*turn["audio"])
                if turn["text"]:
                    chat.add_text(turn["text"])
            chat.end_turn()

        audio = read_audio(audio_input) if audio_input is not None else None
        chat.new_turn("user")
        if audio is not None:
            chat.add_audio(*audio)
        if text_input:
            chat.add_text(text_input)
        chat.end_turn()
        chat.new_turn("assistant")
        text_tokens, audio_tokens, modalities = [], [], []
        full_text = ""
        for token in model.generate_interleaved(
            **chat, max_new_tokens=512, audio_temperature=1.0, audio_top_k=4
        ):
            if token.numel() == 1:
                text_tokens.append(token)
                modalities.append(LFMModality.TEXT)
                full_text = processor.text.decode(
                    torch.cat(text_tokens), skip_special_tokens=True
                )
                yield full_text, None, history
            else:
                audio_tokens.append(token)
                modalities.append(LFMModality.AUDIO_OUT)
        audio_result = decode_audio(processor, audio_tokens)
        tokens = {
            "text": torch.stack(text_tokens, 1).cpu()
            if text_tokens
            else torch.empty((1, 0), dtype=torch.long),
            "audio_out": torch.stack(audio_tokens, 1).cpu()
            if audio_tokens
            else torch.empty((8, 0), dtype=torch.long),
            "modality_flag": torch.tensor(modalities, dtype=torch.long),
        }
        history += [
            {"role": "user", "audio": audio, "text": text_input},
            {"role": "assistant", "tokens": tokens},
        ]
        yield full_text, audio_result, history[-MAX_HISTORY_TURNS:]


def asr_transcription(audio_input):
    """Transcribe an uploaded recording."""
    if audio_input is None:
        raise gr.Error("Upload or record audio to transcribe.")
    with model_lock:
        model, processor = load_models()
        chat = new_chat(model, processor, "Perform ASR.")
        chat.new_turn("user")
        chat.add_audio(*read_audio(audio_input))
        chat.end_turn()
        chat.new_turn("assistant")
        text_tokens = []
        for token in model.generate_sequential(**chat, max_new_tokens=512):
            if token.numel() == 1:
                text_tokens.append(token)
                yield processor.text.decode(
                    torch.cat(text_tokens), skip_special_tokens=True
                )
        if not text_tokens:
            yield ""


def tts_synthesis(text_input, voice_selection):
    """Synthesize audio, reporting errors through Gradio instead of audio paths."""
    text_input = (text_input or "").strip()
    if not text_input:
        raise gr.Error("Enter text to synthesize.")
    voices = {
        "US Male": "US male",
        "US Female": "US female",
        "UK Male": "UK male",
        "UK Female": "UK female",
    }
    if voice_selection not in voices:
        raise gr.Error("Select one of the supported voices.")
    with model_lock:
        model, processor = load_models()
        chat = new_chat(
            model, processor, f"Perform TTS. Use the {voices[voice_selection]} voice."
        )
        chat.new_turn("user")
        chat.add_text(text_input)
        chat.end_turn()
        chat.new_turn("assistant")
        tokens = [
            token
            for token in model.generate_sequential(
                **chat, max_new_tokens=512, audio_temperature=0.8, audio_top_k=64
            )
            if token.numel() > 1
        ]
        result = decode_audio(processor, tokens)
        if result is None:
            raise gr.Error(
                "The model produced no audio. Try a shorter or different text."
            )
        yield result


def create_ui():
    """Create the Gradio interface"""

    with gr.Blocks(title="Liquid Audio UI", delete_cache=(3600, 3600)) as demo:
        gr.Markdown("# 🎙️ Liquid Audio - LFM2.5-Audio-1.5B")
        gr.Markdown("Speech-to-Speech, ASR, and TTS capabilities in one place")

        with gr.Tabs():
            # Speech-to-Speech Chat Tab
            with gr.Tab("💬 Speech-to-Speech Chat"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Input")
                        audio_input = gr.Audio(
                            label="Upload Audio (or record)",
                            type="filepath",
                            sources=["upload", "microphone"],
                        )
                        text_input = gr.Textbox(
                            label="Text Input (optional)",
                            placeholder="Or type a message...",
                            lines=2,
                        )
                        system_prompt = gr.Textbox(
                            label="System Prompt (optional)",
                            placeholder="Leave blank for default: 'Respond with interleaved text and audio.'",
                            lines=2,
                        )
                        chat_submit = gr.Button("Send", variant="primary", size="lg")
                        chat_clear = gr.Button("New conversation")

                    with gr.Column():
                        gr.Markdown("### Response")
                        text_output = gr.Textbox(
                            label="Text Response", interactive=False, lines=5
                        )
                        audio_output = gr.Audio(label="Audio Response", type="numpy")

                chat_history = gr.State([])

                chat_submit.click(
                    fn=speech_to_speech_chat,
                    inputs=[audio_input, text_input, chat_history, system_prompt],
                    outputs=[text_output, audio_output, chat_history],
                    api_name="speech_to_speech_chat",
                    concurrency_id="model",
                    concurrency_limit=1,
                )
                chat_clear.click(
                    fn=lambda: ("", None, []),
                    inputs=[],
                    outputs=[text_output, audio_output, chat_history],
                    api_name="reset_chat",
                    concurrency_id="model",
                    concurrency_limit=1,
                )

                gr.Markdown("---")
                gr.Markdown(
                    "**How to use:**\n"
                    "1. Upload audio or record a message\n"
                    "2. Optionally add text input\n"
                    "3. Click Send to get a response with both text and audio\n"
                    "4. Continue the conversation - your history is preserved"
                )

            # ASR Tab
            with gr.Tab("📝 Automatic Speech Recognition"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Audio Input")
                        asr_audio_input = gr.Audio(
                            label="Upload Audio or Record",
                            type="filepath",
                            sources=["upload", "microphone"],
                        )
                        asr_submit = gr.Button(
                            "Transcribe", variant="primary", size="lg"
                        )

                    with gr.Column():
                        gr.Markdown("### Transcription")
                        asr_output = gr.Textbox(
                            label="Transcribed Text", interactive=False, lines=10
                        )

                asr_submit.click(
                    fn=asr_transcription,
                    inputs=asr_audio_input,
                    outputs=asr_output,
                    api_name="asr_transcription",
                    concurrency_id="model",
                    concurrency_limit=1,
                )

                gr.Markdown("---")
                gr.Markdown(
                    "**How to use:**\n"
                    "1. Upload an audio file or record speech\n"
                    "2. Click Transcribe to convert speech to text"
                )

            # TTS Tab
            with gr.Tab("🔊 Text-to-Speech"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Text Input")
                        tts_text_input = gr.Textbox(
                            label="Enter Text to Convert",
                            placeholder="Type the text you want to synthesize...",
                            lines=5,
                        )
                        voice_selection = gr.Radio(
                            choices=["US Male", "US Female", "UK Male", "UK Female"],
                            value="US Male",
                            label="Select Voice",
                        )
                        tts_submit = gr.Button(
                            "Synthesize", variant="primary", size="lg"
                        )

                    with gr.Column():
                        gr.Markdown("### Audio Output")
                        tts_output = gr.Audio(label="Generated Audio", type="numpy")

                tts_submit.click(
                    fn=tts_synthesis,
                    inputs=[tts_text_input, voice_selection],
                    outputs=tts_output,
                    api_name="tts_synthesis",
                    concurrency_id="model",
                    concurrency_limit=1,
                )

                gr.Markdown("---")
                gr.Markdown(
                    "**How to use:**\n"
                    "1. Enter text in the input field\n"
                    "2. Select a voice (US/UK, Male/Female)\n"
                    "3. Click Synthesize to generate audio"
                )

        gr.Markdown("---")
        gr.Markdown(
            "**Model:** LFM2.5-Audio-1.5B by Liquid AI\n"
            "**License:** LFM Open License v1.0"
        )

    return demo.queue()


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(server_name="127.0.0.1")
