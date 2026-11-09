# AI-Agent-Music-mastering

A reusable FFmpeg-based mastering toolkit for PREVAILER's music catalog. It creates transparent streaming and CD WAV masters, supports custom EQ/M/S/tape/dynamics configurations, and prints verified delivery measurements.

## What is included

- `scripts/master_audio.py` — deterministic mastering engine.
- `presets/` — JSON examples for the custom chains used in this catalog.
- `audio/source/` — source WAV/FLAC files supplied for the catalog.
- `audio/masters/` — mastered streaming, CD, and radio-edit WAV deliverables available in this workspace.
- `reports/` — catalog inventory and verification notes.
- `MASTERING_WORKFLOW.md` — the detailed workflow and delivery standards.

## Requirements

- Python 3.10+
- FFmpeg and FFprobe
- NumPy is required by the stereo-width verification routine in `master_audio.py`.

## Basic usage

```bash
python3 scripts/master_audio.py input.wav \
  --output-dir mastered \
  --title "Song Title" \
  --preset hybrid
```

Use a custom chain:

```bash
python3 scripts/master_audio.py input.wav \
  --output-dir mastered \
  --title "Song Title" \
  --config presets/custom_example.json
```

The command creates:

- A 24-bit / 48 kHz WAV for streaming platforms.
- A 16-bit / 44.1 kHz WAV for CD, with final triangular dither.
- Loudness, true-peak, loudness-range, stereo-width, and correlation measurements.

## Delivery targets

The default delivery target is approximately **−14 LUFS integrated** and **no higher than −1.0 dBTP**. These are safe technical targets, not universal platform requirements. The toolkit preserves dynamics when possible and reports the actual measurements rather than assuming the settings were achieved.

Stereo width is reported as the **Side-to-Mid RMS ratio**. This is distinct from stereo correlation: the ratio describes the amount of side energy, while correlation describes left/right phase relationship.

## Important notes

- The source audio remains the limiting factor: a 16-bit source cannot be converted into a true high-resolution recording by exporting it as 24-bit.
- EQ, saturation, widening, and limiting are creative operations. Listen to the final WAV before release.
- The public repository contains audio assets because the repository owner explicitly requested that they be included. Do not add confidential or unreleased material without confirming repository visibility.
- For explicit material, use a separate clean/radio edit rather than overwriting the original master.
