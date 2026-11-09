# Mastering workflow

## Signal flow

1. Inspect the source with FFprobe and EBU R128.
2. Apply the requested parametric EQ.
3. Apply M/S processing when enabled. Keep low frequencies controlled with the side low-cut.
4. Apply compressor settings only when requested. A bypassed compressor remains bypassed.
5. Apply the requested Tape-style saturation approximation.
6. Apply limiter threshold and true-peak ceiling.
7. Run a measured loudness pass toward −14 LUFS integrated.
8. Render the streaming WAV at 24-bit / 48 kHz.
9. Render the CD WAV at 16-bit / 44.1 kHz with triangular dither exactly once at the final bit-depth conversion.
10. Verify the actual LUFS, LRA, true peak, duration, format, stereo width, and correlation.

## Verification

A master is not considered complete until the exported file is measured. In particular, final sample-rate conversion can change true peak, so the CD file must be verified separately from the streaming file. If a file exceeds the requested true-peak ceiling, apply a final calibrated true-peak pass and remeasure both loudness and peak.

## Stereo metrics

The toolkit reports:

- **Side-to-Mid RMS ratio:** `RMS(side) / RMS(mid)`, where mid is `(L + R) / 2` and side is `(L - R) / 2`.
- **Stereo correlation:** Pearson correlation between left and right channels.

A high Side-to-Mid ratio does not automatically mean a good mix. Check mono compatibility, vocal stability, bass centering, and phase behavior by ear.

## Platform guidance

- Spotify, Apple Music, YouTube, and SoundCloud: use the 24-bit streaming WAV unless a platform requests a different format.
- CD duplication: use the separate 16-bit / 44.1 kHz dithered WAV.
- Do not submit the CD export as the streaming master or vice versa.

## Radio edits

Radio edits should be rendered as separate files. Preserve the original duration where possible, censor only the explicit sections, use short fades at edit boundaries to avoid clicks, and keep the original master untouched.
