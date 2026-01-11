import torch
import torchaudio
import gradio as gr
from liquid_audio import LFM2AudioModel, LFM2AudioProcessor, ChatState, LFMModality
from typing import Optional
import tempfile
import os
import numpy as np

# Global model and processor
model = None
processor = None

def load_models():
    """Load the Liquid Audio model and processor"""
    global model, processor
    if model is None or processor is None:
        HF_REPO = "LiquidAI/LFM2.5-Audio-1.5B"
        processor = LFM2AudioProcessor.from_pretrained(HF_REPO).eval()
        model = LFM2AudioModel.from_pretrained(HF_REPO).eval()
    return model, processor

def speech_to_speech_chat(audio_input, text_input, chat_history, system_prompt):
    """Handle multi-turn speech-to-speech conversation"""
    try:
        model, processor = load_models()
        
        chat = ChatState(processor)
        
        # Set system prompt
        chat.new_turn("system")
        chat.add_text(system_prompt or "Respond with interleaved text and audio.")
        chat.end_turn()
        
        # Add chat history
        for role, (audio_data, text_data) in chat_history:
            chat.new_turn(role)
            if audio_data is not None:
                wav, sr = torchaudio.load(audio_data) if isinstance(audio_data, str) else audio_data
                chat.add_audio(wav, sr)
            if text_data:
                chat.add_text(text_data)
            chat.end_turn()
        
        # Add current user input
        chat.new_turn("user")
        if audio_input is not None:
            wav, sr = torchaudio.load(audio_input)
            chat.add_audio(wav, sr)
        if text_input:
            chat.add_text(text_input)
        chat.end_turn()
        
        chat.new_turn("assistant")
        
        # Generate response
        text_out = []
        audio_out = []
        modality_out = []
        full_text = ""
        
        for t in model.generate_interleaved(**chat, max_new_tokens=512, audio_temperature=1.0, audio_top_k=4):
            if t.numel() == 1:
                text_token = processor.text.decode(t)
                full_text += text_token
                text_out.append(t)
                modality_out.append(LFMModality.TEXT)
                yield full_text, None, chat_history
            else:
                audio_out.append(t)
                modality_out.append(LFMModality.AUDIO_OUT)
        
        # Detokenize audio
        audio_file = None
        if audio_out:
            audio_codes = torch.stack(audio_out[:-1], 1).unsqueeze(0)
            waveform = processor.decode(audio_codes)
            
            # Ensure waveform is in correct format for saving
            waveform_cpu = waveform.cpu()
            
            # Ensure 2D tensor (channels, samples)
            if waveform_cpu.dim() == 1:
                waveform_cpu = waveform_cpu.unsqueeze(0)
            elif waveform_cpu.dim() > 2:
                waveform_cpu = waveform_cpu.squeeze()
                if waveform_cpu.dim() == 1:
                    waveform_cpu = waveform_cpu.unsqueeze(0)
            
            # Clip to valid range
            waveform_cpu = torch.clamp(waveform_cpu, -1.0, 1.0)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                torchaudio.save(tmp.name, waveform_cpu, 24_000, encoding="PCM_S", bits_per_sample=16)
                audio_file = tmp.name
        
        # Update chat history
        new_history = chat_history + [("user", (audio_input, text_input))]
        new_history = new_history + [("assistant", (audio_file, full_text))]
        
        yield full_text, audio_file, new_history
        
    except Exception as e:
        yield f"Error: {str(e)}", None, chat_history

def asr_transcription(audio_input):
    """Perform Automatic Speech Recognition"""
    try:
        model, processor = load_models()
        
        chat = ChatState(processor)
        
        chat.new_turn("system")
        chat.add_text("Perform ASR.")
        chat.end_turn()
        
        chat.new_turn("user")
        wav, sr = torchaudio.load(audio_input)
        chat.add_audio(wav, sr)
        chat.end_turn()
        
        chat.new_turn("assistant")
        
        full_text = ""
        for t in model.generate_sequential(**chat, max_new_tokens=512):
            if t.numel() == 1:
                text_token = processor.text.decode(t)
                full_text += text_token
                yield full_text
    except Exception as e:
        yield f"Error: {str(e)}"

def tts_synthesis(text_input, voice_selection):
    """Perform Text-to-Speech synthesis"""
    try:
        model, processor = load_models()
        
        voice_prompts = {
            "US Male": "Perform TTS. Use the US male voice.",
            "US Female": "Perform TTS. Use the US female voice.",
            "UK Male": "Perform TTS. Use the UK male voice.",
            "UK Female": "Perform TTS. Use the UK female voice.",
        }
        
        system_prompt = voice_prompts.get(voice_selection, voice_prompts["US Male"])
        
        chat = ChatState(processor)
        
        chat.new_turn("system")
        chat.add_text(system_prompt)
        chat.end_turn()
        
        chat.new_turn("user")
        chat.add_text(text_input)
        chat.end_turn()
        
        chat.new_turn("assistant")
        
        audio_out = []
        for t in model.generate_sequential(**chat, max_new_tokens=512, audio_temperature=0.8, audio_top_k=64):
            if t.numel() > 1:
                audio_out.append(t)
        
        # Detokenize audio
        if audio_out:
            audio_codes = torch.stack(audio_out[:-1], 1).unsqueeze(0)
            waveform = processor.decode(audio_codes)
            
            # Ensure waveform is in the correct shape and format
            waveform_np = waveform.cpu().squeeze().numpy()
            
            # Handle multi-channel audio - take first channel if stereo
            if waveform_np.ndim > 1:
                waveform_np = waveform_np[0]
            
            # Ensure the audio is in float32 format normalized between -1 and 1
            waveform_np = waveform_np.astype(np.float32)
            
            # Clip values to valid range
            waveform_np = np.clip(waveform_np, -1.0, 1.0)
            
            # Return as (sample_rate, numpy_array) tuple
            yield (24_000, waveform_np)
        
    except Exception as e:
        yield f"Error: {str(e)}"

def create_ui():
    """Create the Gradio interface"""
    
    with gr.Blocks(title="Liquid Audio UI") as demo:
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
                            sources=["upload", "microphone"]
                        )
                        text_input = gr.Textbox(
                            label="Text Input (optional)",
                            placeholder="Or type a message...",
                            lines=2
                        )
                        system_prompt = gr.Textbox(
                            label="System Prompt (optional)",
                            placeholder="Leave blank for default: 'Respond with interleaved text and audio.'",
                            lines=2
                        )
                        chat_submit = gr.Button("Send", variant="primary", size="lg")
                    
                    with gr.Column():
                        gr.Markdown("### Response")
                        text_output = gr.Textbox(
                            label="Text Response",
                            interactive=False,
                            lines=5
                        )
                        audio_output = gr.Audio(
                            label="Audio Response",
                            type="filepath"
                        )
                
                chat_history = gr.State([])
                
                chat_submit.click(
                    fn=speech_to_speech_chat,
                    inputs=[audio_input, text_input, chat_history, system_prompt],
                    outputs=[text_output, audio_output, chat_history]
                )
                
                gr.Markdown("---")
                gr.Markdown("**How to use:**\n"
                           "1. Upload audio or record a message\n"
                           "2. Optionally add text input\n"
                           "3. Click Send to get a response with both text and audio\n"
                           "4. Continue the conversation - your history is preserved")
            
            # ASR Tab
            with gr.Tab("📝 Automatic Speech Recognition"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Audio Input")
                        asr_audio_input = gr.Audio(
                            label="Upload Audio or Record",
                            type="filepath",
                            sources=["upload", "microphone"]
                        )
                        asr_submit = gr.Button("Transcribe", variant="primary", size="lg")
                    
                    with gr.Column():
                        gr.Markdown("### Transcription")
                        asr_output = gr.Textbox(
                            label="Transcribed Text",
                            interactive=False,
                            lines=10
                        )
                
                asr_submit.click(
                    fn=asr_transcription,
                    inputs=asr_audio_input,
                    outputs=asr_output
                )
                
                gr.Markdown("---")
                gr.Markdown("**How to use:**\n"
                           "1. Upload an audio file or record speech\n"
                           "2. Click Transcribe to convert speech to text")
            
            # TTS Tab
            with gr.Tab("🔊 Text-to-Speech"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Text Input")
                        tts_text_input = gr.Textbox(
                            label="Enter Text to Convert",
                            placeholder="Type the text you want to synthesize...",
                            lines=5
                        )
                        voice_selection = gr.Radio(
                            choices=["US Male", "US Female", "UK Male", "UK Female"],
                            value="US Male",
                            label="Select Voice"
                        )
                        tts_submit = gr.Button("Synthesize", variant="primary", size="lg")
                    
                    with gr.Column():
                        gr.Markdown("### Audio Output")
                        tts_output = gr.Audio(
                            label="Generated Audio",
                            type="numpy"
                        )
                
                tts_submit.click(
                    fn=tts_synthesis,
                    inputs=[tts_text_input, voice_selection],
                    outputs=tts_output
                )
                
                gr.Markdown("---")
                gr.Markdown("**How to use:**\n"
                           "1. Enter text in the input field\n"
                           "2. Select a voice (US/UK, Male/Female)\n"
                           "3. Click Synthesize to generate audio")
        
        gr.Markdown("---")
        gr.Markdown("**Model:** LFM2.5-Audio-1.5B by Liquid AI\n"
                   "**License:** LFM Open License v1.0")
    
    return demo

if __name__ == "__main__":
    demo = create_ui()
    demo.launch(share=True)