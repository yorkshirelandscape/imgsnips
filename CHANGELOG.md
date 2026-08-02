# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Changed
- Renamed the project from PyPdf2Imgs to ImgSnips, including the window title (previously "PDF Image Selector").
- The app now ships with a real icon (in the window, on the packaged .app/.exe, and in the taskbar/Dock) instead of falling back to a generic default.

### Added
- The "Saved N images to ..." confirmation popup now shows the destination folder as a clickable link that opens it in the system file manager, instead of plain unclickable text.

### Fixed
- Image/alpha-mask pairing no longer guesses which extracted file is the correct mask by matching pixel dimensions; it now reads each image's real `/SMask` reference straight from the PDF. The old heuristic broke down whenever the document reused identical dimensions for repeated cover art, logos, or color swatches, causing images partway through a PDF to get cropped or recolored using the wrong mask.
- CMYK JPEGs written by Adobe tools (InDesign, Photoshop) were rendering as color negatives of themselves; Adobe's CMYK JPEG encoder stores channel values inverted, and Pillow doesn't correct for it automatically. Extraction now detects and un-inverts these images.
- The mutool-missing screen referenced the generic CSS font family "monospace" in a stylesheet, forcing Qt to enumerate every installed font to resolve the alias (a startup cost of a couple hundred milliseconds); it now asks for the system's fixed-width font directly instead.

## [1.0.0] - 2026-07-23
### Added
- PyQt6-based GUI, replacing the original Tkinter implementation
- Centered "Open PDF" button as the initial view, instead of auto-prompting a file dialog on launch
- Image selection shown via card border/background highlighting; click a thumbnail to toggle selection
- Per-image zoom, rename, and rotate actions
- Adaptive light/dark theming for the image grid that tracks the OS appearance live
- One-click `Fix macOS Warning.command` helper bundled with the macOS release to clear the Gatekeeper quarantine flag
- Startup check for mutool: if it isn't found, the window shows OS-specific install instructions and a download link instead of the Open PDF button, with a "Check Again" option

### Fixed
- Background/full-page images that mutool extracts as JPEG were silently skipped, since the app assumed every extracted image was a PNG; extraction now resolves the actual file mutool produced for each image object
- Alpha-mask merging no longer fails when the base image is a JPEG (previously errored trying to save an RGBA result with a .jpg extension)
- Renaming an image now actually affects the exported filename (previously ignored by the save step)
- The packaged macOS app couldn't find mutool when launched normally (e.g. by double-clicking), since GUI apps don't inherit the shell's PATH; extraction now checks common install locations directly and reports a clear error if mutool truly isn't installed
- The macOS release zip contained a redundant duplicate of the app (a loose Unix executable alongside the .app bundle); only the .app is included now
- The packaged macOS app crashed on launch (segfault in Qt's library path resolution) because the release zip step dereferenced the .app bundle's internal symlinks into full duplicate file copies; the zip step now preserves symlinks correctly
- mutool occasionally extracts images as PAM (raw CMYK or CMYK+alpha data) rather than PNG/JPEG; these are now decoded correctly instead of crashing extraction
- A single unrecognized or corrupt image no longer aborts extraction of the whole PDF; it's skipped with a warning instead

### Changed
- Migrated the macOS build to PyInstaller's onedir mode; --onefile combined with a --windowed .app bundle is deprecated on macOS and will become a hard error in a future PyInstaller release
- Updated GitHub Actions dependencies (checkout, setup-python, upload-artifact, download-artifact) off the deprecated Node 20 runtime
- Documented the macOS Gatekeeper warning and quarantine-removal options in the README
