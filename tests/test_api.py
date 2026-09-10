"""Exercise the actual Gradio HTTP API with deterministic model outputs."""

import unittest
from unittest.mock import patch

import torch
from gradio_client import Client
from test_app import app, fake_pair


class ApiTests(unittest.TestCase):
    def test_audio_and_stateful_chat_api(self):
        pair = fake_pair([torch.tensor([5]), torch.zeros(8, dtype=torch.long)])
        with patch.object(app, "load_models", return_value=pair):
            demo = app.create_ui()
            try:
                _, url, _ = demo.launch(
                    server_name="127.0.0.1", prevent_thread_lock=True, quiet=True
                )
                client = Client(url, verbose=False)
                audio = client.predict("Hello", "US Male", api_name="/tts_synthesis")
                self.assertTrue(audio.endswith(".wav"))
                first = client.predict(
                    None, "Hello", "", api_name="/speech_to_speech_chat"
                )
                self.assertEqual(first[0], "hello")
                client.predict(None, "Again", "", api_name="/speech_to_speech_chat")
                inputs = pair[0].generate_interleaved.call_args.kwargs
                self.assertEqual(inputs["audio_out"].shape[-1], 1)
                client.predict(api_name="/reset_chat")
                client.predict(None, "Fresh", "", api_name="/speech_to_speech_chat")
                inputs = pair[0].generate_interleaved.call_args.kwargs
                self.assertEqual(inputs["audio_out"].shape[-1], 0)
                client.close()
            finally:
                demo.close()


if __name__ == "__main__":
    unittest.main()
