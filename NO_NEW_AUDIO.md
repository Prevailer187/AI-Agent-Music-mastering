# Audio freeze policy

The audio catalog is frozen at the files already committed to this repository.

Do not add, replace, or update audio files in future commits or pull requests. The existing source, master, and radio-edit assets remain available for reference, but all future changes should be limited to code, presets, documentation, reports, and other non-audio project files.

This policy is enforced in two ways:

- `.gitignore` ignores newly untracked audio files.
- `.github/workflows/reject-new-audio.yml` fails pull requests that add audio files.

If an existing audio file must be corrected, document the reason and obtain an explicit exception before changing it.
