# ImgSnips
# Copyright (C) 2026 Andrew Howard
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import os
import sys
import shutil
import tempfile

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QMovie, QPixmap, QCursor, QPalette, QColor, QIcon, QFont, QFontDatabase
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame, QScrollArea, QFileDialog,
    QMessageBox, QRadioButton, QButtonGroup, QStackedWidget, QDialog, QInputDialog,
)
from PIL import Image
from PIL.ImageQt import ImageQt

import pdf_extract as pe

# PyInstaller's onefile mode extracts bundled data files to a temp dir at
# runtime (sys._MEIPASS), not next to the script/executable.
SCRIPT_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
SPINNER_PATH = os.path.join(SCRIPT_DIR, 'spinner.gif')
ICON_PATH = os.path.join(SCRIPT_DIR, 'imgsnips.png')
FONTS_DIR = os.path.join(SCRIPT_DIR, 'fonts')
THUMB_SIZE = 160
GRID_COLS = 4

NAME_FONT_FAMILY = 'Saira Condensed'
SIZE_FONT_FAMILY = 'Lilex'


def load_bundled_fonts():
    """Register the card labels' fonts with Qt before any window is built.
    Falls back to the platform default silently if a font fails to load
    (setFont on an unrecognized family just uses the closest match)."""
    for fname in ('SairaCondensed-Medium.ttf', 'Lilex-Regular.ttf'):
        QFontDatabase.addApplicationFont(os.path.join(FONTS_DIR, fname))


def pil_to_pixmap(pil_img):
    return QPixmap.fromImage(ImageQt(pil_img.convert('RGBA')))


class ExtractWorker(QThread):
    finished_ok = pyqtSignal(list)
    no_images = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, pdf_path, outdir):
        super().__init__()
        self.pdf_path = pdf_path
        self.outdir = outdir

    def run(self):
        try:
            images = pe.extract_images(self.pdf_path, self.outdir)
        except Exception as e:
            self.error.emit(str(e))
            return
        if not images:
            self.no_images.emit()
            return
        self.finished_ok.emit(images)


class ClickableLabel(QLabel):
    clicked = pyqtSignal(bool)  # emits whether Shift was held
    doubleClicked = pyqtSignal()
    rotateRequested = pyqtSignal(bool)  # emits whether the rotation is clockwise

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            shift_held = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            self.clicked.emit(shift_held)
        elif event.button() == Qt.MouseButton.RightButton:
            clockwise = not (event.modifiers() & Qt.KeyboardModifier.AltModifier)
            self.rotateRequested.emit(clockwise)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)


class IconButton(QPushButton):
    """QPushButton that also reacts to a right-click (Alt+right-click for
    the reverse direction), used for the rotate button's clockwise/
    counter-clockwise gesture. Harmless no-op for buttons that don't
    connect to rightClicked."""
    rightClicked = pyqtSignal(bool)  # emits whether the rotation is clockwise

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            clockwise = not (event.modifiers() & Qt.KeyboardModifier.AltModifier)
            self.rightClicked.emit(clockwise)
            return
        super().mousePressEvent(event)


class FullImageDialog(QDialog):
    def __init__(self, parent, orig_path, meta, img_file):
        super().__init__(parent)
        self.setWindowTitle(f"Full Image: {img_file}")

        screen = QApplication.primaryScreen().availableGeometry()
        max_w = min(1600, screen.width() - 100)
        max_h = min(1200, screen.height() - 100)

        pil_full = Image.open(orig_path)
        img_w, img_h = pil_full.size
        scale = min(1.0, max_w / img_w, max_h / img_h)
        if scale < 1.0:
            pil_disp = pil_full.resize((int(img_w * scale), int(img_h * scale)), Image.Resampling.LANCZOS)
        else:
            pil_disp = pil_full

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        info_label = QLabel(f"{img_file}  |  {meta.get('width', '?')} x {meta.get('height', '?')}")
        info_label.setStyleSheet('background:#222; color:#fff; padding:4px;')
        layout.addWidget(info_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        image_label = QLabel()
        image_label.setPixmap(pil_to_pixmap(pil_disp))
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(image_label)
        layout.addWidget(scroll)

        self.resize(min(pil_disp.width + 40, max_w + 40), min(pil_disp.height + 80, max_h + 80))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('ImgSnips')
        self.images = []
        self.tmpdir = None
        self.spinner_movie = None
        self.theme_colors = {}
        self._selection_anchor_idx = None
        self._build_ui()
        self._center_on_screen(965, 800)
        QApplication.instance().styleHints().colorSchemeChanged.connect(self._on_color_scheme_changed)

    def _is_dark_mode(self):
        scheme = QApplication.instance().styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return True
        if scheme == Qt.ColorScheme.Light:
            return False
        # Unknown: fall back to inspecting the actual palette we were handed.
        return self.palette().color(QPalette.ColorRole.Window).lightness() < 128

    def _compute_theme_colors(self):
        """Derive card/text colors from the live system palette instead of
        hardcoding a light- or dark-mode assumption, so the UI tracks whatever
        appearance the OS is actually set to (and updates if it changes)."""
        window = self.palette().color(QPalette.ColorRole.Window)
        text = self.palette().color(QPalette.ColorRole.WindowText)
        if self._is_dark_mode():
            unselected_bg = window.lighter(128)
            unselected_border = window.lighter(165)
            selected_bg = QColor('#123a5c')
            selected_border = QColor('#64b5f6')
        else:
            unselected_bg = window.darker(107)
            unselected_border = window.darker(120)
            selected_bg = QColor('#e3f2fd')
            selected_border = QColor('#1976d2')
        secondary_text = QColor(text)
        secondary_text.setAlpha(160)
        return {
            'text': text.name(),
            'secondary_text': f'rgba({secondary_text.red()}, {secondary_text.green()}, {secondary_text.blue()}, {secondary_text.alpha()})',
            'unselected_bg': unselected_bg.name(),
            'unselected_border': unselected_border.name(),
            'selected_bg': selected_bg.name(),
            'selected_border': selected_border.name(),
            # A low-alpha white overlay lightens either the selected or
            # unselected card background by the same subtle amount, rather
            # than needing a separate fixed color per selection state.
            'name_bg': 'rgba(255, 255, 255, 28)',
        }

    def _on_color_scheme_changed(self, _scheme):
        self.render_grid()

    def _center_on_screen(self, w, h):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.x() + (screen.width() - w) // 2
        y = screen.y() + (screen.height() - h) // 2
        self.setGeometry(x, y, w, h)

    def _build_ui(self):
        toolbar = QWidget()
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 5, 12, 5)

        self.btn_open = QPushButton('\U0001F4C2 Open PDF')
        self.btn_open.setStyleSheet(
            'background:#bbdefb; color:#0d47a1; font-weight:600; border-radius:8px; padding:4px 12px;'
        )
        self.btn_open.clicked.connect(self.open_pdf)
        tb_layout.addWidget(self.btn_open)

        tb_layout.addStretch(1)

        self.btn_all = QPushButton('Select All')
        self.btn_all.clicked.connect(self.select_all)
        tb_layout.addWidget(self.btn_all)

        self.btn_none = QPushButton('Select None')
        self.btn_none.clicked.connect(self.select_none)
        tb_layout.addWidget(self.btn_none)

        tb_layout.addStretch(1)

        self.rb_png = QRadioButton('PNG')
        self.rb_png.setChecked(True)
        self.rb_webp = QRadioButton('WEBP')
        fmt_group = QButtonGroup(self)
        fmt_group.addButton(self.rb_png)
        fmt_group.addButton(self.rb_webp)
        tb_layout.addWidget(self.rb_png)
        tb_layout.addWidget(self.rb_webp)

        self.btn_save = QPushButton('\U0001F4BE Save Selected')
        self.btn_save.setStyleSheet('background:#43a047; border-radius:8px; padding:4px 12px;')
        self.btn_save.clicked.connect(self.save_selected)
        tb_layout.addWidget(self.btn_save)

        self.stack = QStackedWidget()

        # --- Empty state: big centered Open PDF button ---
        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        big_open_btn = QPushButton('\U0001F4C2  Open PDF')
        big_open_btn.setFixedSize(240, 80)
        big_open_btn.setStyleSheet(
            'font-size: 18px; background: #bbdefb; color: #0d47a1; font-weight: 600; border-radius: 8px;'
        )
        big_open_btn.clicked.connect(self.open_pdf)
        hcenter = QHBoxLayout()
        hcenter.addStretch(1)
        hcenter.addWidget(big_open_btn)
        hcenter.addStretch(1)
        empty_layout.addStretch(1)
        empty_layout.addLayout(hcenter)
        empty_layout.addStretch(1)
        self.stack.addWidget(empty_page)  # index 0

        # --- Grid page ---
        grid_page = QWidget()
        grid_page_layout = QVBoxLayout(grid_page)
        grid_page_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet('border: none;')
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setHorizontalSpacing(24)
        self.grid_layout.setVerticalSpacing(18)
        self.scroll_area.setWidget(self.grid_container)
        grid_page_layout.addWidget(self.scroll_area)
        self.stack.addWidget(grid_page)  # index 1

        # --- Spinner page ---
        spinner_page = QWidget()
        spinner_layout = QVBoxLayout(spinner_page)
        self.spinner_label = QLabel()
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spinner_layout.addWidget(self.spinner_label)
        self.stack.addWidget(spinner_page)  # index 2

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(toolbar)
        central_layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

    # --- PDF opening / extraction ---
    def open_pdf(self):
        pdf_path, _ = QFileDialog.getOpenFileName(self, 'Select PDF file', '', 'PDF files (*.pdf)')
        if not pdf_path:
            return
        self.show_spinner()
        self.tmpdir = pe.make_extract_dir(self.tmpdir)
        self.worker = ExtractWorker(pdf_path, self.tmpdir)
        self.worker.finished_ok.connect(self.on_extract_finished)
        self.worker.no_images.connect(self.on_no_images)
        self.worker.error.connect(self.on_extract_error)
        self.worker.start()

    def show_spinner(self):
        self.spinner_movie = QMovie(SPINNER_PATH)
        self.spinner_label.setMovie(self.spinner_movie)
        self.spinner_movie.start()
        self.stack.setCurrentIndex(2)

    def hide_spinner(self):
        if self.spinner_movie:
            self.spinner_movie.stop()
            self.spinner_movie = None

    def _return_to_prior_page(self):
        self.stack.setCurrentIndex(1 if self.images else 0)

    def on_no_images(self):
        self.hide_spinner()
        self._return_to_prior_page()
        QMessageBox.information(self, 'No Images', 'No images found in PDF.')

    def on_extract_error(self, message):
        self.hide_spinner()
        self._return_to_prior_page()
        QMessageBox.critical(self, 'Extraction Error', message)

    def on_extract_finished(self, images):
        self.hide_spinner()
        self.images = images
        self._selection_anchor_idx = None
        self.render_grid()
        self.stack.setCurrentIndex(1)

    # --- Grid rendering ---
    def clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def render_grid(self):
        self.theme_colors = self._compute_theme_colors()
        self.clear_grid()
        page_counter = {}
        last_row = 0
        for idx, img in enumerate(self.images):
            row = idx // GRID_COLS
            col = idx % GRID_COLS
            cell = self._build_cell(img, page_counter, idx)
            self.grid_layout.addWidget(cell, row, col, Qt.AlignmentFlag.AlignTop)
            last_row = row
        # Soak up leftover vertical space in a phantom row so cards stay
        # compact at the top instead of stretching to fill the scroll area.
        self.grid_layout.setRowStretch(last_row + 1, 1)

    def _build_cell(self, img, page_counter, idx):
        meta = img['meta']
        pg = meta.get('page', '?')
        pg_str = f"{int(pg):03}" if isinstance(pg, int) else str(pg)
        page_counter[pg_str] = page_counter.get(pg_str, 0) + 1
        idx_str = f"{page_counter[pg_str]:02}"
        if not img.get('save_name'):
            img['save_name'] = f"pg{pg_str}-{idx_str}"
        # Rebuilt from scratch on every render_grid() call (e.g. on an OS
        # theme change), so use setdefault rather than clobbering a
        # selection the user already made.
        img.setdefault('selected', False)
        img['_idx'] = idx

        card = QFrame()
        card.setObjectName('imageCard')
        v = QVBoxLayout(card)
        v.setContentsMargins(6, 6, 6, 2)
        v.setSpacing(4)

        thumb_path = img['thumb_path'] if os.path.exists(img['thumb_path']) else img['orig_path']
        pil_thumb = Image.open(thumb_path)
        pil_thumb.thumbnail((THUMB_SIZE, THUMB_SIZE))
        thumb_label = ClickableLabel()
        thumb_label.setPixmap(pil_to_pixmap(pil_thumb))
        thumb_label.setFixedSize(THUMB_SIZE, THUMB_SIZE)
        thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb_label.setToolTip('Click to select • double-click to preview • right-click to rotate')
        thumb_label.clicked.connect(lambda shift_held, img=img: self.handle_thumb_clicked(img, shift_held))
        thumb_label.doubleClicked.connect(lambda img=img: self.show_full_res(img))
        thumb_label.rotateRequested.connect(lambda clockwise, img=img: self.rotate_image(img, clockwise))
        v.addWidget(thumb_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        img['_thumb_label'] = thumb_label

        info_grid = QGridLayout()
        info_grid.setContentsMargins(0, 2, 0, 0)
        info_grid.setHorizontalSpacing(3)
        info_grid.setVerticalSpacing(1)
        info_grid.setColumnStretch(1, 1)

        rename_btn = self._make_icon_button('✏️', 'Rename', self.theme_colors['text'])
        rename_btn.clicked.connect(lambda _, img=img: self.rename_image(img))
        name_label = ClickableLabel(img['save_name'])
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setFont(QFont(NAME_FONT_FAMILY, 13))
        name_label.setStyleSheet(
            f"color: {self.theme_colors['text']}; background: {self.theme_colors['name_bg']}; "
            'padding: 1px 4px;'
        )
        name_label.setToolTip('Double-click to rename')
        name_label.doubleClicked.connect(lambda img=img: self.rename_image(img))
        rotate_btn = self._make_icon_button(
            '\U0001F504', 'Rotate clockwise (Option/Alt+click for counter-clockwise)',
            self.theme_colors['text'],
        )
        # Unlike the thumbnail's right-click gesture, either mouse button
        # rotates the same way here -- only Option/Alt picks the direction,
        # so there's nothing to remember about which button does what on
        # the button itself.
        rotate_btn.clicked.connect(lambda _, img=img: self.rotate_image(
            img, not bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.AltModifier)
        ))
        rotate_btn.rightClicked.connect(lambda clockwise, img=img: self.rotate_image(img, clockwise))
        info_grid.addWidget(rename_btn, 0, 0)
        info_grid.addWidget(name_label, 0, 1)
        info_grid.addWidget(rotate_btn, 0, 2)
        img['_name_label'] = name_label

        zoom_btn = self._make_icon_button('\U0001F50E', 'View full size', self.theme_colors['text'])
        zoom_btn.clicked.connect(lambda _, img=img: self.show_full_res(img))
        dims_label = QLabel(f"{meta.get('width', '?')} x {meta.get('height', '?')}")
        dims_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dims_label.setFont(QFont(SIZE_FONT_FAMILY, 10))
        dims_label.setStyleSheet(f"color: {self.theme_colors['secondary_text']};")
        copy_btn = self._make_icon_button('\U0001F4CB', 'Copy image to clipboard', self.theme_colors['text'])
        copy_btn.clicked.connect(lambda _, img=img: self.copy_image(img))
        info_grid.addWidget(zoom_btn, 1, 0)
        info_grid.addWidget(dims_label, 1, 1)
        info_grid.addWidget(copy_btn, 1, 2)
        img['_dims_label'] = dims_label

        v.addLayout(info_grid)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"color: {self.theme_colors['unselected_border']};")
        v.addWidget(divider)

        img['_card'] = card
        self._apply_card_style(img)

        return card

    def _make_icon_button(self, glyph, tooltip, color):
        btn = IconButton(glyph)
        btn.setFixedSize(22, 22)
        btn.setToolTip(tooltip)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setStyleSheet(
            f'QPushButton {{ border: none; background: transparent; color: {color}; font-size: 12px; border-radius: 4px; }}'
            'QPushButton:hover { background: rgba(127, 127, 127, 0.25); }'
        )
        return btn

    def _apply_card_style(self, img):
        card = img.get('_card')
        if not card:
            return
        c = self.theme_colors
        if img.get('selected', True):
            card.setStyleSheet(
                f"#imageCard {{ border: 2px solid {c['selected_border']}; background: {c['selected_bg']}; border-radius: 8px; }}"
            )
        else:
            card.setStyleSheet(
                f"#imageCard {{ border: 1px solid {c['unselected_border']}; background: {c['unselected_bg']}; border-radius: 8px; }}"
            )

    def handle_thumb_clicked(self, img, shift_held):
        idx = img['_idx']
        if shift_held and self._selection_anchor_idx is not None:
            # Range-select from the last plain-clicked image to this one,
            # inclusive; the anchor itself doesn't move, so repeated
            # shift-clicks extend/shrink relative to that original click.
            lo, hi = sorted((self._selection_anchor_idx, idx))
            for i in range(lo, hi + 1):
                other = self.images[i]
                other['selected'] = True
                self._apply_card_style(other)
        else:
            img['selected'] = not img.get('selected', False)
            self._apply_card_style(img)
            self._selection_anchor_idx = idx

    def select_all(self):
        for img in self.images:
            img['selected'] = True
            self._apply_card_style(img)

    def select_none(self):
        for img in self.images:
            img['selected'] = False
            self._apply_card_style(img)

    def rename_image(self, img):
        new_name, ok = QInputDialog.getText(self, 'Rename Image', 'File name:', text=img['save_name'])
        if not ok:
            return
        new_name = new_name.strip()
        if new_name:
            img['save_name'] = new_name
            img['_name_label'].setText(new_name)

    def rotate_image(self, img, clockwise=True):
        transpose = Image.Transpose.ROTATE_270 if clockwise else Image.Transpose.ROTATE_90
        try:
            with Image.open(img['orig_path']) as im:
                rotated = im.transpose(transpose)
                rotated.save(img['orig_path'])
            with Image.open(img['orig_path']) as im:
                trimmed = pe.trim_whitespace(im)
                thumb = trimmed.copy()
            thumb.thumbnail((THUMB_SIZE, THUMB_SIZE))
            thumb.save(img['thumb_path'], 'PNG')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Could not rotate image: {e}')
            return

        meta = img['meta']
        w, h = meta.get('width'), meta.get('height')
        if isinstance(w, int) and isinstance(h, int):
            meta['width'], meta['height'] = h, w
            img['_dims_label'].setText(f"{h} x {w}")

        img['_thumb_label'].setPixmap(pil_to_pixmap(thumb))

    def show_full_res(self, img):
        orig_path = img['orig_path']
        if not os.path.exists(orig_path):
            QMessageBox.critical(self, 'Error', 'Image file not found.')
            return
        dlg = FullImageDialog(self, orig_path, img['meta'], img['filename'])
        dlg.exec()

    def copy_image(self, img):
        try:
            with Image.open(img['orig_path']) as im:
                QApplication.clipboard().setPixmap(pil_to_pixmap(im))
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Could not copy image: {e}')

    # --- Saving ---
    def save_selected(self):
        if not self.tmpdir or not os.path.exists(self.tmpdir):
            QMessageBox.critical(self, 'No Images', 'No images to save. Please open a PDF first.')
            return
        selected = [img for img in self.images if img.get('selected', True)]
        if not selected:
            QMessageBox.information(self, 'No Selection', 'No images selected.')
            return
        outdir = QFileDialog.getExistingDirectory(self, 'Select output folder')
        if not outdir:
            return
        export_fmt = 'WEBP' if self.rb_webp.isChecked() else 'PNG'
        kept = 0
        name_counts = {}
        for img in selected:
            base_name = img.get('save_name') or img['filename']
            name = base_name
            if name in name_counts:
                name_counts[name] += 1
                name = f"{base_name}-{name_counts[base_name]}"
            else:
                name_counts[name] = 0
            out_path = os.path.join(outdir, f"{name}.{export_fmt.lower()}")
            try:
                with Image.open(img['orig_path']) as pil_img:
                    pil_img.save(out_path, export_fmt)
                kept += 1
            except Exception as e:
                print(f"[WARN] Failed to save {img['orig_path']}: {e}")
        outdir_url = QUrl.fromLocalFile(outdir).toString()
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle('Done')
        msg.setText(f'Saved {kept} images to <a href="{outdir_url}">{outdir}</a>')
        for label in msg.findChildren(QLabel):
            label.setOpenExternalLinks(True)
        msg.exec()

    def closeEvent(self, event):
        if self.tmpdir and os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(ICON_PATH))
    load_bundled_fonts()
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
