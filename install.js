module.exports = {
  requires: {
    bundle: "ai"
  },
  run: [
    // Install the platform-specific torch build into the application's environment.
    {
      method: "script.start",
      params: {
        uri: "torch.js",
        params: { path: "app", venv: "env", venv_python: "3.12" }
      }
    },
    {
      method: "shell.run",
      params: {
        venv_python: "3.12",
        venv: "env",
        path: "app",
        message: [
          "uv pip install -r requirements.txt",
          "uv pip check"
        ]
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
