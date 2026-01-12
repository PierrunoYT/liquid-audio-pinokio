module.exports = {
  run: [
    // Install Liquid Audio dependencies first (before torch to prevent torchvision mismatch)
    {
      method: "shell.run",
      params: {
        venv_python: "3.12",
        venv: "env",
        message: [
          "uv pip install gradio>=5.50.0 transformers>=4.30.0 accelerate>=0.20.0 librosa>=0.10.0 numba>=0.59.0 llvmlite>=0.44.0 sentencepiece",
          "uv pip install liquid-audio --no-deps",
          "uv pip install huggingface-hub safetensors tokenizers pyyaml regex tqdm requests packaging"
        ]
      }
    },
    // Install PyTorch last (after requirements) - flags ensure correct version replaces any wrong one
    {
      method: "script.start",
      params: {
        uri: "torch.js",
        params: {
          venv: "env",
          xformers: true,
          flashattn: true
        }
      }
    },
    {
      method: "notify",
      params: {
        html: "Installation complete! Click 'Start' to launch Liquid Audio. Models will be downloaded automatically from Hugging Face on first use."
      }
    }
  ]
}
