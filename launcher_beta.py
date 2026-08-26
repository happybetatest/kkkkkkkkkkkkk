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
RELEASES_API = f"https://api.github.com/repos/{REPOSITORY}/releases"
LATEST_RELEASE_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
MANIFEST_ASSET = "beta-manifest.json"
PACKAGE_ASSET = "FiveM-Farming-Beta-Package.zip"
APP_EXE = "FiveM-Farming-Beta-Macro.exe"
APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "FiveM-Farming-Beta")
VERSION_FILE = os.path.join(APP_DIR, ".installed-version.json")
USER_AGENT = "FiveM-Farming-Beta-Launcher/1.0"
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

    def find_target_release(self):
        # 1. Try listing recent releases (supports Beta / Prereleases)
        try:
            releases_data = json.loads(request_bytes(RELEASES_API, timeout=15).decode("utf-8"))
            if isinstance(releases_data, list):
                for rel in releases_data:
                    assets = {asset["name"]: asset["browser_download_url"] for asset in rel.get("assets", [])}
                    if MANIFEST_ASSET in assets and PACKAGE_ASSET in assets:
                        return rel, assets
        except Exception:
            pass

        # 2. Fallback to latest standard release
        release = json.loads(request_bytes(LATEST_RELEASE_API, timeout=15).decode("utf-8"))
        assets = {asset["name"]: asset["browser_download_url"] for asset in release.get("assets", [])}
        return release, assets

    def update_and_run(self):
        try:
            release, assets = self.find_target_release()
            if MANIFEST_ASSET not in assets or PACKAGE_ASSET not in assets:
                raise RuntimeError("ไม่พบไฟล์อัปเดตสำหรับเวอร์ชัน Beta (beta-manifest.json)")

            manifest = json.loads(request_bytes(assets[MANIFEST_ASSET], timeout=15).decode("utf-8"))
            remote_version = str(manifest["version"])
            expected_hash = str(manifest["package_sha256"]).lower()
            installed_version = self.get_installed_version()
            app_path = os.path.join(APP_DIR, APP_EXE)

            if installed_version != remote_version or not os.path.isfile(app_path):
                self.status.emit(
                    f"กำลังอัปเดตเป็นเวอร์ชัน Beta {remote_version}",
                    "กำลังดาวน์โหลดแพ็กเกจ Beta ล่าสุด…",
                    10,
                )
                os.makedirs(APP_DIR, exist_ok=True)
                with tempfile.TemporaryDirectory(prefix="fivem-beta-update-") as temporary:
                    archive_path = os.path.join(temporary, PACKAGE_ASSET)
                    package = request_bytes(assets[PACKAGE_ASSET], timeout=120)
                    with open(archive_path, "wb") as stream:
                        stream.write(package)
                    self.status.emit(
                        f"กำลังอัปเดตเป็นเวอร์ชัน Beta {remote_version}",
                        "กำลังตรวจสอบความถูกต้องของไฟล์…",
                        65,
                    )
                    actual_hash = sha256_file(archive_path)
                    if actual_hash != expected_hash:
                        raise RuntimeError("SHA-256 ของไฟล์อัปเดต Beta ไม่ตรง")

                    staging = os.path.join(temporary, "staging")
                    safe_extract(archive_path, staging)
                    staged_app = os.path.join(staging, APP_EXE)
                    if not os.path.isfile(staged_app):
                        raise RuntimeError("ไม่พบโปรแกรมหลักในแพ็กเกจ Beta")

                    self.status.emit(
                        f"กำลังอัปเดตเป็นเวอร์ชัน Beta {remote_version}",
                        "กำลังติดตั้งไฟล์เวอร์ชัน Beta ใหม่…",
                        85,
                    )
                    for name in (APP_EXE, "config.json", "templates", "keyauth_helper.py", "discord_remote.py"):
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
                f"เวอร์ชัน Beta {remote_version} พร้อมใช้งาน",
                "กำลังเปิดมาโคร Beta…",
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
        self.setWindowTitle("FiveM Farming Launcher (Beta / Test)")
        self.setFixedSize(540, 300)
        self.setStyleSheet(
            "QMainWindow, QWidget { background: #f8fafc; font-family: 'Segoe UI', Tahoma, sans-serif; }"
            "QLabel { color: #0f172a; }"
            "QProgressBar { height: 18px; text-align: center; border-radius: 9px; background: #e2e8f0; }"
            "QProgressBar::chunk { background: #8b5cf6; border-radius: 9px; }"
            "QLineEdit { padding: 8px 12px; border: 1.5px solid #cbd5e1; border-radius: 6px; background: white; font-size: 13px; color: #1e293b; }"
            "QLineEdit:focus { border-color: #8b5cf6; }"
            "QPushButton { padding: 8px 16px; border-radius: 6px; font-weight: bold; font-size: 13px; }"
            "QPushButton#btn_primary { background: #8b5cf6; color: white; border: none; }"
            "QPushButton#btn_primary:hover { background: #7c3aed; }"
            "QPushButton#btn_secondary { background: #e2e8f0; color: #334155; border: none; }"
            "QPushButton#btn_secondary:hover { background: #cbd5e1; }"
        )

        self.central = QWidget()
        self.layout = QVBoxLayout(self.central)
        self.layout.setContentsMargins(28, 24, 28, 24)
        self.layout.setSpacing(14)
        self.setCentralWidget(self.central)

        # Progress / Status View Components
        self.title_label = QLabel("กำลังตรวจสอบสิทธิ์การใช้งาน (Beta Channel)…")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #5b21b6;")
        self.detail_label = QLabel("กำลังเชื่อมต่อเซิร์ฟเวอร์...")
        self.detail_label.setStyleSheet("font-size: 12px; color: #64748b;")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)

        # License Input View Components
        self.key_container = QWidget()
        key_layout = QVBoxLayout(self.key_container)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.setSpacing(10)

        self.hwid_label = QLabel(f"HWID: {get_hwid()}")
        self.hwid_label.setStyleSheet("font-size: 11px; color: #94a3b8;")

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("กรอก License Key สำหรับเวอร์ชัน Beta...")

        btn_layout = QHBoxLayout()
        self.btn_submit = QPushButton("เข้าสู่ระบบ (Beta)")
        self.btn_submit.setObjectName("btn_primary")
        self.btn_submit.clicked.connect(self.on_submit_key)

        self.btn_exit = QPushButton("ปิด")
        self.btn_exit.setObjectName("btn_secondary")
        self.btn_exit.clicked.connect(self.close)

        btn_layout.addWidget(self.btn_submit)
        btn_layout.addWidget(self.btn_exit)

        key_layout.addWidget(self.hwid_label)
        key_layout.addWidget(self.key_input)
        key_layout.addLayout(btn_layout)
        self.key_container.hide()

        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.detail_label)
        self.layout.addWidget(self.progress)
        self.layout.addWidget(self.key_container)

        self.license_worker = None
        self.update_worker = None

        QTimer.singleShot(200, self.start_auth_check)

    def start_auth_check(self):
        saved_key = load_saved_key()
        if saved_key:
            self.title_label.setText("กำลังตรวจสอบสิทธิ์การใช้งาน (Beta)…")
            self.detail_label.setText("กำลังยืนยันคีย์กับระบบ KeyAuth...")
            self.progress.setValue(20)
            self.verify_key(saved_key)
        else:
            self.show_key_input()

    def show_key_input(self, error_msg=""):
        self.title_label.setText("กรุณากรอก License Key (Beta Channel)")
        if error_msg:
            self.detail_label.setText(f"❌ {error_msg}")
            self.detail_label.setStyleSheet("font-size: 12px; color: #ef4444; font-weight: bold;")
        else:
            self.detail_label.setText("กรอกคีย์เพื่อปลดล็อกและทดสอบเวอร์ชัน Beta")
            self.detail_label.setStyleSheet("font-size: 12px; color: #64748b;")

        self.progress.hide()
        self.key_container.show()
        self.key_input.setFocus()

    def on_submit_key(self):
        key = self.key_input.text().strip()
        if not key:
            self.detail_label.setText("❌ กรุณากรอกคีย์ก่อนกดยืนยัน")
            self.detail_label.setStyleSheet("font-size: 12px; color: #ef4444;")
            return

        self.btn_submit.setEnabled(False)
        self.btn_submit.setText("กำลังตรวจสอบ...")
        self.key_container.hide()
        self.progress.show()
        self.progress.setValue(25)
        self.title_label.setText("กำลังตรวจสอบ License Key…")
        self.detail_label.setText("กำลังยืนยันข้อมูลกับเซิร์ฟเวอร์...")
        self.detail_label.setStyleSheet("font-size: 12px; color: #64748b;")

        self.verify_key(key)

    def verify_key(self, key):
        self.license_worker = LicenseWorker(key)
        self.license_worker.finished.connect(self.on_auth_finished)
        self.license_worker.start()

    def on_auth_finished(self, success, message, info):
        self.btn_submit.setEnabled(True)
        self.btn_submit.setText("เข้าสู่ระบบ (Beta)")

        if success:
            save_key(self.license_worker.key)
            self.progress.setValue(50)
            expiry = info.get("expiry", "ไม่ระบุ")
            self.title_label.setText("สิทธิ์การใช้งานถูกต้อง (Beta Active)")
            self.detail_label.setText(f"ยินดีต้อนรับ! วันหมดอายุ: {expiry}")
            self.detail_label.setStyleSheet("font-size: 12px; color: #10b981; font-weight: bold;")

            QTimer.singleShot(800, self.start_update_check)
        else:
            self.show_key_input(error_msg=message)

    def start_update_check(self):
        self.title_label.setText("กำลังตรวจสอบการอัปเดตเวอร์ชัน Beta…")
        self.detail_label.setText("กำลังเชื่อมต่อเซิร์ฟเวอร์ GitHub...")
        self.detail_label.setStyleSheet("font-size: 12px; color: #64748b;")
        self.progress.setValue(60)

        self.update_worker = UpdateWorker()
        self.update_worker.status.connect(self.on_update_status)
        self.update_worker.failed.connect(self.on_update_failed)
        self.update_worker.ready.connect(self.on_update_ready)
        self.update_worker.start()

    def on_update_status(self, title, detail, progress_value):
        self.title_label.setText(title)
        self.detail_label.setText(detail)
        self.progress.setValue(progress_value)

    def on_update_failed(self, error):
        self.title_label.setText("การอัปเดตล้มเหลว")
        self.detail_label.setText(error)
        self.detail_label.setStyleSheet("font-size: 12px; color: #ef4444; font-weight: bold;")
        QMessageBox.critical(self, "FiveM Farming Beta", f"เกิดข้อผิดพลาดในการตรวจสอบหรืออัปเดต:\n{error}")
        self.close()

    def on_update_ready(self, app_path):
        self.progress.setValue(100)
        QTimer.singleShot(400, lambda: self.launch_app(app_path))

    def launch_app(self, app_path):
        if not os.path.isfile(app_path):
            QMessageBox.critical(self, "FiveM Farming Beta", "ไม่พบไฟล์โปรแกรมหลัก")
            self.close()
            return

        subprocess.Popen([app_path], cwd=APP_DIR)
        self.close()


def main():
    app = QApplication(sys.argv)
    window = LauncherWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
