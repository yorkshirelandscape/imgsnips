# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Each opened PDF now gets its own tab instead of replacing (or merging into) whatever's already open. Icon size is remembered per tab; the window title and tab label both show the current file's name.
- ImgSnips now opens a PDF handed to it directly -- a command-line argument, or (macOS) Finder's "Open With" on an already-running instance, which now lists ImgSnips as a PDF viewer.
- New mirror button per card (flip horizontal by default, vertical with Option/Alt). It and the rotate button now swap their icon live while Option/Alt is held, previewing which direction a click will use.
- Saving now warns before overwriting files already in the destination folder, listing which ones, instead of silently replacing them.

### Fixed
- Rotating an image made its thumbnail ignore the current icon size, overflowing its card into neighboring ones. The rotated thumbnail was set from the on-disk cache copy (capped at a fixed 280px for reuse at any icon size) without the same downscale-to-current-size step every other thumbnail gets; it's now downscaled the same way immediately after rotating.
- The grid's reflow-on-resize could appear to freeze after opening a second PDF, showing a column count sized for an earlier, narrower window even seconds after a further resize. Traced to a now-redundant check that skipped rebuilding the grid unless it could already tell the column count had changed; removed it and unconditionally rebuild whenever the resize-debounce timer fires, so reflow can no longer get stuck on a stale reading.
- PyMuPDF (via its underlying MuPDF C library) intermittently dropped extracted files with no exception raised, most reproducible when opening a PDF shortly after another -- surfacing later as an unrelated-looking crash when the grid tried to load a thumbnail that never made it to disk. MuPDF's own docs call for external locking around concurrent use; extraction now holds a lock for the duration of every PyMuPDF call, and the background extraction thread was switched from `QThread` to a plain Python thread (repeated testing showed the failure specifically tied to QThread execution alongside a live Qt event loop, never reproducing on a plain thread or the main thread). Belt-and-suspenders: if an image's files are still missing by the time the grid tries to render it, that one card is now dropped with a console warning instead of crashing the whole grid.

### ToDo
- Round 2
  - Option to set background color instead of transparent

## [1.1.0] - 2026-08-04

### Added
- Images start unselected instead of all-selected by default.
- Shift+click an image to range-select from the last-clicked image to it.
- Double-click a thumbnail to preview it full-size; double-click a name to rename it.
- A copy button per image, for copying it straight to the clipboard.
- Right-click a thumbnail (or the rotate button) to rotate it clockwise; Option/Alt+right-click (or Option/Alt+click the rotate button) rotates counter-clockwise instead.
- Card layout redesigned: rename/rotate and view/copy icon buttons now flank the name and dimensions directly, with a divider below, instead of a separate button row.
- The image name uses a condensed sans-serif font ([Saira Condensed](https://github.com/Omnibus-Type/Saira)) and the dimensions use a monospace font ([Lilex](https://github.com/mishamyrt/Lilex)), both bundled under the SIL Open Font License.
- A Resize control (toolbar's Side/Length pair) lets saved images be constrained to a given pixel length -- by long side, short side, width, or height -- before writing them out; aspect ratio is preserved and images are only ever scaled down, never up.
- An icon-size slider (toolbar, far right, Apple Photos-style) scales thumbnails and their cards up or down; the grid reflows its column count to fit the window at any size or icon setting.

### Fixed
- The image grid rebuilds every card from scratch on an OS light/dark theme change; this previously reset every image's selection state along with it. Selection now survives a theme-triggered rebuild.
- The icon-size slider stopped growing thumbnails past 160px, since cards were rendered from a cached thumbnail file generated at a fixed 160x160 cap during extraction, and PIL's `.thumbnail()` only ever shrinks, never enlarges. The cache is now generated (and regenerated on rotate) at the slider's actual maximum instead of a fixed 160px, so images with enough native resolution genuinely fill a larger card.

### Changed
- Extraction now uses PyMuPDF directly instead of shelling out to a separately-installed `mutool` binary. No more "mutool not found" screen, PATH lookups, or install instructions -- PyMuPDF is bundled with the app, so images are extracted straight from the PDF in-process, with mask pairing and CMYK JPEG handling behaving the same as before.
- Reduced card padding and icon-button size to make room for a slightly larger image name; card bottom padding trimmed further since.
- Toolbar reorganized into stacked two-row groups to fit the icon-size slider and a two-line Resize control without overflowing: "Open PDF"/"Save Selected" shortened to "Open"/"Save" and stacked together, "Select All"/"Select None" collapsed to a "SELECT:" label (bold, larger, vertically centered) with stacked "All"/"None" buttons, PNG/WEBP format radios stacked next to Open/Save, and Resize split into a "Side:" (mode) row above a "Length:" (pixel value) row -- the Side dropdown and Length spinbox are held to the same width.
- Toolbar text now uses the same condensed sans as the image names (Saira Condensed) instead of the platform default; the Length input uses the monospace font (Lilex) that the dimension labels use, since it's a number rather than a word.
- Open (both the toolbar button and the big centered one on the empty-state screen) recolored pale yellow (previously the same pale blue as None); None and All swapped order (None on top) and given rounded corners and a blue color scheme matching Open/Save's style, with All more saturated than None since it's the more consequential of the two. The Length value is now right-aligned like a typical numeric field.
- Toolbar font bumped from 13pt to 17pt (SELECT: 16pt to 20pt) for legibility. Button padding and the spacing between each stacked pair (Open/Save, PNG/WEBP, None/All, Side/Length) were both trimmed down afterward to keep the buttons and their layout as compact as before the font bump -- only the text itself was meant to grow. The folder/save glyphs on Open/Save are now rendered as fixed-size icons rather than living in the button's text, so they no longer scale up along with it.

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
- The release build failed on every platform (`ModuleNotFoundError: No module named 'packaging'` from inside PyInstaller's own hooks) because `pipenv install --dev` resolves `packaging`/`setuptools` into `Pipfile.lock` correctly but doesn't actually install them into the virtualenv. The build now installs them directly as an explicit follow-up step.
- Background/full-page images that mutool extracts as JPEG were silently skipped, since the app assumed every extracted image was a PNG; extraction now resolves the actual file mutool produced for each image object
- Alpha-mask merging no longer fails when the base image is a JPEG (previously errored trying to save an RGBA result with a .jpg extension)
- Renaming an image now actually affects the exported filename (previously ignored by the save step)
- The packaged macOS app couldn't find mutool when launched normally (e.g. by double-clicking), since GUI apps don't inherit the shell's PATH; extraction now checks common install locations directly and reports a clear error if mutool truly isn't installed
- The macOS release zip contained a redundant duplicate of the app (a loose Unix executable alongside the .app bundle); only the .app is included now
- The packaged macOS app crashed on launch (segfault in Qt's library path resolution) because the release zip step dereferenced the .app bundle's internal symlinks into full duplicate file copies; the zip step now preserves symlinks correctly
- mutool occasionally extracts images as PAM (raw CMYK or CMYK+alpha data) rather than PNG/JPEG; these are now decoded correctly instead of crashing extraction
- A single unrecognized or corrupt image no longer aborts extraction of the whole PDF; it's skipped with a warning instead
- Image/alpha-mask pairing no longer guessed which extracted file was the correct mask by matching pixel dimensions; it now reads each image's real `/SMask` reference straight from the PDF. The old heuristic broke down whenever the document reused identical dimensions for repeated cover art, logos, or color swatches, causing images partway through a PDF to get cropped or recolored using the wrong mask.
- CMYK JPEGs written by Adobe tools (InDesign, Photoshop) were rendering as color negatives of themselves; Adobe's CMYK JPEG encoder stores channel values inverted, and Pillow doesn't correct for it automatically. Extraction now detects and un-inverts these images.
- The mutool-missing screen referenced the generic CSS font family "monospace" in a stylesheet, forcing Qt to enumerate every installed font to resolve the alias (a startup cost of a couple hundred milliseconds); it now asks for the system's fixed-width font directly instead.

### Changed
- Migrated the macOS build to PyInstaller's onedir mode; --onefile combined with a --windowed .app bundle is deprecated on macOS and will become a hard error in a future PyInstaller release
- Updated GitHub Actions dependencies (checkout, setup-python, upload-artifact, download-artifact) off the deprecated Node 20 runtime
- Documented the macOS Gatekeeper warning and quarantine-removal options in the README
- Renamed the project from PyPdf2Imgs to ImgSnips, including the window title (previously "PDF Image Selector")
- The app now ships with a real icon (in the window, on the packaged .app/.exe, and in the taskbar/Dock) instead of falling back to a generic default
