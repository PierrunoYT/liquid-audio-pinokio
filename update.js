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
        message: [
          "uv pip install --upgrade -r requirements.txt"
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
