# ComfyURLSwap

**v1.3.0** · Windows · Pure Python (Tkinter), **zero third-party dependencies** · **8 UI languages**

[简体中文](../README.md) | **English**

![Preview](../screenshot.png)

**ComfyURLSwap** is a small GUI downloader for ComfyUI model files. Paste a batch of
download links, and it will:

1. **Auto-detect your ComfyUI project** on startup (ComfyUI Desktop installs under
   `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs`, portable packages on common drives,
   or pick a folder manually — your choice is remembered).
2. **Swap HuggingFace links to the China mirror** — `huggingface.co` → `hf-mirror.com`
   automatically (can be turned off). Pasted `/blob/` web-page URLs are converted to
   `/resolve/` direct-download URLs automatically.
3. **Download with multi-threading and resume support** — byte-level resume
   (`.part` + `Range`), survives pause / network loss / closing the app; task list is
   persisted and restored on next launch; failed tasks retry with backoff.
4. **File every model into the right folder**: an **official ComfyUI model table**
   (`urlswap/model_table.json` — 153 official blueprint file names → folders, freely
   editable) is matched first by exact file name; anything unmatched falls back to
   URL / file-name keyword detection. Files land under `<project>\ComfyUI\models\`,
   in the right sub-folder (double-click a task to override):

   | Model type | Destination folder |
   | --- | --- |
   | Checkpoint (SD1.5 / SDXL / Stable Audio …) | `models/checkpoints/` |
   | Diffusion base (Flux / Qwen-Image / Wan / SD3.5 / Z-Image, incl. `fp8/int8/nvfp4` quantized) | `models/diffusion_models/` |
   | Text encoder (CLIP / T5 / UMT5 / Qwen-VL) | `models/text_encoders/` (legacy `models/clip/`) |
   | LoRA | `models/loras/` |
   | VAE | `models/vae/` |
   | Preview VAE (TAESD) | `models/vae_approx/` |
   | ControlNet | `models/controlnet/` |
   | Embedding / Textual Inversion | `models/embeddings/` |
   | CLIP Vision | `models/clip_vision/` |
   | Upscaler (ESRGAN …) | `models/upscale_models/` |
   | Latent upscaler | `models/latent_upscale_models/` |
   | Model patch / adapter (T2I-Adapter …) | `models/model_patches/` |
   | Style model (IP-Adapter …) | `models/style_models/` or `models/ipadapter/` |
   | GLIGEN / Hypernetwork / PhotoMaker / Classifier | `models/gligen/` etc. |
   | Detection / geometry / optical flow / frame interpolation / background removal / audio | `models/detection/`, `models/geometry_estimation/` etc. |
5. **Talk to you in your language** — the whole UI *and* log messages are localized in
   English · 简体中文 · 日本語 · 한국어 · Español · Français · Deutsch · Русский,
   auto-detected from your system locale on first run and switchable live via the
   dropdown at the top-right (your choice is remembered).

## Download

* **Windows EXE (recommended, no Python needed):**
  [GitHub Releases](https://github.com/carychief-gpt/ComfyURLSwap/releases/latest) →
  download `ComfyURLSwap-v1.3.0.exe` and double-click it. `settings.json` / `tasks.json`
  (preferences, resume data) are created next to the EXE on first run.
* **Run from source:** Python 3.8+ (with tkinter), then `python main.py`.

## Usage

1. Select your ComfyUI project in **step 1** (auto-detected or browse).
2. Paste model download links into **step 2**, one per line, then click
   **“＋ Add & start”** — links are mirrored and queued automatically.
3. Watch progress in the task table; finished files land in `models\<category>\`.
   Use **Open model folder** to verify. Double-click a row to change its category
   (before download, or while paused).

Buttons: Start/Resume · Pause All · Retry Failed · Cancel Selected · Change Category ·
Remove Completed · Open Model Folder.

## Security / privacy

* The app stores **no accounts, no tokens, no credentials** — it only issues plain
  HTTP GET requests to the download links you paste.
* Runtime files `settings.json` (local paths, preferences) and `tasks.json`
  (your download history) are deliberately **excluded from this repository** via
  `.gitignore`, so nothing personal is ever uploaded. Delete them anytime.

## Build from source

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name ComfyURLSwap ^
  --icon tools\app.ico --add-data "tools\app.ico;." ^
  --add-data "urlswap\model_table.json;urlswap" main.py
# → dist\ComfyURLSwap.exe
```

`tools\build_exe.bat` does the same on Windows; `tools\make_icon.py` regenerates the icon.

## Changelog

### v1.3.0
* **New official ComfyUI model table** (`urlswap/model_table.json`): scraped from the
  official repo's 116 workflow blueprints — 153 model file names → destination folders.
  Classification now matches this table first (exact file name) and only falls back to
  keyword rules afterwards; the table is plain JSON and freely editable
* Category folders fully aligned with official ComfyUI: added `text_encoders` (legacy
  `clip` folder still works), `vae_approx`, `latent_upscale_models`, `model_patches`,
  `style_models`, `detection`, `geometry_estimation`, `optical_flow`,
  `frame_interpolation`, `background_removal`, `audio_encoders` — all translated into
  the 8 UI languages
* Logs now state the routing source: official table hit / keyword hit / default

### v1.2.0
* **i18n:** entire UI + log/status messages localized — English, 简体中文, 日本語,
  한국어, Español, Français, Deutsch, Русский; auto-detected from system locale,
  live switch from the top-right language dropdown (persisted in settings)
* Category names (checkpoint / LoRA / CLIP …) fully translated in the task table and
  the category dialog
* Documentation reorganized: the root `README.md` is now the Chinese default;
  English documentation lives in `docs/README_en.md`

### v1.1.1
* Fix: quantized base models (`int8/int4/fp8/nvfp4/convrot/gguf/awq`, Hyper-SD) now go to `diffusion_models`
* Fix: speed LoRAs (`turbo`, `Nstep`, `lightning`, `lightx2v`) now go to `loras` even without “lora” in the filename
* New `diffusion_models` category (modern ComfyUI standard folder; legacy `unet` still selectable)

### v1.0.0
* First release: project auto-detect, hf-mirror swap, multithreaded download, resume, task persistence, auto model routing

## Repo layout

```
main.py                  # entry point
urlswap/
  ui.py                  # Tkinter GUI (dark theme, i18n)
  i18n.py                # translations — 8 languages
  downloader.py          # multithread / resume / task persistence
  project.py             # ComfyUI project auto-detection
  classify.py            # official model table + keyword routing rules
  model_table.json       # official ComfyUI blueprint table (filename -> folder, editable)
  settings.py            # settings IO (EXE-aware)
docs/
  README_en.md           # English documentation
tools/
  build_exe.bat          # one-click EXE rebuild
  make_icon.py           # regenerate app icon
  shot.py                # regenerate screenshot.png
  smoke_test.py          # headless automated tests
```
