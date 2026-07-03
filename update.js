module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        message: "git pull"
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: [
          "uv pip install --upgrade gradio>=5.50.0 transformers>=4.30.0 accelerate>=0.20.0 librosa>=0.10.0 numba>=0.59.0 llvmlite>=0.44.0 sentencepiece",
          "uv pip install --upgrade liquid-audio --no-deps"
        ]
      }
    },
    {
      method: "notify",
      params: {
        html: "Update complete! The launcher and dependencies have been updated to the latest versions."
      }
    }
  ]
}
