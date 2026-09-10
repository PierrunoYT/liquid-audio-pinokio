module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        message: "git pull --ff-only"
      }
    },
    {
      method: "script.start",
      params: {
        uri: "install.js"
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
