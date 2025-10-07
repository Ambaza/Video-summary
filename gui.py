import sys
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QFileDialog, QLabel,
    QLineEdit, QHBoxLayout, QGridLayout, QCheckBox, QComboBox
)
from PySide6.QtCore import Qt, QThread, Signal
from main import run_pipeline


class Worker(QThread):
    progress = Signal(str)
    done = Signal(str)

    def __init__(self, pdf_path, template_path, out_dir, api_keys, settings):
        super().__init__()
        self.pdf_path = pdf_path
        self.template_path = template_path
        self.out_dir = out_dir
        self.api_keys = api_keys
        self.settings = settings

    def run(self):
        try:
            video_path = run_pipeline(
                self.pdf_path,
                self.template_path,
                self.out_dir,
                self.api_keys,
                self.progress.emit,
                self.settings
            )
            self.done.emit(video_path)
        except Exception as e:
            self.done.emit(f"ERROR: {e}")


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF to Video Summary")
        self.resize(900, 540)

        # File paths
        self.pdf_path = ""
        self.template_path = ""
        self.out_dir = "project_runtime"
        self.music_path = ""

        # Labels
        self.pdf_label = QLabel("No PDF selected")
        self.tmpl_label = QLabel("No PPTX theme")
        self.out_label = QLabel("Output folder: project_runtime")
        self.music_label = QLabel("No music selected")

        # API keys
        self.openai_edit = QLineEdit()
        self.openai_edit.setPlaceholderText("OPENAI_API_KEY")

        self.eleven_key_edit = QLineEdit()
        self.eleven_key_edit.setPlaceholderText("ELEVENLABS_API_KEY")
        self.eleven_key_edit.setEchoMode(QLineEdit.Password)

        self.eleven_voice_edit = QLineEdit()
        self.eleven_voice_edit.setPlaceholderText("ELEVENLABS_VOICE_ID")

        # Feature toggles
        self.chk_anim = QCheckBox("Enable animation")
        self.chk_anim.setChecked(True)

        self.chk_emojis = QCheckBox("Enable emojis")
        self.chk_emojis.setChecked(True)

        self.chk_music = QCheckBox("Enable background music")
        self.chk_music.setChecked(False)

        # Buttons
        btn_pdf = QPushButton("Choose PDF")
        btn_pdf.clicked.connect(self.pick_pdf)

        btn_tmpl = QPushButton("Choose PPTX Theme (optional)")
        btn_tmpl.clicked.connect(self.pick_template)

        btn_out = QPushButton("Choose Output Folder")
        btn_out.clicked.connect(self.pick_out)

        btn_music = QPushButton("Choose Music")
        btn_music.clicked.connect(self.pick_music)

        btn_run = QPushButton("Generate Video")
        btn_run.clicked.connect(self.run)

        # Dropdowns
        self.cbo_profile = QComboBox()
        self.cbo_profile.addItems(["minimal", "subtle", "lively"])
        self.cbo_profile.setCurrentText("subtle")

        self.cbo_bullet = QComboBox()
        self.cbo_bullet.addItems(["fade", "slide", "fade-slide"])
        self.cbo_bullet.setCurrentText("fade-slide")

        # Logs
        self.log = QLabel("")
        self.log.setAlignment(Qt.AlignTop)
        self.log.setWordWrap(True)

        # Layout setup
        self._setup_layout(
            btn_pdf, btn_tmpl, btn_out, btn_music, btn_run
        )

    def _setup_layout(self, btn_pdf, btn_tmpl, btn_out, btn_music, btn_run):
        """Set up the main UI layout."""
        grid = QGridLayout()
        grid.addWidget(QLabel("PDF:"), 0, 0)
        grid.addWidget(self.pdf_label, 0, 1)
        grid.addWidget(btn_pdf, 0, 2)

        grid.addWidget(QLabel("Theme:"), 1, 0)
        grid.addWidget(self.tmpl_label, 1, 1)
        grid.addWidget(btn_tmpl, 1, 2)

        grid.addWidget(QLabel("Output:"), 2, 0)
        grid.addWidget(self.out_label, 2, 1)
        grid.addWidget(btn_out, 2, 2)

        keys_layout = QHBoxLayout()
        keys_layout.addWidget(self.openai_edit)
        keys_layout.addWidget(self.eleven_key_edit)
        keys_layout.addWidget(self.eleven_voice_edit)

        feat_grid = QGridLayout()
        feat_grid.addWidget(self.chk_anim, 0, 0)
        feat_grid.addWidget(self.chk_emojis, 0, 1)
        feat_grid.addWidget(self.chk_music, 0, 2)
        feat_grid.addWidget(QLabel("Effect profile:"), 1, 0)
        feat_grid.addWidget(self.cbo_profile, 1, 1)
        feat_grid.addWidget(QLabel("Bullet reveal:"), 1, 2)
        feat_grid.addWidget(self.cbo_bullet, 1, 3)
        feat_grid.addWidget(QLabel("Music:"), 2, 0)
        feat_grid.addWidget(self.music_label, 2, 1)
        feat_grid.addWidget(btn_music, 2, 2)

        layout = QVBoxLayout()
        layout.addLayout(grid)
        layout.addLayout(keys_layout)
        layout.addLayout(feat_grid)
        layout.addWidget(btn_run)
        layout.addWidget(self.log)
        self.setLayout(layout)

    def pick_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select PDF", "", "PDF Files (*.pdf)")
        if path:
            self.pdf_path = path
            self.pdf_label.setText(path)

    def pick_template(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select PPTX Template", "", "PPTX Files (*.pptx)")
        if path:
            self.template_path = path
            self.tmpl_label.setText(path)

    def pick_out(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if directory:
            self.out_dir = directory
            self.out_label.setText(f"Output folder: {directory}")

    def pick_music(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Music", "", "Audio Files (*.mp3 *.wav *.m4a)"
        )
        if path:
            self.music_path = path
            self.music_label.setText(os.path.basename(path))
            self.chk_music.setChecked(True)

    def run(self):
        api_keys = {
            "OPENAI_API_KEY": self.openai_edit.text().strip(),
            "ELEVENLABS_API_KEY": self.eleven_key_edit.text().strip(),
            "ELEVENLABS_VOICE_ID": self.eleven_voice_edit.text().strip(),
        }

        if not self.pdf_path:
            self.on_progress("Please select a PDF.")
            return

        settings = {
            "enable_animation": self.chk_anim.isChecked(),
            "enable_emojis": self.chk_emojis.isChecked(),
            "enable_music": self.chk_music.isChecked(),
            "bg_music_path": self.music_path,
            "effect_profile": self.cbo_profile.currentText(),
            "bullet_reveal": self.cbo_bullet.currentText(),
        }

        self.worker = Worker(self.pdf_path, self.template_path, self.out_dir, api_keys, settings)
        self.worker.progress.connect(self.on_progress)
        self.worker.done.connect(self.on_done)
        self.worker.start()

    def on_progress(self, msg: str):
        text = self.log.text()
        new_text = text + ("\n" if text else "") + msg
        self.log.setText(new_text)

    def on_done(self, msg: str):
        self.on_progress("DONE: " + msg)


def main():
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
