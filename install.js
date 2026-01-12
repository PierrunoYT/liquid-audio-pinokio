module.exports = {
  run: [
    // Install PyTorch with CUDA support first
    {
      method: "script.start",
      params: {
        uri: "torch.js",
        params: {
          venv_python: "3.12",
          venv: "env",
          xformers: true,
          flashattn: true
        }
      }
    },
    // Install Liquid Audio dependencies from requirements.txt (skip torch packages to preserve CUDA versions)
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: "uv pip install gradio>=5.50.0 liquid-audio transformers>=4.30.0 accelerate>=0.20.0 librosa>=0.10.0 numba>=0.59.0 llvmlite>=0.44.0 sentencepiece"
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
