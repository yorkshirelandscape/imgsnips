# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Each opened PDF now gets its own tab, with icon size remembered per tab and the window/tab titles showing the file name.
- ImgSnips now opens PDFs handed to it directly, via a command-line argument or (macOS) Finder's "Open With".
- New mirror button per card (horizontal by default, vertical with Option/Alt), with the rotate/mirror icons live-swapping to preview which direction a click will use.
- Saving now warns before overwriting files already in the destination folder, listing which ones, instead of silently replacing them.
- Open and Save dialogs each reopen to wherever you last used them, tracked independently of each other.

### Fixed
- Rotating an image could overflow its thumbnail past the card's current size; it's now downscaled consistently like every other thumbnail.
- The grid's reflow-on-resize could get stuck showing a stale column count after opening a second PDF; it now always rebuilds on resize.
- PyMuPDF intermittently dropped extracted files with no error, especially when opening PDFs back-to-back; extraction now locks around PyMuPDF calls, runs on a plain thread instead of `QThread`, and skips a card instead of crashing if its files never arrive.
- Some CMYK images extracted as color negatives again, occasionally. A previous fix manually un-inverted CMYK JPEGs carrying Adobe's APP14 marker, but a newer Pillow now does that unconditionally for every CMYK JPEG regardless of the marker; the two corrections stacked into a double-inversion for exactly the images still carrying it. Removed the now-redundant manual step.
- Holding Option/Alt to preview counter-clockwise rotation or vertical mirroring sometimes didn't swap the button icons until the mouse moved. It polled the OS's modifier-key state on a timer, which turned out to only refresh on the next event Qt happened to process; it now reacts to Option/Alt's own key event directly instead.

### Changed
- Slightly enlarged each card's icon buttons, name, and dimensions text for legibility, with proportionally more breathing room around them.
- The mirror button now uses custom artwork (a hollow vs. solid shape split by a dashed divider) instead of a plain ↔/↕ Unicode glyph, still swapping live between horizontal and vertical on Option/Alt.
- The rotate button now uses custom artwork (a bold curled arrow) instead of a plain ↻/↺ Unicode glyph, still swapping live between clockwise and counter-clockwise on Option/Alt.
- The loading spinner is now drawn directly instead of playing a baked GIF, so it's crisp at any size and tints to the live light/dark theme like the rest of the UI instead of one fixed color.
- Rearranged each card's buttons around the name box (zoom/rename above, copy below rename, rotate/mirror anchoring the bottom corners) to leave room for a possible future button, instead of two flat rows.

### ToDo
- Round 2
  - Option to set background color instead of transparent

## [1.1.0] - 2026-08-04

### Added
- Images start unselected instead of all-selected by default.
- Shift+click an image to range-select from the last-clicked image to it.
- Double-click a thumbnail to preview it full-size; double-click a name to rename it.
- A per-image copy button, for copying it straight to the clipboard.
- Right-click a thumbnail (or the rotate button) to rotate it clockwise; Option/Alt+right-click (or Option/Alt+click the rotate button) rotates counter-clockwise instead.
- Card layout redesigned: rename/rotate and view/copy icon buttons now flank the name and dimensions directly, with a divider below, instead of a separate button row.
- The image name uses a condensed sans-serif font ([Saira Condensed](https://github.com/Omnibus-Type/Saira)) and the dimensions use a monospace font ([Lilex](https://github.com/mishamyrt/Lilex)), both bundled under the SIL Open Font License.
- A Resize control (toolbar's Side/Length pair) constrains saved images to a given pixel length (long side, short side, width, or height), preserving aspect ratio and only ever scaling down.
- An icon-size slider (toolbar, far right, Apple Photos-style) scales thumbnails and their cards up or down; the grid reflows its column count to fit the window at any size or icon setting.

### Fixed
- Selection state now survives the grid rebuild triggered by an OS light/dark theme change (previously reset).
- The icon-size slider couldn't grow thumbnails past 160px, since the thumbnail cache was generated at a fixed 160x160 cap; it's now generated at the slider's actual maximum, so higher-resolution images can fill a larger card.

### Changed
- Extraction now uses bundled PyMuPDF directly instead of shelling out to a separately-installed `mutool` binary, removing the "mutool not found" screen and install instructions entirely.
- Toolbar reorganized into compact stacked two-row groups (Open/Save, PNG/WEBP, SELECT All/None, Resize Side/Length) to fit the icon-size slider without overflowing, now using the same condensed sans/monospace fonts (Saira Condensed / Lilex) as the image cards at a larger, more legible size.
- Open recolored pale yellow to stand out from None/All's blue scheme; None and All reordered (None on top) with rounded corners; Open/Save's icons are now fixed-size instead of scaling with the button text.
- Reduced card padding and icon-button size for a larger image name.

## [1.0.0] - 2026-08-03
> **License correction (2026-08-04):** originally published under the MIT License, but bundling GPL-3.0-only PyQt6 meant the distributed application was always bound by GPLv3 terms regardless of that label. Retroactively relicensed under the AGPL-3.0, matching the license used going forward.

### Added
- PyQt6-based GUI, replacing the original Tkinter implementation
- Centered "Open PDF" button as the initial view, instead of auto-prompting a file dialog on launch
- Image selection shown via card border/background highlighting; click a thumbnail to toggle selection
- Per-image zoom, rename, and rotate actions
- Adaptive light/dark theming for the image grid that tracks the OS appearance live
- One-click `Fix macOS Warning.command` helper bundled with the macOS release to clear the Gatekeeper quarantine flag
- Startup check for mutool: if it isn't found, the window shows OS-specific install instructions and a download link instead of the Open PDF button, with a "Check Again" option
- The "Saved N images to ..." confirmation popup shows the destination folder as a clickable link that opens it in the system file manager

### Fixed
- Fixed a release build failure (`ModuleNotFoundError: No module named 'packaging'`) by installing `packaging`/`setuptools` directly instead of relying on `pipenv install --dev`.
- Background/full-page JPEG images from mutool were silently skipped (extraction assumed PNG); it now resolves the actual file type produced.
- Alpha-mask merging no longer fails when the base image is a JPEG (previously errored trying to save an RGBA result with a .jpg extension).
- Renaming an image now actually affects the exported filename (previously ignored by the save step).
- The packaged macOS app couldn't find mutool when launched normally, since GUI apps don't inherit the shell's PATH; it now checks common install locations directly.
- The macOS release zip contained a redundant duplicate of the app (a loose Unix executable alongside the .app bundle); only the .app is included now.
- The packaged macOS app crashed on launch because the release zip step dereferenced the .app bundle's internal symlinks into full copies; it now preserves them correctly.
- mutool occasionally extracts images as PAM (raw CMYK or CMYK+alpha data) rather than PNG/JPEG; these are now decoded correctly instead of crashing extraction.
- A single unrecognized or corrupt image no longer aborts extraction of the whole PDF; it's skipped with a warning instead.
- Image/alpha-mask pairing now reads each image's real `/SMask` reference from the PDF instead of guessing by matching pixel dimensions, which broke on documents reusing identical dimensions for repeated art or logos.
- CMYK JPEGs from Adobe tools (InDesign, Photoshop) rendered as color negatives, since Adobe's encoder inverts channel values and Pillow doesn't correct for it; extraction now detects and un-inverts these.
- The mutool-missing screen's generic "monospace" CSS reference forced Qt to enumerate every installed font at a startup cost; it now asks for the system's fixed-width font directly.

### Changed
- Migrated the macOS build to PyInstaller's onedir mode; --onefile combined with a --windowed .app bundle is deprecated on macOS and will become a hard error in a future PyInstaller release
- Updated GitHub Actions dependencies (checkout, setup-python, upload-artifact, download-artifact) off the deprecated Node 20 runtime
- Documented the macOS Gatekeeper warning and quarantine-removal options in the README
- Renamed the project from PyPdf2Imgs to ImgSnips, including the window title (previously "PDF Image Selector")
- The app now ships with a real icon (in the window, on the packaged .app/.exe, and in the taskbar/Dock) instead of falling back to a generic default
