# Code review and validation

Reviewed all tracked launcher scripts, Python application code, dependency declarations, metadata, and documentation. No repository AGENTS.md or runtime logs were present, and the starting worktree was clean.

## Batch 1: installation and launcher lifecycle

- Aligned install, start, menu detection, reset, and deduplication on `app/env`.
- Replaced unquoted shell version constraints and hand-maintained dependency lists with `requirements.txt`.
- Enabled normal dependency resolution instead of skipping Liquid Audio dependencies.
- Paired torch/torchaudio 2.8.0 with Liquid Audio 1.3.0; removed unused torchvision, xformers, DirectML, and incompatible Python 3.10 attention wheels.
- Corrected platform wheel selection and ensured every selected branch terminates instead of falling through to another installation.
- Made Update reuse installation and fast-forward Git changes only.
- Kept reset/update menu states visible after the environment disappears.
- Ignored local test environments, caches, and logs.

## Batch 2: application behavior

- Validated missing audio/text and unsupported voice selections before loading weights.
- Made unsupported hardware fail clearly before downloading models. The upstream decoder requires CUDA/ROCm; CPU/MPS inference is not claimed.
- Published the model and processor atomically after successful loading and serialized their use across endpoints.
- Downmixed stereo uploads to mono as required by ChatState.
- Replayed generated assistant tokens as AUDIO_OUT instead of re-encoding assistant speech as user audio input.
- Kept history on CPU, bounded it to ten exchanges, and added conversation reset.
- Removed end-of-audio markers without dropping valid frames when generation reaches the token limit; handled marker-only output.
- Decoded accumulated text while excluding special tokens.
- Replaced manually leaked temporary audio files with Gradio-managed outputs and timed cache cleanup.
- Reported TTS failures as errors instead of returning strings interpreted as audio filenames.
- Added explicit API names and one shared inference queue.

## Batch 3: documentation and API contract

- Corrected hardware requirements, package versions, environment paths, update behavior, cache retention, and model-test limitations.
- Removed the server-owned chat state argument from client examples.
- Replaced obsolete `/api/predict` examples with the Gradio client and two-step `/gradio_api/call` protocol.
- Avoided claiming a standalone repository license that is not present.

## Validation

- Four Node regression tests cover environment alignment, wheel selection, lifecycle menu states, and URL capture.
- Ten Python regression tests cover input validation, partial loading, hardware errors, stereo input, token decoding, history replay and bounds, and UI construction.
- One HTTP integration test covers audio serialization, multi-turn session state, reset, and the documented curl submission/event protocol.
- An isolated Python 3.12 environment resolved and installed all 101 dependencies; `uv pip check` passed.
- Ruff and `git diff --check` passed.

GPU inference, model quality, and actual Pinokio installation on each operating system were not exercised. Tests use the published libraries and real tensors with simulated model generation. Gradio emits upstream event-loop/deprecation warnings during tests; no test failures resulted.

## Launcher review checklist

The gepeto skill sections applied were its execution workflow, app launcher layout, URL capture, troubleshooting logs, virtual environments, dynamic menus, package management, and reproducible installation rules. Existing app and launcher locations were retained.

Reference patterns were `D:/pinokio/prototype/system/examples/mochi/install.js` (shell environment and nested torch script parameters, lines 44-68), `mochi/pinokio.js` (environment detection and dynamic menus), `mochi/reset.js` (fs.rm), and `accdiffusion/update.js` (repository pull). The local `D:/pinokio/prototype/PINOKIO.md` fs.rm/fs.link documentation was checked. Reset and deduplication target the environment rather than the tracked application source.

Exit checks: existing script structure retained; relative paths and Python virtual environments used; dependencies centralized; optional attention wheels removed; metadata schema version preserved; generated files ignored; README and API examples updated. The existing daemon launch binds to loopback, lets Gradio choose its port, and sets `local.url` using `input.event[1]`; URL capture regression testing passed. No stop script was added.

Upstream compatibility references: [Liquid Audio dependency metadata](https://github.com/Liquid4All/liquid-audio/blob/main/pyproject.toml), [processor and ChatState implementation](https://github.com/Liquid4All/liquid-audio/blob/main/src/liquid_audio/processor.py), [generation implementation](https://github.com/Liquid4All/liquid-audio/blob/main/src/liquid_audio/model/lfm2_audio.py), and [PyTorch 2.8 wheel commands](https://pytorch.org/get-started/previous-versions/). Gradio API routes were also checked against the installed 5.50.0 source and the live HTTP test.
