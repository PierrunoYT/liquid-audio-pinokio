"""Regression tests use real tensors and ChatState, without model downloads."""

import importlib.util
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import gradio as gr
import numpy as np
import soundfile as sf
import torch

spec = importlib.util.spec_from_file_location(
    "audio_app", Path(__file__).parents[1] / "app/app.py"
)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class AudioProcessor(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.register_buffer("anchor", torch.zeros(1))

    def forward(self, wave, length):
        return torch.zeros(1, 128, 8), length


def fake_pair(tokens):
    tokenizer = Mock()
    tokenizer.encode.side_effect = lambda *args, **kwargs: torch.tensor([[1]])
    tokenizer.decode.side_effect = lambda tokens, **kwargs: "hello"
    processor = types.SimpleNamespace(
        device=torch.device("cpu"),
        text=tokenizer,
        audio=AudioProcessor(),
        decode=Mock(return_value=torch.tensor([[0.0, 2.0, -2.0]])),
    )
    model = torch.nn.Linear(1, 1)
    model.generate_interleaved = Mock(side_effect=lambda **kwargs: iter(tokens))
    model.generate_sequential = Mock(side_effect=lambda **kwargs: iter(tokens))
    return model, processor


class AudioTests(unittest.TestCase):
    def test_empty_inputs_fail_before_loading(self):
        with patch.object(app, "load_models") as load:
            for generator in [
                app.tts_synthesis("  ", "US Male"),
                app.asr_transcription(None),
                app.speech_to_speech_chat(None, "", [], ""),
            ]:
                with self.assertRaises(gr.Error):
                    list(generator)
            load.assert_not_called()

    def test_invalid_voice_is_reported(self):
        with self.assertRaises(gr.Error):
            list(app.tts_synthesis("hello", "invalid"))

    def test_cpu_fails_before_downloading(self):
        with (
            patch.object(app, "model", None),
            patch.object(app, "processor", None),
            patch.object(torch.cuda, "is_available", return_value=False),
            patch.object(app.LFM2AudioProcessor, "from_pretrained") as load,
        ):
            with self.assertRaises(gr.Error):
                app.load_models()
            load.assert_not_called()

    def test_partial_load_is_not_published(self):
        with (
            patch.object(app, "model", None),
            patch.object(app, "processor", None),
            patch.object(torch.cuda, "is_available", return_value=True),
            patch.object(torch.cuda, "is_bf16_supported", return_value=True),
            patch.object(app.LFM2AudioProcessor, "from_pretrained"),
            patch.object(
                app.LFM2AudioModel,
                "from_pretrained",
                side_effect=RuntimeError("failed"),
            ),
        ):
            with self.assertRaises(RuntimeError):
                app.load_models()
            self.assertIsNone(app.processor)
            self.assertIsNone(app.model)

    def test_stereo_upload_is_downmixed(self):
        with tempfile.TemporaryDirectory() as directory:
            filename = str(Path(directory) / "stereo.wav")
            sf.write(
                filename, np.array([[0.5, -0.5], [0.25, 0.75]]), 16000, subtype="FLOAT"
            )
            waveform, rate = app.read_audio(filename)
            self.assertEqual(rate, 16000)
            self.assertEqual(tuple(waveform.shape), (1, 2))
            torch.testing.assert_close(waveform, torch.tensor([[0.0, 0.5]]))

    def test_end_marker_and_token_limit(self):
        _, processor = fake_pair([])
        frame = torch.zeros(8, dtype=torch.long)
        end = torch.full((8,), 2048)
        for tokens, count in [
            ([frame], 1),
            ([frame, frame], 2),
            ([frame, end], 1),
            ([frame, end, frame], 2),
        ]:
            rate, samples = app.decode_audio(processor, tokens)
            self.assertEqual(processor.decode.call_args.args[0].shape[-1], count)
            self.assertEqual(rate, 24000)
            np.testing.assert_array_equal(samples, [0, 1, -1])
        processor.decode.reset_mock()
        self.assertIsNone(app.decode_audio(processor, [end]))
        self.assertIsNone(app.decode_audio(processor, []))
        processor.decode.assert_not_called()

    def test_tts_no_audio_raises_instead_of_returning_a_path(self):
        with (
            patch.object(app, "load_models", return_value=fake_pair([])),
            self.assertRaises(gr.Error),
        ):
            list(app.tts_synthesis("hello", "US Male"))

    def test_chat_replays_assistant_as_output_tokens(self):
        pair = fake_pair(
            [
                torch.tensor([5]),
                torch.zeros(8, dtype=torch.long),
                torch.full((8,), 2048),
            ]
        )
        with patch.object(app, "load_models", return_value=pair):
            first = list(app.speech_to_speech_chat(None, "hello", [], ""))[-1]
            history = first[2]
            second = list(app.speech_to_speech_chat(None, "again", history, ""))[-1]
        inputs = pair[0].generate_interleaved.call_args.kwargs
        self.assertEqual(inputs["audio_out"].shape, (8, 2))
        self.assertEqual(inputs["audio_in"].shape[-1], 0)
        self.assertEqual(len(history), 2)
        self.assertEqual(len(second[2]), 4)
        self.assertEqual(second[2][-1]["tokens"]["audio_out"].device.type, "cpu")

    def test_text_only_chat_and_history_bound(self):
        with patch.object(
            app, "load_models", return_value=fake_pair([torch.tensor([5])])
        ):
            history = []
            for _ in range(12):
                result = list(app.speech_to_speech_chat(None, "hello", history, ""))[-1]
                history = result[2]
            self.assertIsNone(result[1])
            self.assertEqual(len(history), app.MAX_HISTORY_TURNS)
            self.assertEqual(history[0]["role"], "user")

    def test_ui_builds_with_named_serialized_endpoints(self):
        demo = app.create_ui()
        names = {dependency["api_name"] for dependency in demo.config["dependencies"]}
        self.assertTrue(
            {
                "speech_to_speech_chat",
                "asr_transcription",
                "tts_synthesis",
                "reset_chat",
            }
            <= names
        )
        for fn in demo.fns.values():
            if fn.api_name in names:
                self.assertEqual(fn.concurrency_id, "model")
                self.assertEqual(fn.concurrency_limit, 1)
        demo.close()


if __name__ == "__main__":
    unittest.main()
