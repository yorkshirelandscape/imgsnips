# ImgSnips

A modern, user-friendly tool for extracting and saving images from PDF files using a graphical interface. Built with Python and PyQt6, it uses [PyMuPDF](https://pymupdf.readthedocs.io/) for fast, accurate image extraction.

## Features
- Extracts all images from a PDF file with a single click
- Displays thumbnails in a scrollable, selectable grid
- Batch select/deselect images
- Rename images before saving
- Save selected images as PNG or WEBP

## Installation
1. Download the appropriate executable from GitHub Releases:
   - [macOS](https://github.com/yorkshirelandscape/imgsnips/releases/latest/download/ImgSnips-macos.zip)
   - [Windows](https://github.com/yorkshirelandscape/imgsnips/releases/latest/download/ImgSnips-windows.zip)
   - [Linux](https://github.com/yorkshirelandscape/imgsnips/releases/latest/download/ImgSnips-linux.zip)
2. **macOS only:** since the app isn't signed with a paid Apple Developer ID, Gatekeeper will flag it as coming from an unidentified developer (or warn that it "could damage your computer") the first time you open it. To clear that:
   - **Easiest:** double-click `Fix macOS Warning.command`, included in the zip next to the app. (It'll still prompt you once, since it's also unsigned — right-click it and choose "Open" instead of double-clicking if it doesn't open normally.)
   - **Or manually:** run this in Terminal after unzipping:
     ```sh
     xattr -d -r com.apple.quarantine ImgSnips.app
     ```

## Usage
1. Run the application.
2. Click "Open PDF" (either the button in the center of the window, or the toolbar button) and select a PDF file.
3. Browse, select, and rename images as desired.
4. Click "Save Selected" to export images to your chosen folder.

## Run from source or build your own executable

### Requirements
- [Python 3.9+](https://www.python.org/downloads/)
- Python packages:
  - `Pillow`
  - `PyQt6`
  - `PyMuPDF`
  - `pyinstaller` (only needed to build your own executable)

### Run from source
1. Install pipenv: `pip install --user pipenv`
2. Clone the repository: `git clone https://github.com/yorkshirelandscape/imgsnips.git`
3. Navigate into the directory: `cd imgsnips`
4. Install dependencies: `pipenv install`
5. Run it: `pipenv run python main.py`

### Build your own executable
1. Install dev dependencies: `pipenv install --dev`
2. Work around a pipenv issue where `packaging`/`setuptools` resolve into `Pipfile.lock` but don't actually land in the virtualenv, which otherwise breaks PyInstaller: `pipenv run pip install packaging setuptools`
3. Build with PyInstaller, bundling the spinner and app icon assets:
   - **macOS:** `pipenv run pyinstaller --windowed --name ImgSnips --icon packaging/icon/imgsnips.icns --add-data "spinner.gif:." --add-data "imgsnips.png:." --add-data "fonts:fonts" main.py` (onedir, not onefile — PyInstaller deprecates combining `--onefile` with a `--windowed` .app bundle on macOS)
   - **Linux:** `pipenv run pyinstaller --onefile --windowed --name ImgSnips --add-data "spinner.gif:." --add-data "imgsnips.png:." --add-data "fonts:fonts" main.py`
   - **Windows:** `pipenv run pyinstaller --onefile --windowed --name ImgSnips --icon packaging/icon/imgsnips.ico --add-data "spinner.gif;." --add-data "imgsnips.png;." --add-data "fonts;fonts" main.py`
4. Find the executable in `dist/`.

## License
[GNU Affero General Public License v3.0](LICENSE)

ImgSnips bundles [PyMuPDF](https://pymupdf.readthedocs.io/), which is dual-licensed
under the AGPL-3.0 or a commercial license from Artifex. Distributing ImgSnips means
distributing PyMuPDF with it, so ImgSnips is licensed under the AGPL-3.0 to match.

ImgSnips also bundles two fonts used in the image grid, both under the [SIL Open Font
License 1.1](https://openfontlicense.org/) (license text included alongside each font
in `fonts/`): [Saira Condensed](https://github.com/Omnibus-Type/Saira) by Héctor Gatti/
Omnibus-Type, and [Lilex](https://github.com/mishamyrt/Lilex) by the Lilex Project
Authors.
