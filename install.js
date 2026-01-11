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
    // Install Liquid Audio dependencies from requirements.txt
    {
      method: "shell.run",
      params: {
        venv: "env",
        message: [
          "pip install -r requirements.txt"
        ],
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
