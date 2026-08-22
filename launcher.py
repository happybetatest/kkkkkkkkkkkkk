import hashlib
import json
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
import certifi
from PySide6.QtCore import QThread, Signal, QTimer, Qt
from PySide6.QtWidgets import (
    QApplication, QLabel, QMainWindow, QMessageBox, QProgressBar,
    QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QPushButton, QFrame
)

from keyauth_helper import KeyAuthClient, load_saved_key, save_key, get_hwid


REPOSITORY = "happybetatest/kkkkkkkkkkkkk"
RELEASE_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
MANIFEST_ASSET = "release-manifest.json"
PACKAGE_ASSET = "FiveM-Farming-Package.zip"
APP_EXE = "FiveM-Farming-Macro.exe"
APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "FiveM-Farming")
VERSION_FILE = os.path.join(APP_DIR, ".installed-version.json")
USER_AGENT = "FiveM-Farming-Launcher/1.0"
HTTPS_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def request_bytes(url, timeout=30):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout, context=HTTPS_CONTEXT) as response:
        return response.read()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().lower()


def safe_extract(archive, destination):
    destination_abs = os.path.abspath(destination)
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            target = os.path.abspath(os.path.join(destination_abs, member.filename))
            if os.path.commonpath([destination_abs, target]) != destination_abs:
                raise ValueError("Unsafe path in update package")
        zipped.extractall(destination_abs)


class LicenseWorker(QThread):
    finished = Signal(bool, str, dict)

    def __init__(self, key):
        super().__init__()
        self.key = key

    def run(self):
        client = KeyAuthClient()
        success, message, info = client.verify_license(self.key)
        self.finished.emit(success, message, info)


class UpdateWorker(QThread):
    status = Signal(str, str, int)
    failed = Signal(str)
    ready = Signal(str)

    def get_installed_version(self):
        try:
            with open(VERSION_FILE, "r", encoding="utf-8") as stream:
                return str(json.load(stream).get("version", ""))
        except Exception:
            return ""

    def update_and_run(self):
        try:
            release = json.loads(request_bytes(RELEASE_API, timeout=15).decode("utf-8"))
            assets = {asset["name"]: asset["browser_download_url"] for asset in release.get("assets", [])}
            if MANIFEST_ASSET not in assets or PACKAGE_ASSET not in assets:
                raise RuntimeError("รีลีสล่าสุดมีไฟล์อัปเดตไม่ครบ")

            manifest = json.loads(request_bytes(assets[MANIFEST_ASSET], timeout=15).decode("utf-8"))
            remote_version = str(manifest["version"])
            expected_hash = str(manifest["package_sha256"]).lower()
            installed_version = self.get_installed_version()
            app_path = os.path.join(APP_DIR, APP_EXE)

            if installed_version != remote_version or not os.path.isfile(app_path):
                self.status.emit(
                    f"กำลังบังคับอัปเดตเป็นเวอร์ชัน {remote_version}",
                    "กำลังดาวน์โหลดแพ็กเกจล่าสุด…",
                    10,
                )
                os.makedirs(APP_DIR, exist_ok=True)
                with tempfile.TemporaryDirectory(prefix="fivem-update-") as temporary:
                    archive_path = os.path.join(temporary, PACKAGE_ASSET)
                    package = request_bytes(assets[PACKAGE_ASSET], timeout=120)
                    with open(archive_path, "wb") as stream:
                        stream.write(package)
                    self.status.emit(
                        f"กำลังบังคับอัปเดตเป็นเวอร์ชัน {remote_version}",
                        "กำลังตรวจสอบความถูกต้องของไฟล์…",
                        65,
                    )
                    actual_hash = sha256_file(archive_path)
                    if actual_hash != expected_hash:
                        raise RuntimeError("SHA-256 ของไฟล์อัปเดตไม่ตรง")

                    staging = os.path.join(temporary, "staging")
                    safe_extract(archive_path, staging)
                    staged_app = os.path.join(staging, APP_EXE)
                    if not os.path.isfile(staged_app):
                        raise RuntimeError("ไม่พบโปรแกรมหลักในแพ็กเกจ")

                    self.status.emit(
                        f"กำลังบังคับอัปเดตเป็นเวอร์ชัน {remote_version}",
                        "กำลังติดตั้งไฟล์เวอร์ชันใหม่…",
                        85,
                    )
                    for name in (APP_EXE, "config.json", "templates", "keyauth_helper.py"):
                        source = os.path.join(staging, name)
                        target = os.path.join(APP_DIR, name)
                        if not os.path.exists(source):
                            continue
                        if name == "config.json" and os.path.isfile(target):
                            continue
                        if os.path.isdir(source):
                            if os.path.isdir(target):
                                shutil.rmtree(target)
                            shutil.copytree(source, target)
                        else:
                            shutil.copy2(source, target)

                    with open(VERSION_FILE, "w", encoding="utf-8") as stream:
                        json.dump({"version": remote_version}, stream)

            self.status.emit(
                f"เวอร์ชัน {remote_version} พร้อมใช้งาน",
                "กำลังเปิดมาโคร…",
                100,
            )
            self.ready.emit(os.path.join(APP_DIR, APP_EXE))
        except Exception as error:
            self.failed.emit(str(error))

    def run(self):
        self.update_and_run()


class LauncherWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FiveM Farming Launcher")
        self.setFixedSize(520, 290)
        self.setStyleSheet(
            "QMainWindow, QWidget { background: #f8fafc; font-family: 'Segoe UI', Tahoma, sans-serif; }"
            "QLabel { color: #0f172a; }"
            "QProgressBar { height: 18px; text-align: center; border-radius: 9px; background: #e2e8f0; }"
            "QProgressBar::chunk { background: #10b981; border-radius: 9px; }"
            "QLineEdit { padding: 8px 12px; border: 1.5px solid #cbd5e1; border-radius: 6px; background: white; font-size: 13px; color: #1e293b; }"
            "QLineEdit:focus { border-color: #0ea5e9; }"
            "QPushButton { padding: 8px 16px; border-radius: 6px; font-weight: bold; font-size: 13px; }"
            "QPushButton#btn_primary { background: #0ea5e9; color: white; border: none; }"
            "QPushButton#btn_primary:hover { background: #0284c7; }"
            "QPushButton#btn_secondary { background: #e2e8f0; color: #334155; border: none; }"
            "QPushButton#btn_secondary:hover { background: #cbd5e1; }"
        )

        self.central = QWidget()
        self.layout = QVBoxLayout(self.central)
        self.layout.setContentsMargins(28, 24, 28, 24)
        self.layout.setSpacing(14)
        self.setCentralWidget(self.central)

        # Progress / Status View Components
        self.title_label = QLabel("กำลังตรวจสอบสิทธิ์การใช้งาน (KeyAuth)…")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a;")
        self.detail_label = QLabel("กำลังเชื่อมต่อเซิร์ฟเวอร์...")
        self.detail_label.setStyleSheet("font-size: 12px; color: #64748b;")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)

        # License Input View Components
        self.key_container = QWidget()
        key_layout = QVBoxLayout(self.key_container)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.setSpacing(10)

        hwid_row = QHBoxLayout()
        hwid_str = get_hwid()[:18] + "..."
        hwid_lbl = QLabel(f"รหัสเครื่อง (HWID): <b style='color:#0ea5e9;'>{hwid_str}</b>")
        hwid_lbl.setStyleSheet("font-size: 11px; color: #475569;")
        btn_copy_hwid = QPushButton("คัดลอก HWID")
        btn_copy_hwid.setObjectName("btn_secondary")
        btn_copy_hwid.setFixedHeight(26)
        btn_copy_hwid.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        btn_copy_hwid.clicked.connect(self.copy_hwid)
        hwid_row.addWidget(hwid_lbl)
        hwid_row.addStretch()
        hwid_row.addWidget(btn_copy_hwid)
        key_layout.addLayout(hwid_row)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("กรอก License Key ของคุณ...")
        key_layout.addWidget(self.key_input)

        btn_row = QHBoxLayout()
        self.btn_activate = QPushButton("ยืนยัน Key (Activate)")
        self.btn_activate.setObjectName("btn_primary")
        self.btn_activate.clicked.connect(self.on_activate_clicked)
        btn_row.addWidget(self.btn_activate)
        key_layout.addLayout(btn_row)

        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.progress)
        self.layout.addWidget(self.key_container)
        self.layout.addWidget(self.detail_label)

        self.key_container.hide()
        self.worker = None
        self.license_worker = None

        QTimer.singleShot(100, self.check_saved_license)

    def copy_hwid(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(get_hwid())
        self.detail_label.setText("คัดลอก HWID ไปยังคลิปบอร์ดแล้ว!")
        self.detail_label.setStyleSheet("font-size: 12px; color: #10b981;")

    def check_saved_license(self):
        saved_key = load_saved_key()
        if saved_key:
            self.title_label.setText("กำลังตรวจสอบ License Key...")
            self.detail_label.setText("เชื่อมต่อระบบ KeyAuth...")
            self.progress.setValue(30)
            self.verify_key(saved_key)
        else:
            self.show_key_input_screen("กรุณากรอก License Key เพื่อเริ่มใช้งาน")

    def show_key_input_screen(self, msg=""):
        self.progress.hide()
        self.key_container.show()
        self.title_label.setText("🔑 ยืนยันสิทธิ์การใช้งาน (License Key)")
        if msg:
            self.detail_label.setText(msg)
            self.detail_label.setStyleSheet("font-size: 12px; color: #ef4444;")
        else:
            self.detail_label.setText("ใส่ License Key ที่ได้รับจากผู้ขาย")
            self.detail_label.setStyleSheet("font-size: 12px; color: #64748b;")

    def on_activate_clicked(self):
        key = self.key_input.text().strip()
        if not key:
            self.detail_label.setText("กรุณากรอก License Key")
            self.detail_label.setStyleSheet("font-size: 12px; color: #ef4444;")
            return

        self.btn_activate.setEnabled(False)
        self.btn_activate.setText("กำลังตรวจสอบ...")
        self.detail_label.setText("กำลังติดต่อเซิร์ฟเวอร์ KeyAuth...")
        self.detail_label.setStyleSheet("font-size: 12px; color: #0ea5e9;")
        self.verify_key(key)

    def verify_key(self, key):
        self.license_worker = LicenseWorker(key)
        self.license_worker.finished.connect(self.on_license_result)
        self.license_worker.start()

    def on_license_result(self, success, message, info):
        self.btn_activate.setEnabled(True)
        self.btn_activate.setText("ยืนยัน Key (Activate)")

        if success:
            expiry = info.get("expiry", "ไม่ระบุ")
            save_key(info.get("key", ""))
            self.key_container.hide()
            self.progress.show()
            self.progress.setValue(100)
            self.title_label.setText("✅ ยืนยันสิทธิ์สำเร็จ!")
            self.detail_label.setText(f"อายุการใช้งาน: {expiry}")
            self.detail_label.setStyleSheet("font-size: 12px; color: #10b981; font-weight: bold;")
            QTimer.singleShot(800, self.start_update)
        else:
            self.show_key_input_screen(f"❌ {message}")

    def start_update(self):
        self.worker = UpdateWorker()
        self.worker.status.connect(self.set_status)
        self.worker.failed.connect(self.show_failure)
        self.worker.ready.connect(self.launch_app)
        self.worker.start()

    def set_status(self, title, detail, progress):
        self.title_label.setText(title)
        self.detail_label.setText(detail)
        self.detail_label.setStyleSheet("font-size: 12px; color: #64748b;")
        self.progress.setValue(progress)

    def show_failure(self, error):
        QMessageBox.critical(
            self,
            "อัปเดตไม่สำเร็จ",
            "ไม่สามารถอัปเดตเป็นเวอร์ชันล่าสุดได้ กรุณาตรวจสอบการเชื่อมต่ออินเทอร์เน็ต\n\n"
            f"รายละเอียด: {error}",
        )
        self.close()

    def launch_app(self, app_path):
        subprocess.Popen([app_path], cwd=APP_DIR)
        self.close()


if __name__ == "__main__":
    application = QApplication(sys.argv)
    window = LauncherWindow()
    window.show()
    sys.exit(application.exec())
