// Liquid Audio needs matching torch and torchaudio, without optional attention wheels.
const variants = [
  ["{{gpu === 'nvidia' && (platform === 'win32' || platform === 'linux')}}", "cu128"],
  ["{{gpu === 'amd' && platform === 'linux'}}", "rocm6.4"],
  ["{{platform === 'darwin'}}", null],
  [null, "cpu"]
]
module.exports = {
  run: variants.map(([when, index]) => ({
    ...(when ? { when } : {}),
    method: "shell.run",
    params: {
      venv_python: "{{args && args.venv_python ? args.venv_python : '3.12'}}",
      venv: "{{args && args.venv ? args.venv : 'env'}}",
      path: "{{args && args.path ? args.path : 'app'}}",
      message: "uv pip install torch==2.8.0 torchaudio==2.8.0" +
        (index ? ` --index-url https://download.pytorch.org/whl/${index}` : "")
    },
    next: null
  }))
}
