import sys
import os
import time
import ctypes
import json
import ssl
import urllib.request
import random
import numpy as np
import cv2
import win32gui
import win32ui
import win32con
import win32api
import win32process
import keyboard
import asyncio
import mimetypes
import threading
from uuid import uuid4

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    import certifi
    HTTPS_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:
    HTTPS_CONTEXT = ssl.create_default_context()

# Keep Qt screen coordinates, Win32 window coordinates, and captured pixels in
# the same (physical-pixel) coordinate space.  Without this, Windows display
# scaling can make a freshly cropped template differ from PrintWindow output.
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot, QTimer, QPoint, QRect
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QSlider, QTextEdit, QFrame, QGridLayout, 
    QGroupBox, QSystemTrayIcon, QMenu, QCheckBox, QTabWidget, QScrollArea,
    QComboBox, QLineEdit, QMessageBox, QProgressBar
)
from PySide6.QtGui import (
    QIcon, QAction, QColor, QFont, QPainter, QPen, QPixmap, QImage, QPalette
)

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def get_writable_path(filename):
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

CURRENT_APP_VERSION = "1.4.3"

def get_current_version():
    try:
        v_path = get_writable_path("version.json")
        if os.path.isfile(v_path):
            with open(v_path, "r", encoding="utf-8") as f:
                return json.load(f).get("version", CURRENT_APP_VERSION)
    except Exception:
        pass
    return CURRENT_APP_VERSION

def parse_ver(v_str):
    import re
    nums = re.findall(r'\d+', str(v_str))
    return tuple(map(int, nums)) if nums else (0, 0, 0)

class RealtimeUpdateWorker(QThread):
    check_finished = Signal(bool, str, str)  # has_update, remote_version, error_msg
    download_finished = Signal(bool, str)    # success, message

    def __init__(self, mode="check"):
        super().__init__()
        self.mode = mode

    def run(self):
        if self.mode == "check":
            self.do_check()
        elif self.mode == "download":
            self.do_download()

    def do_check(self):
        try:
            url = f"https://raw.githubusercontent.com/happybetatest/kkkkkkkkkkkkk/main/version.json?t={int(time.time())}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=6, context=HTTPS_CONTEXT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                remote_ver = str(data.get("version", "")).strip()
                cur_ver = get_current_version()
                has_update = parse_ver(remote_ver) > parse_ver(cur_ver)
                self.check_finished.emit(has_update, remote_ver, "")
        except Exception as e:
            self.check_finished.emit(False, "", str(e))

    def do_download(self):
        try:
            files_to_sync = [
                ("gui_macro.py", "https://raw.githubusercontent.com/happybetatest/kkkkkkkkkkkkk/main/gui_macro.py"),
                ("keyauth_helper.py", "https://raw.githubusercontent.com/happybetatest/kkkkkkkkkkkkk/main/keyauth_helper.py"),
                ("discord_remote.py", "https://raw.githubusercontent.com/happybetatest/kkkkkkkkkkkkk/main/discord_remote.py"),
                ("version.json", "https://raw.githubusercontent.com/happybetatest/kkkkkkkkkkkkk/main/version.json")
            ]
            app_dir = os.path.dirname(os.path.abspath(__file__))
            for filename, raw_url in files_to_sync:
                raw_url_timed = f"{raw_url}?t={int(time.time())}"
                req = urllib.request.Request(raw_url_timed, headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"})
                with urllib.request.urlopen(req, timeout=10, context=HTTPS_CONTEXT) as resp:
                    content = resp.read()

                target_path = os.path.join(app_dir, filename)
                with open(target_path, "wb") as f:
                    f.write(content)

                template_app_path = os.path.join(app_dir, "templates", "_app", filename)
                if os.path.exists(os.path.dirname(template_app_path)):
                    try:
                        with open(template_app_path, "wb") as f:
                            f.write(content)
                    except Exception:
                        pass
            self.download_finished.emit(True, "อัปเดตไฟล์สำเร็จเรียบร้อย กำลังเริ่มระบบใหม่...")
        except Exception as e:
            self.download_finished.emit(False, f"เกิดข้อผิดพลาดในการดาวน์โหลด: {e}")

def apply_fixed_light_theme(app):
    """Keep the app colors independent from the Windows light/dark setting."""
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#f8fafc"))
    palette.setColor(QPalette.WindowText, QColor("#334155"))
    palette.setColor(QPalette.Base, QColor("#ffffff"))
    palette.setColor(QPalette.AlternateBase, QColor("#f1f5f9"))
    palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipText, QColor("#334155"))
    palette.setColor(QPalette.Text, QColor("#334155"))
    palette.setColor(QPalette.Button, QColor("#ffffff"))
    palette.setColor(QPalette.ButtonText, QColor("#334155"))
    palette.setColor(QPalette.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.Link, QColor("#0d9488"))
    palette.setColor(QPalette.Highlight, QColor("#0d9488"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(
        QPalette.Disabled, QPalette.WindowText, QColor("#94a3b8")
    )
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#94a3b8"))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#94a3b8"))
    palette.setColor(QPalette.Disabled, QPalette.Base, QColor("#f1f5f9"))
    app.setPalette(palette)

def force_light_title_bar(window):
    """Prevent the native Windows title bar from following Dark Mode."""
    try:
        hwnd = int(window.winId())
        disabled = ctypes.c_int(0)
        for attribute in (20, 19):
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                attribute,
                ctypes.byref(disabled),
                ctypes.sizeof(disabled),
            )
            if result == 0:
                break
    except Exception:
        pass

# ==========================================
# HARDWARE-LEVEL SCANCODE KEYBOARD SENDER (SendInput API)
# ==========================================
class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort), ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_short), ("wParamH", ctypes.c_ushort)]

class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput), ("mi", MouseInput), ("hi", HardwareInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002

SCANCODES = {
    "esc": 0x01, "escape": 0x01,
    "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05, "5": 0x06, "6": 0x07, "7": 0x08, "8": 0x09, "9": 0x0A, "0": 0x0B,
    "-": 0x0C, "ข": 0x0C, "_": 0x0C, "=": 0x0D,
    "q": 0x10, "w": 0x11, "e": 0x12, "r": 0x13, "t": 0x14, "y": 0x15, "u": 0x16, "i": 0x17, "o": 0x18, "p": 0x19,
    "a": 0x1E, "s": 0x1F, "d": 0x20, "f": 0x21, "g": 0x22, "h": 0x23, "j": 0x24, "k": 0x25, "l": 0x26,
    "z": 0x2C, "x": 0x2D, "c": 0x2E, "v": 0x2F, "b": 0x30, "n": 0x31, "m": 0x32,
    "enter": 0x1C, "return": 0x1C, "space": 0x39, "backspace": 0x0E, "tab": 0x0F,
    "f1": 0x3B, "f2": 0x3C, "f3": 0x3D, "f4": 0x3E, "f5": 0x3F, "f6": 0x40,
    "f7": 0x41, "f8": 0x42, "f9": 0x43, "f10": 0x44, "f11": 0x57, "f12": 0x58,
    "up": (0x48, True), "down": (0x50, True), "left": (0x4B, True), "right": (0x4D, True),
}

def resolve_scancode(key_name):
    name = str(key_name).strip().lower()
    if name in SCANCODES:
        val = SCANCODES[name]
        if isinstance(val, tuple):
            return val
        return (val, False)
    if len(name) == 1:
        try:
            vk = ctypes.windll.user32.VkKeyScanW(ord(name[0])) & 0xFF
            sc = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
            if sc > 0:
                return (sc, False)
        except Exception:
            pass
    return (None, False)

def press_key(scancode, is_extended=False):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    flags = KEYEVENTF_SCANCODE
    if is_extended:
        flags |= KEYEVENTF_EXTENDEDKEY
    ii_.ki = KeyBdInput(0, scancode, flags, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def release_key(scancode, is_extended=False):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    flags = KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP
    if is_extended:
        flags |= KEYEVENTF_EXTENDEDKEY
    ii_.ki = KeyBdInput(0, scancode, flags, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def send_key_direct(key_name, duration=0.10):
    scancode, is_extended = resolve_scancode(key_name)
    if scancode is not None:
        press_key(scancode, is_extended)
        time.sleep(duration)
        release_key(scancode, is_extended)

def press_key_hold(key_name):
    scancode, is_extended = resolve_scancode(key_name)
    if scancode is not None:
        press_key(scancode, is_extended)

def release_key_hold(key_name):
    scancode, is_extended = resolve_scancode(key_name)
    if scancode is not None:
        release_key(scancode, is_extended)

# ==========================================
# DISCORD REMOTE CONTROL ENGINE (EMBEDDED)
# ==========================================
def send_discord_rest_message(bot_token, channel_id, content="", file_path=None, reply_to_message_id=None):
    """Send text message and/or file attachment via Discord REST API v10."""
    try:
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        headers = {
            "Authorization": f"Bot {bot_token}",
            "User-Agent": "FiveMFarmingRemote/1.3.4",
        }

        payload_json = {}
        if content:
            payload_json["content"] = content
        if reply_to_message_id:
            payload_json["message_reference"] = {
                "message_id": str(reply_to_message_id),
                "fail_if_not_exists": False
            }

        if file_path and os.path.isfile(file_path):
            boundary = f"----WebKitFormBoundary{uuid4().hex}"
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
            
            body = bytearray()
            # 1. Payload JSON part
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(b'Content-Disposition: form-data; name="payload_json"\r\n')
            body.extend(b"Content-Type: application/json\r\n\r\n")
            body.extend(json.dumps(payload_json).encode("utf-8"))
            body.extend(b"\r\n")

            # 2. File part
            filename = os.path.basename(file_path)
            content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
            with open(file_path, "rb") as f:
                file_bytes = f.read()

            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="files[0]"; filename="{filename}"\r\n'.encode("utf-8"))
            body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
            body.extend(file_bytes)
            body.extend(b"\r\n")
            body.extend(f"--{boundary}--\r\n".encode("utf-8"))

            req = urllib.request.Request(url, data=bytes(body), headers=headers, method="POST")
        else:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload_json).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        with urllib.request.urlopen(req, timeout=12, context=HTTPS_CONTEXT) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            return resp_data.get("id")
    except Exception as e:
        print(f"[Discord REST Error] {e}")
        return None

def delete_discord_rest_message(bot_token, channel_id, message_id):
    """Delete a message via Discord REST API."""
    try:
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
        headers = {
            "Authorization": f"Bot {bot_token}",
            "User-Agent": "FiveMFarmingRemote/1.3.4",
        }
        req = urllib.request.Request(url, headers=headers, method="DELETE")
        with urllib.request.urlopen(req, timeout=8, context=HTTPS_CONTEXT):
            pass
    except Exception:
        pass

class DiscordRemoteWorker(QObject):
    """Background worker managing the Discord Bot Gateway connection and commands."""

    status_signal = Signal(bool, str)          # (is_connected, bot_username_or_error)
    log_signal = Signal(str)                   # log message
    action_requested = Signal(str, object)     # (action_name, reply_callback_or_dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bot_token = ""
        self.admin_user_id = ""
        self.command_prefix = "!"
        self.bot_id = ""
        self.bot_name = "Bot"
        self.is_enabled = False
        self.is_running = False
        self.loop = None
        self.thread = None

    def configure(self, token, admin_id, enabled, prefix="!"):
        self.bot_token = str(token).strip()
        self.admin_user_id = str(admin_id).strip()
        self.is_enabled = bool(enabled)
        self.command_prefix = str(prefix).strip() or "!"

    def start_bot(self):
        if not self.bot_token:
            self.status_signal.emit(False, "ยังไม่ได้ใส่ Bot Token")
            return

        if self.is_running or (self.thread and self.thread.is_alive()):
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._run_gateway, daemon=True)
        self.thread.start()

    def stop_bot(self):
        self.is_running = False
        if self.loop and self.loop.is_running():
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except Exception:
                pass
        self.status_signal.emit(False, "ออฟไลน์")

    def _run_gateway(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._gateway_loop())
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        except Exception as e:
            if self.is_running:
                self.status_signal.emit(False, f"ข้อผิดพลาด: {e}")
                self.log_signal.emit(f"[Discord Remote] การเชื่อมต่อขัดข้อง: {e}")
        finally:
            try:
                # Cancel and collect all pending tasks
                pending = [t for t in asyncio.all_tasks(self.loop) if not t.done()]
                for task in pending:
                    task.cancel()
                if pending:
                    self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            except Exception:
                pass
            finally:
                try:
                    self.loop.close()
                except Exception:
                    pass
            self.is_running = False
            self.status_signal.emit(False, "ออฟไลน์")

    async def _gateway_loop(self):
        gateway_url = "wss://gateway.discord.gg/?v=10&encoding=json"
        
        while self.is_running:
            heartbeat_task = None
            try:
                if not AIOHTTP_AVAILABLE:
                    self.status_signal.emit(False, "จำเป็นต้องมี aiohttp")
                    return

                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(gateway_url, ssl=HTTPS_CONTEXT) as ws:
                        seq = None

                        async for msg in ws:
                            if not self.is_running:
                                break

                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                op = data.get("op")
                                d = data.get("d")
                                s = data.get("s")
                                t = data.get("t")

                                if s is not None:
                                    seq = s

                                # OP 10: HELLO -> Start Heartbeat & Identify
                                if op == 10:
                                    interval_ms = d.get("heartbeat_interval", 41250)
                                    if heartbeat_task and not heartbeat_task.done():
                                        heartbeat_task.cancel()
                                    heartbeat_task = asyncio.create_task(self._heartbeat(ws, interval_ms / 1000.0, seq))
                                    
                                    # Send Identify (Op 2)
                                    identify_payload = {
                                        "op": 2,
                                        "d": {
                                            "token": self.bot_token,
                                            "intents": 37377,
                                            "properties": {
                                                "os": sys.platform,
                                                "browser": "FiveM_Remote",
                                                "device": "FiveM_Remote"
                                            }
                                        }
                                    }
                                    await ws.send_str(json.dumps(identify_payload))

                                # OP 11: Heartbeat ACK
                                elif op == 11:
                                    pass

                                # OP 0: Dispatch Events
                                elif op == 0:
                                    if t == "READY":
                                        username = d.get("user", {}).get("username", "Bot")
                                        self.bot_id = str(d.get("user", {}).get("id", ""))
                                        self.bot_name = username
                                        self.status_signal.emit(True, f"ออนไลน์: {username}")
                                        self.log_signal.emit(f"[Discord Remote] เชื่อมต่อบอทสำเร็จ: {username} (Prefix: '{self.command_prefix}')")

                                    elif t == "MESSAGE_CREATE":
                                        asyncio.create_task(self._handle_message(d))

                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break

            except asyncio.CancelledError:
                break
            except Exception as conn_err:
                if self.is_running:
                    self.status_signal.emit(False, f"กำลังต่อใหม่ ({conn_err})")
                    self.log_signal.emit(f"[Discord Remote] หลุดการเชื่อมต่อ กำลังเชื่อมต่อใหม่ใน 5 วินาที: {conn_err}")
                    try:
                        await asyncio.sleep(5.0)
                    except asyncio.CancelledError:
                        break
            finally:
                if heartbeat_task and not heartbeat_task.done():
                    heartbeat_task.cancel()

    async def _heartbeat(self, ws, interval_seconds, current_seq):
        try:
            while self.is_running and not ws.closed:
                await asyncio.sleep(interval_seconds)
                if ws.closed:
                    break
                hb_payload = {"op": 1, "d": current_seq}
                await ws.send_str(json.dumps(hb_payload))
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def _handle_message(self, d):
        author = d.get("author", {})
        if author.get("bot"):
            return

        sender_id = str(author.get("id", "")).strip()
        sender_name = str(author.get("username", "")).strip()
        sender_discrim = str(author.get("discriminator", "0")).strip()
        sender_tag = f"{sender_name}#{sender_discrim}" if sender_discrim != "0" else sender_name
        sender_global = str(author.get("global_name", "")).strip()
        channel_id = str(d.get("channel_id", "")).strip()
        msg_id = str(d.get("id", "")).strip()
        content = str(d.get("content", "")).strip()

        if not content:
            return

        # Security Whitelist check: only accept commands from Admin User ID or username
        if self.admin_user_id:
            admin_target = self.admin_user_id.lower().strip()
            # Match against ID, tag (Bothxp#9286), username (bothxp), or global display name
            matched = (
                sender_id == admin_target or
                sender_name.lower() == admin_target or
                sender_tag.lower() == admin_target or
                sender_global.lower() == admin_target
            )
            if not matched:
                return

        content_clean = content.strip()
        bot_mention = f"<@{self.bot_id}>" if self.bot_id else None
        bot_mention_nick = f"<@!{self.bot_id}>" if self.bot_id else None
        is_direct_message = bool(d.get("guild_id") is None)

        matched_prefix = False
        extracted_cmd = ""

        # 1. Mention check: @BOT DIS check or @Bothxp check
        if bot_mention and content_clean.startswith(bot_mention):
            matched_prefix = True
            extracted_cmd = content_clean[len(bot_mention):].strip()
        elif bot_mention_nick and content_clean.startswith(bot_mention_nick):
            matched_prefix = True
            extracted_cmd = content_clean[len(bot_mention_nick):].strip()
        # 2. Configured Prefix check: e.g. prefix is "!" or "?" or "!2"
        elif content_clean.lower().startswith(self.command_prefix.lower()):
            matched_prefix = True
            extracted_cmd = content_clean[len(self.command_prefix):].strip()
        # 3. Direct Message (DM) to this specific bot: always accepts commands
        elif is_direct_message:
            matched_prefix = True
            extracted_cmd = content_clean
            if extracted_cmd.startswith("!") or extracted_cmd.startswith("/") or extracted_cmd.startswith("?"):
                extracted_cmd = extracted_cmd[1:].strip()

        if not matched_prefix or not extracted_cmd:
            return

        parts = extracted_cmd.split(maxsplit=1)
        main_cmd = parts[0].lower() if parts else ""
        arg = parts[1].strip() if len(parts) > 1 else ""
        pfx = self.command_prefix
        tag_prefix = f"🤖 **[{self.bot_name}]**"

        # 1. HELP COMMAND
        if main_cmd in ("help", "คำสั่ง", "เมนู", "menu"):
            help_text = (
                f"🎮 **FiveM Farming [{self.bot_name}] — เมนูคำสั่งควบคุมระยะไกล**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🚀 `{pfx}เข้าเกม [IP/cfx]` : **สั่งเปิด FiveM และเชื่อมต่อเข้าเซิร์ฟเวอร์ทันที**\n"
                f"📍 `{pfx}map1` : **เปิดแผนที่ (P) และปักหมุดจุด Mine Job ให้อัตโนมัติ**\n"
                f"🚗 `{pfx}map2` : **เปิดแผนที่ (P) และปักหมุดพาวรถ (Car Pound 2/2) ให้อัตโนมัติ**\n"
                f"🚙 `{pfx}car` หรือ `{pfx}เบิกรถ` : **กด E ค้าง 2วิ ➔ เลือกรถ ➔ กด Select Vehicle**\n"
                f"🚘 `{pfx}drive` หรือ `{pfx}ขับออโต้` : **กด '-' (ข) ➔ คลิกเปิด Auto Drive อัตโนมัติ**\n"
                f"📦 `{pfx}check` หรือ `{pfx}bag` : **เปิดกระเป๋า ตรวจเช็คทอง/เพชร และถ่ายรูปส่งกลับมา**\n"
                f"🚪 `{pfx}close` หรือ `{pfx}ปิดกระเป๋า` หรือ `{pfx}t` : **สั่งกด T เพื่อปิดกระเป๋าทันที**\n"
                f"🗑️ `{pfx}discard` หรือ `{pfx}ทิ้งทอง` : **สั่งทิ้งทอง กดยืนยัน และกลับไปเริ่มฟาร์มต่อให้อัตโนมัติ**\n"
                f"📸 `{pfx}screen` : ถ่ายภาพหน้าจอ FiveM สดๆ\n"
                f"📊 `{pfx}status` : ตรวจสอบสถานะการทำงานปัจจุบัน\n"
                f"🟢 `{pfx}start` : เริ่มการทำงานของบอท (F9)\n"
                f"🔴 `{pfx}stop` : หยุดพักบอทชั่วคราว (F9)\n"
                f"🍗 `{pfx}feed` : สั่งให้ตัวละครกินน้ำ (ช่อง 6) และอาหาร (ช่อง 7)\n"
                f"💎 `{pfx}store` : สั่งให้เริ่มกระบวนการเก็บเพชรลงรถ\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"*Prefix ปัจจุบัน: `{pfx}` (หรือแท็ก @{self.bot_name} ได้โดยตรง) 🔒*"
            )
            send_discord_rest_message(self.bot_token, channel_id, help_text, reply_to_message_id=msg_id)
            return

        # 2. CONNECT / JOIN FIVEM SERVER
        if main_cmd in ("connect", "join", "เข้าเกม", "เข้าเกมส์", "เข้าเซิฟ", "เข้าเซิร์ฟ", "เล่น", "server", "ip"):
            target_server = arg
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("connect_server", {"server": target_server, "callback": callback})

            try:
                res = await asyncio.wait_for(future, timeout=15.0)
                msg_text = res.get("message", "กำลังเปิดเกม FiveM...")
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    f"{tag_prefix} 🚀 **{msg_text}**",
                    reply_to_message_id=msg_id
                )
            except asyncio.TimeoutError:
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    f"{tag_prefix} ⚠️ การสั่งเข้าเกมหมดเวลา",
                    reply_to_message_id=msg_id
                )
            return

        # 3. CHECK BAG & SEND SCREENSHOT
        if main_cmd in ("check", "bag", "กระเป๋า", "ทอง", "gold"):
            wait_id = send_discord_rest_message(
                self.bot_token, channel_id,
                f"{tag_prefix} ⏳ กำลังสลับไป FiveM และเปิดกระเป๋าเพื่อถ่ายรูป กรุณารอสักครู่...",
                reply_to_message_id=msg_id
            )
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("check_bag", callback)

            try:
                res = await asyncio.wait_for(future, timeout=20.0)
                img_path = res.get("image_path")
                gold_info = res.get("gold_info", "ไม่ระบุ")
                status_info = res.get("status_info", "ปกติ")

                caption = (
                    f"{tag_prefix} 📦 **[ผลการตรวจสอบกระเป๋า FiveM]**\n"
                    f"• แร่ทอง: {gold_info}\n"
                    f"• สถานะบอท: {status_info}\n"
                    f"• เวลา: <t:{int(time.time())}:T>"
                )

                send_discord_rest_message(
                    self.bot_token, channel_id,
                    content=caption,
                    file_path=img_path,
                    reply_to_message_id=msg_id
                )
                if img_path and os.path.isfile(img_path):
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass
                if wait_id:
                    delete_discord_rest_message(self.bot_token, channel_id, wait_id)
            except asyncio.TimeoutError:
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    f"{tag_prefix} ⚠️ คำสั่งหมดเวลา: ไม่สามารถเปิดกระเป๋าได้ทันเวลา กรุณาเช็คว่าเปิด FiveM อยู่หรือไม่",
                    reply_to_message_id=msg_id
                )
            return

        # 4. DISCARD GOLD & RESUME FARMING
        if main_cmd in ("discard", "dump", "drop", "ทิ้งทอง", "ทิ้ง"):
            wait_id = send_discord_rest_message(
                self.bot_token, channel_id,
                f"{tag_prefix} 🗑️ กำลังเปิดกระเป๋าเพื่อกดทิ้งทอง และเริ่มฟาร์มต่อให้อัตโนมัติ...",
                reply_to_message_id=msg_id
            )
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("discard_gold", callback)

            try:
                res = await asyncio.wait_for(future, timeout=25.0)
                success = res.get("success", False)
                msg_text = res.get("message", "ดำเนินการเสร็จสิ้น")
                img_path = res.get("image_path")

                reply_text = f"{tag_prefix} ✅ **{msg_text}**" if success else f"{tag_prefix} ⚠️ **{msg_text}**"
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    content=reply_text,
                    file_path=img_path,
                    reply_to_message_id=msg_id
                )
                if img_path and os.path.isfile(img_path):
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass
                if wait_id:
                    delete_discord_rest_message(self.bot_token, channel_id, wait_id)
            except asyncio.TimeoutError:
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    f"{tag_prefix} ⚠️ คำสั่งหมดเวลา: การทิ้งทองใช้เวลานานเกินกำหนด",
                    reply_to_message_id=msg_id
                )
            return

        # 5. CAPTURE SCREEN
        if main_cmd in ("screen", "screenshot", "จอ", "ภาพ"):
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("screenshot", callback)

            try:
                res = await asyncio.wait_for(future, timeout=10.0)
                img_path = res.get("image_path")
                if img_path and os.path.isfile(img_path):
                    send_discord_rest_message(
                        self.bot_token, channel_id,
                        content=f"{tag_prefix} 📸 **ภาพหน้าจอ FiveM สดๆ** (<t:{int(time.time())}:T>)",
                        file_path=img_path,
                        reply_to_message_id=msg_id
                    )
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass
                else:
                    send_discord_rest_message(
                        self.bot_token, channel_id,
                        f"{tag_prefix} ⚠️ ไม่สามารถจับภาพหน้าจอ FiveM ได้ (หน้าต่างอาจถูกย่อ)",
                        reply_to_message_id=msg_id
                    )
            except asyncio.TimeoutError:
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    f"{tag_prefix} ⚠️ การถ่ายภาพหน้าจอหมดเวลา",
                    reply_to_message_id=msg_id
                )
            return

        # 6. START MACRO
        if main_cmd in ("start", "เริ่ม", "on"):
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("start_macro", callback)
            res = await future
            send_discord_rest_message(
                self.bot_token, channel_id,
                f"{tag_prefix} 🟢 **{res.get('message', 'เริ่มการทำงานของบอทแล้ว')}**",
                reply_to_message_id=msg_id
            )
            return

        # 7. STOP MACRO
        if main_cmd in ("stop", "หยุด", "off", "pause"):
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("stop_macro", callback)
            res = await future
            send_discord_rest_message(
                self.bot_token, channel_id,
                f"{tag_prefix} 🔴 **{res.get('message', 'หยุดพักบอทชั่วคราวแล้ว')}**",
                reply_to_message_id=msg_id
            )
            return

        # 8. FEED ACTION
        if main_cmd in ("feed", "กินข้าว", "กินน้ำ", "อาหาร", "กิน"):
            wait_id = send_discord_rest_message(
                self.bot_token, channel_id,
                f"{tag_prefix} 🍗 กำลังเริ่มกระบวนการกินน้ำ (ช่อง 6) และอาหาร (ช่อง 7)...",
                reply_to_message_id=msg_id
            )
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("feed", callback)

            try:
                res = await asyncio.wait_for(future, timeout=30.0)
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    f"{tag_prefix} 🍗 **{res.get('message', 'ป้อนอาหารและน้ำเรียบร้อยแล้ว')}**",
                    reply_to_message_id=msg_id
                )
                if wait_id:
                    delete_discord_rest_message(self.bot_token, channel_id, wait_id)
            except asyncio.TimeoutError:
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    f"{tag_prefix} ⚠️ กระบวนการกินอาหารหมดเวลา",
                    reply_to_message_id=msg_id
                )
            return

        # 9. STORE DIAMONDS
        if main_cmd in ("store", "เก็บเพชร", "เก็บของ", "รถ", "diamond", "เพชร"):
            wait_id = send_discord_rest_message(
                self.bot_token, channel_id,
                f"{tag_prefix} 💎 กำลังเริ่มกระบวนการเก็บเพชรลงท้ายรถ...",
                reply_to_message_id=msg_id
            )
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("store_diamonds", callback)

            try:
                res = await asyncio.wait_for(future, timeout=35.0)
                img_path = res.get("image_path")
                msg_text = res.get("message", "กระบวนการเก็บเพชรเสร็จสิ้น")
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    content=f"{tag_prefix} 💎 **{msg_text}**",
                    file_path=img_path,
                    reply_to_message_id=msg_id
                )
                if img_path and os.path.isfile(img_path):
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass
                if wait_id:
                    delete_discord_rest_message(self.bot_token, channel_id, wait_id)
            except asyncio.TimeoutError:
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    f"{tag_prefix} ⚠️ กระบวนการเก็บเพชรหมดเวลา",
                    reply_to_message_id=msg_id
                )
            return

        # 10. STATUS
        if main_cmd in ("status", "สถานะ", "info"):
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("get_status", callback)
            res = await future
            status_text = (
                f"{tag_prefix} 📊 **สถานะระบบ FiveM Farming Macro**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• สถานะบอท: {res.get('running_text', 'ไม่ระบุ')}\n"
                f"• การเชื่อมต่อ FiveM: {res.get('fivem_connected', 'ไม่ระบุ')}\n"
                f"• เป้าหมายทิ้งทองรอบนี้: {res.get('gold_target', '-')}\n"
                f"• โหมดเก็บเพชร: {res.get('diamond_mode', 'ไม่ระบุ')}\n"
                f"• ระบบอาหาร/น้ำ: {res.get('food_status', 'ไม่ระบุ')}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            send_discord_rest_message(self.bot_token, channel_id, status_text, reply_to_message_id=msg_id)
            return

        # 11. MARK MAP (map1 / mark1 / mark / map / มาร์คแมพ)
        if main_cmd in ("map1", "mark1", "map", "mark", "มาร์ค", "มาร์ค1", "แมพ1", "มาร์คแมพ", "ปักหมุด", "ทาง", "waypoint"):
            wait_id = send_discord_rest_message(
                self.bot_token, channel_id,
                f"{tag_prefix} 📍 กำลังเปิดแผนที่ (P) และปักหมุด Waypoint จุด Mine Job...",
                reply_to_message_id=msg_id
            )
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("mark_map", callback)

            try:
                res = await asyncio.wait_for(future, timeout=25.0)
                img_path = res.get("image_path")
                msg_text = res.get("message", "ปักหมุด Waypoint สำเร็จ")
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    content=f"{tag_prefix} 📍 **{msg_text}**",
                    file_path=img_path,
                    reply_to_message_id=msg_id
                )
                if img_path and os.path.isfile(img_path):
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass
                if wait_id:
                    delete_discord_rest_message(self.bot_token, channel_id, wait_id)
            except asyncio.TimeoutError:
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    f"{tag_prefix} ⚠️ กระบวนการมาร์คแมพหมดเวลา",
                    reply_to_message_id=msg_id
                )
            return

        # 12. MARK MAP 2: CAR POUND (map2 / mark2 / พาวรถ / car / car_pound)
        if main_cmd in ("map2", "mark2", "มาร์ค2", "แมพ2", "พาวรถ", "พาว", "car", "car_pound", "carpound"):
            wait_id = send_discord_rest_message(
                self.bot_token, channel_id,
                f"{tag_prefix} 📍 กำลังเปิดแผนที่ (P) และปักหมุด Waypoint พาวรถ (Car Pound 2/2)...",
                reply_to_message_id=msg_id
            )
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("mark_map2", callback)

            try:
                res = await asyncio.wait_for(future, timeout=25.0)
                img_path = res.get("image_path")
                msg_text = res.get("message", "ปักหมุด Waypoint พาวรถ สำเร็จ")
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    content=f"{tag_prefix} 📍 **{msg_text}**",
                    file_path=img_path,
                    reply_to_message_id=msg_id
                )
                if img_path and os.path.isfile(img_path):
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass
                if wait_id:
                    delete_discord_rest_message(self.bot_token, channel_id, wait_id)
            except asyncio.TimeoutError:
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    f"{tag_prefix} ⚠️ กระบวนการมาร์คแมพพาวรถหมดเวลา",
                    reply_to_message_id=msg_id
                )
            return

        # 13. SPAWN / TAKE OUT VEHICLE (car / spawn / เบิกรถ / เบิก / garage / เอารถ / การาจ)
        if main_cmd in ("car", "spawn", "เบิกรถ", "เบิก", "garage", "เอารถ", "การาจ", "รถ"):
            wait_id = send_discord_rest_message(
                self.bot_token, channel_id,
                f"{tag_prefix} 🚗 กำลังกด E ค้าง 2วิ เพื่อเปิดการาจและเบิกรถ...",
                reply_to_message_id=msg_id
            )
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("spawn_vehicle", callback)

            try:
                res = await asyncio.wait_for(future, timeout=25.0)
                img_path = res.get("image_path")
                msg_text = res.get("message", "สั่งเบิกรถเรียบร้อยแล้ว")
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    content=f"{tag_prefix} 🚗 **{msg_text}**",
                    file_path=img_path,
                    reply_to_message_id=msg_id
                )
                if img_path and os.path.isfile(img_path):
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass
                if wait_id:
                    delete_discord_rest_message(self.bot_token, channel_id, wait_id)
            except asyncio.TimeoutError:
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    f"{tag_prefix} ⚠️ กระบวนการเบิกรถหมดเวลา",
                    reply_to_message_id=msg_id
                )
            return

        # 14. AUTO DRIVE (drive / autodrive / ขับรถ / ขับออโต้ / auto / ขับ)
        if main_cmd in ("drive", "autodrive", "ขับรถ", "ขับออโต้", "auto", "ขับ", "ออโต้ไดรฟ์"):
            wait_id = send_discord_rest_message(
                self.bot_token, channel_id,
                f"{tag_prefix} 🚘 กำลังกด '-' (ข) เพื่อเปิดเมนูควบคุมรถและเปิด Auto Drive...",
                reply_to_message_id=msg_id
            )
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("auto_drive", callback)

            try:
                res = await asyncio.wait_for(future, timeout=20.0)
                img_path = res.get("image_path")
                msg_text = res.get("message", "เปิดระบบขับออโต้เรียบร้อยแล้ว")
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    content=f"{tag_prefix} 🚘 **{msg_text}**",
                    file_path=img_path,
                    reply_to_message_id=msg_id
                )
                if img_path and os.path.isfile(img_path):
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass
                if wait_id:
                    delete_discord_rest_message(self.bot_token, channel_id, wait_id)
            except asyncio.TimeoutError:
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    f"{tag_prefix} ⚠️ กระบวนการเปิดระบบขับออโต้หมดเวลา",
                    reply_to_message_id=msg_id
                )
            return

        # 15. CLOSE BAG / PRESS T (t / close / ปิดกระเป๋า / ปิด / closet / ปิดเป๋า / กดt)
        if main_cmd in ("t", "close", "ปิดกระเป๋า", "ปิด", "closet", "ปิดเป๋า", "กดt", "ปิดหน้าต่าง"):
            wait_id = send_discord_rest_message(
                self.bot_token, channel_id,
                f"{tag_prefix} 🚪 กำลังกด T เพื่อปิดกระเป๋า...",
                reply_to_message_id=msg_id
            )
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("close_bag", callback)

            try:
                res = await asyncio.wait_for(future, timeout=15.0)
                img_path = res.get("image_path")
                msg_text = res.get("message", "กดปุ่ม T ปิดกระเป๋าเรียบร้อยแล้ว")
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    content=f"{tag_prefix} 🚪 **{msg_text}**",
                    file_path=img_path,
                    reply_to_message_id=msg_id
                )
                if img_path and os.path.isfile(img_path):
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass
                if wait_id:
                    delete_discord_rest_message(self.bot_token, channel_id, wait_id)
            except asyncio.TimeoutError:
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    f"{tag_prefix} ⚠️ กระบวนการกด T ปิดกระเป๋าหมดเวลา",
                    reply_to_message_id=msg_id
                )
            return

# ==========================================
# REGION SELECTOR OVERLAY
# ==========================================
class RegionSelector(QWidget):
    def __init__(self, callback, close_callback=None):
        super().__init__()
        self.callback = callback
        self.close_callback = close_callback
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setWindowState(Qt.WindowFullScreen)
        self.setCursor(Qt.CrossCursor)
        screen = QApplication.primaryScreen()
        self.background_pixmap = screen.grabWindow(0)
        self.start_pos = None
        self.end_pos = None
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.background_pixmap)
        overlay_color = QColor(0, 0, 0, 60)
        if self.start_pos and self.end_pos:
            rect = QRect(self.start_pos, self.end_pos).normalized()
            painter.fillRect(0, 0, self.width(), rect.top(), overlay_color)
            painter.fillRect(0, rect.bottom(), self.width(), self.height() - rect.bottom(), overlay_color)
            painter.fillRect(0, rect.top(), rect.left(), rect.height(), overlay_color)
            painter.fillRect(rect.right(), rect.top(), self.width() - rect.right(), rect.height(), overlay_color)
            pen = QPen(QColor(239, 68, 68), 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)
        else:
            painter.fillRect(self.rect(), overlay_color)
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.position().toPoint()
            self.end_pos = self.start_pos
            self.update()
            
    def mouseMoveEvent(self, event):
        if self.start_pos:
            self.end_pos = event.position().toPoint()
            self.update()
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.start_pos and self.end_pos:
            x1, y1 = self.start_pos.x(), self.start_pos.y()
            x2, y2 = self.end_pos.x(), self.end_pos.y()
            x, y = min(x1, x2), min(y1, y2)
            w, h = abs(x2 - x1), abs(y2 - y1)
            if w > 5 and h > 5:
                self.callback(x, y, w, h)
            self.close()
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def closeEvent(self, event):
        if self.close_callback:
            self.close_callback()
        event.accept()

WINDOW_NAME = "FiveM"
TEMPLATES = {
    "gold": "templates/gold.png",
    "destroy": "templates/destroy.png",
    "all": "templates/all.png",
    "confirm": "templates/confirm.png"
}

# ==========================================
# WORKER THREAD FOR BACKGROUND MACRO
# ==========================================
class MacroWorker(QThread):
    log_signal = Signal(str)
    connection_signal = Signal(bool, str)
    match_signal = Signal(dict)
    running_state_signal = Signal(bool)
    hud_preview_signal = Signal(np.ndarray, np.ndarray, int, int)
    gold_preview_signal = Signal(np.ndarray, np.ndarray, float, float, float)
    diamond_preview_signal = Signal(np.ndarray, float, bool, str)

    def __init__(self):
        super().__init__()
        self.is_running = False
        self.is_exiting = False
        self.hwnd = None
        self.thresholds = {"gold": 0.84, "destroy": 0.75, "all": 0.65, "confirm": 0.65}
        self.delays = {"gold": 0.8, "destroy": 0.8, "all": 0.8, "confirm": 8.0}
        self.hud_region = None
        self.auto_farm_region = None
        self.bag_region = None
        self.gold_search_region = None
        self.destroy_search_region = None
        self.all_search_region = None
        self.confirm_search_region = None
        self.diamond_search_region = None
        self.diamond_trunk_search_region = None
        self.trunk_ready_search_region = None
        self.all_trunk_search_region = None
        self.confirm_trunk_search_region = None
        self.hunger_limit = 20
        self.thirst_limit = 20
        self.force_feed_test = False
        self.force_store_test = False
        self.last_hud_check_time = 0.0
        self.last_feeding_attempt_time = 0.0
        self.last_diamond_check_time = 0.0
        self.last_diamond_storage_time = 0.0
        self.diamond_pass_streak = 0
        self.diamond_full_streak = 0
        self.diamond_full_notified = False
        self.diamond_cycle_started_at = time.time()
        self.diamond_mode = "car_timer"
        self.diamond_interval_minutes = 40
        self.discord_webhook_url = ""
        self.auto_feed_enabled = True
        self.auto_store_enabled = True
        self.map_mark_coordinate = None
        self.reference_resolution = None
        self.template_reference_sizes = {}
        self.last_runtime_error = ""
        self.last_runtime_error_time = 0.0
        self.last_gold_debug_capture_time = 0.0
        self.gold_discard_target = None
        self.previous_gold_discard_target = None
        self.gold_estimated_count = 0
        self.gold_count_synced = False
        self.gold_count_candidate = None
        self.gold_count_candidate_streak = 0
        self.gold_count_committed = None
        self.gold_disposal_stage = None
        self.gold_disposal_started_at = 0.0
        self.gold_disposal_cooldown_until = 0.0
        self.capture_failure_streak = 0
        self.runtime_error_streak = 0
        self.last_runtime_error_occurrence_time = 0.0
        self.focus_failure_streak = 0
        self.last_watchdog_reset_time = 0.0
        self.watchdog_reconnecting = False
        self.watchdog_resume_at = 0.0
        # Recovery for a farm job that silently stops when the character's
        # inventory is full.  We compare low-resolution gameplay frames and
        # only inspect the bag after the scene has stayed still for a while.
        self.last_activity_frame = None
        self.last_activity_sample_time = 0.0
        self.character_idle_since = 0.0
        self.idle_inventory_recovery = False
        self.idle_inventory_check_until = 0.0
        self.last_rockstar_escape_time = 0.0
        self.discord_bug_alert_times = {}

    def set_config(self, key, config_type, value):
        if config_type == "threshold": self.thresholds[key] = value
        elif config_type == "delay": self.delays[key] = value
        elif config_type == "region":
            if key == "hud": self.hud_region = value
            elif key == "auto_farm": self.auto_farm_region = value
            elif key == "bag": self.bag_region = value
            elif key == "gold_search": self.gold_search_region = value
            elif key == "destroy_search": self.destroy_search_region = value
            elif key == "all_search": self.all_search_region = value
            elif key == "confirm_search": self.confirm_search_region = value
            elif key == "diamond_search": self.diamond_search_region = value
            elif key == "diamond_trunk_search": self.diamond_trunk_search_region = value
            elif key == "trunk_ready_search": self.trunk_ready_search_region = value
            elif key == "all_trunk_search": self.all_trunk_search_region = value
            elif key == "confirm_trunk_search": self.confirm_trunk_search_region = value
        elif config_type == "limit":
            if key == "hunger": self.hunger_limit = value
            elif key == "thirst": self.thirst_limit = value
        elif config_type == "toggle":
            if key == "auto_feed": self.auto_feed_enabled = value
            elif key == "auto_store": self.auto_store_enabled = value
        elif config_type == "diamond":
            if key == "mode": self.diamond_mode = str(value)
            elif key == "interval":
                self.diamond_interval_minutes = max(1, int(value))
            elif key == "webhook":
                self.discord_webhook_url = str(value or "").strip()
        elif config_type == "map_mark":
            if key == "coordinate": self.map_mark_coordinate = value
        elif config_type == "ref_res": self.reference_resolution = value
        elif config_type == "template_refs": self.template_reference_sizes = value or {}

    def reset_diamond_cycle(self):
        self.diamond_cycle_started_at = time.time()
        self.diamond_full_streak = 0

    def reset_runtime_watchdog(self, reason):
        """Reset transient worker state without stopping the app or bot."""
        now = time.time()
        self.hwnd = None  # Clear HWND immediately so next loop tick searches for new FiveM window
        self.watchdog_reconnecting = True
        self.watchdog_resume_at = now + 2.0
        self.capture_failure_streak = 0
        self.runtime_error_streak = 0
        self.last_runtime_error_occurrence_time = 0.0
        self.focus_failure_streak = 0
        self.last_runtime_error = ""
        self.last_runtime_error_time = 0.0
        self.last_hud_check_time = 0.0
        self.last_feeding_attempt_time = 0.0
        self.last_diamond_check_time = 0.0

        # A reconnect may show a different game session. Cancel transient state
        self.gold_discard_target = None
        self.gold_estimated_count = 0
        self.gold_count_synced = False
        self.gold_count_candidate = None
        self.gold_count_candidate_streak = 0
        self.gold_count_committed = None
        self.gold_disposal_stage = None
        self.gold_disposal_started_at = 0.0
        self.gold_disposal_cooldown_until = 0.0
        self.last_activity_frame = None
        self.character_idle_since = 0.0
        self.idle_inventory_recovery = False
        self.idle_inventory_check_until = 0.0

        if now - self.last_watchdog_reset_time >= 3.0:
            self.last_watchdog_reset_time = now
            resume_text = (
                "บอทจะกลับมาทำงานต่ออัตโนมัติ 🟢"
                if self.is_running
                else "เชื่อมต่อแล้วจะรอกด F9"
            )
            self.log_signal.emit(
                f"[Watchdog] {reason} — รีระบบชั่วคราวแล้ว กำลังค้นหา FiveM ใหม่..."
            )
            self.log_signal.emit(f"[Watchdog] {resume_text}")
            self.connection_signal.emit(
                False, "กำลังค้นหาหน้าต่าง FiveM ใหม่ (หลังรีเกม)..."
            )
            self.send_bug_webhook(
                "Watchdog รีระบบ",
                reason,
                alert_key="watchdog",
            )
        return True

    def record_focus_failure(self, reason):
        self.focus_failure_streak += 1
        if self.focus_failure_streak >= 3:
            self.reset_runtime_watchdog(reason)

    def send_diamond_full_webhook(self):
        if not self.discord_webhook_url:
            self.log_signal.emit("[Discord] เพชรเต็ม 40/40 แต่ยังไม่ได้ตั้งค่า Webhook")
            return
        machine_name = os.environ.get("COMPUTERNAME", "Unknown PC")
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        payload = json.dumps({
            "username": "FiveM Farming",
            "content": f"💎 เพชรเต็ม 40/40\\nเครื่อง: {machine_name}\\nเวลา: {timestamp}"
        }, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.discord_webhook_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "FiveM-Farming/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=10, context=HTTPS_CONTEXT
            ) as response:
                if response.status not in (200, 204):
                    raise RuntimeError(f"Discord HTTP {response.status}")
            self.log_signal.emit("[Discord] แจ้งเตือนเพชรเต็ม 40/40 สำเร็จ")
        except Exception as error:
            self.log_signal.emit(f"[Discord] ส่งแจ้งเตือนไม่สำเร็จ: {type(error).__name__}: {error}")

    def send_bug_webhook(
        self, title, detail, alert_key=None, cooldown_seconds=300.0
    ):
        """Send a rate-limited bug alert and current FiveM frame to Discord."""
        if not self.discord_webhook_url:
            return False
        now = time.time()
        key = str(alert_key or title)
        last_sent = self.discord_bug_alert_times.get(key, 0.0)
        if now - last_sent < cooldown_seconds:
            return False
        # Reserve the cooldown before the request so repeated failures cannot
        # stall the worker or flood its log on every loop iteration.
        self.discord_bug_alert_times[key] = now
        machine_name = os.environ.get("COMPUTERNAME", "Unknown PC")
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        safe_detail = str(detail or "ไม่ทราบรายละเอียด")[:1200]
        payload = json.dumps(
            {
                "username": "FiveM Farming Bug Alert",
                "content": (
                    f"⚠️ **ตรวจพบบัค: {title}**\n"
                    f"รายละเอียด: {safe_detail}\n"
                    f"เครื่อง: {machine_name}\n"
                    f"เวลา: {timestamp}"
                ),
            },
            ensure_ascii=False,
        ).encode("utf-8")
        screenshot = self.capture_background(self.hwnd)
        screenshot_attached = False
        headers = {"User-Agent": "FiveM-Farming/1.0"}
        request_data = payload
        if screenshot is not None:
            encoded, png_bytes = cv2.imencode(".png", screenshot)
            if encoded:
                # Discord requires multipart/form-data whenever a webhook
                # message includes a file attachment.
                boundary = f"----FiveMFarming{int(now * 1000)}"
                separator = f"--{boundary}\r\n".encode("ascii")
                request_data = b"".join((
                    separator,
                    b'Content-Disposition: form-data; name="payload_json"\r\n',
                    b"Content-Type: application/json\r\n\r\n",
                    payload,
                    b"\r\n",
                    separator,
                    b'Content-Disposition: form-data; name="files[0]"; filename="bug_screenshot.png"\r\n',
                    b"Content-Type: image/png\r\n\r\n",
                    png_bytes.tobytes(),
                    b"\r\n",
                    f"--{boundary}--\r\n".encode("ascii"),
                ))
                headers["Content-Type"] = (
                    f"multipart/form-data; boundary={boundary}"
                )
                screenshot_attached = True
        if not screenshot_attached:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.discord_webhook_url,
            data=request_data,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=10, context=HTTPS_CONTEXT
            ) as response:
                if response.status not in (200, 204):
                    raise RuntimeError(f"Discord HTTP {response.status}")
            image_status = "พร้อมภาพหน้าจอ" if screenshot_attached else "ไม่มีภาพหน้าจอ"
            self.log_signal.emit(
                f"[Discord] ส่งแจ้งเตือนบัคสำเร็จ: {title} ({image_status})"
            )
            return True
        except Exception as error:
            self.log_signal.emit(
                f"[Discord] ส่งแจ้งเตือนบัคไม่สำเร็จ: "
                f"{type(error).__name__}: {error}"
            )
            return False

    def safe_sleep(self, duration):
        """Sleep in small intervals so thread stops immediately when paused or exiting."""
        end_time = time.time() + duration
        while time.time() < end_time:
            if self.is_exiting or not self.is_running:
                break
            time.sleep(min(0.1, max(0.01, end_time - time.time())))

    def get_client_geometry(self, hwnd=None):
        """Return the game client origin on screen and its pixel size."""
        hwnd = hwnd or self.hwnd
        if not hwnd:
            return None
        try:
            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            screen_x, screen_y = win32gui.ClientToScreen(hwnd, (0, 0))
            width, height = right - left, bottom - top
            if width <= 0 or height <= 0:
                return None
            return screen_x, screen_y, width, height
        except Exception:
            return None

    def client_to_screen(self, x, y):
        try:
            return win32gui.ClientToScreen(self.hwnd, (int(x), int(y)))
        except Exception:
            geometry = self.get_client_geometry()
            if geometry:
                return geometry[0] + int(x), geometry[1] + int(y)
            return int(x), int(y)

    def get_scaled_region(self, region):
        if not region or not self.reference_resolution or not self.hwnd: return region
        try:
            geometry = self.get_client_geometry()
            if not geometry:
                return region
            cur_w, cur_h = geometry[2], geometry[3]
            ref_w, ref_h = self.reference_resolution
            if ref_w <= 0 or ref_h <= 0 or cur_w <= 0 or cur_h <= 0: return region
            if cur_w == ref_w and cur_h == ref_h: return region
            sx, sy = cur_w / ref_w, cur_h / ref_h
            return [int(region[0] * sx), int(region[1] * sy), int(region[2] * sx), int(region[3] * sy)]
        except Exception: return region

    def get_region_ranges(self, region, w_img, h_img, default_x=(0.0, 1.0), default_y=(0.0, 1.0)):
        if region:
            scaled = self.get_scaled_region(region)
            return (scaled[0]/w_img, (scaled[0]+scaled[2])/w_img), (scaled[1]/h_img, (scaled[1]+scaled[3])/h_img)
        return default_x, default_y

    def get_window_hwnd(self, keyword):
        hwnd_list = []
        def callback(hwnd, extra):
            try:
                if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
                    return
                rect = win32gui.GetClientRect(hwnd)
                if (rect[2] - rect[0] < 100) or (rect[3] - rect[1] < 100):
                    return

                title = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)
                lower_title = title.lower()

                # Exclude developer tools and background utilities
                if any(x in lower_title for x in ["visual studio", "cmd.exe", "powershell", "antigravity", "cursor", "chrome", "firefox", "edge"]):
                    return

                if class_name == "grcWindow":
                    hwnd_list.append((hwnd, title, 10))
                    return
                if "cfx.re" in lower_title:
                    hwnd_list.append((hwnd, title, 9))
                    return
                if keyword.lower() in lower_title:
                    hwnd_list.append((hwnd, title, 8))
                    return
                if "fivem" in lower_title or "grand theft auto" in lower_title or "gta5" in lower_title:
                    hwnd_list.append((hwnd, title, 7))
                    return
            except Exception:
                pass

        win32gui.EnumWindows(callback, None)
        hwnd_list.sort(key=lambda x: x[2], reverse=True)
        return hwnd_list[0][0] if hwnd_list else None

    def capture_background(self, hwnd):
        geometry = self.get_client_geometry(hwnd)
        if not geometry:
            return None
        width, height = geometry[2], geometry[3]
        hwindc = srcdc = memdc = bmp = None
        try:
            # Chicken PCs use the BitBlt capture backend proven by the supplied
            # non-flickering macro. The main PC keeps its current PrintWindow
            # backend unchanged.
            use_bitblt = os.environ.get("FIVEM_CAPTURE_BITBLT") == "1"
            if use_bitblt:
                hwindc = win32gui.GetWindowDC(hwnd)
            else:
                hwindc = win32gui.GetDC(hwnd)
            srcdc = win32ui.CreateDCFromHandle(hwindc)
            memdc = srcdc.CreateCompatibleDC()
            bmp = win32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(srcdc, width, height)
            memdc.SelectObject(bmp)
            if use_bitblt:
                memdc.BitBlt(
                    (0, 0),
                    (width, height),
                    srcdc,
                    (0, 0),
                    win32con.SRCCOPY,
                )
                result = 1
            else:
                result = ctypes.windll.user32.PrintWindow(hwnd, memdc.GetSafeHdc(), 3)
            if not result:
                return None
            bmpinfo = bmp.GetInfo()
            bmpstr = bmp.GetBitmapBits(True)
            img = np.frombuffer(bmpstr, dtype='uint8')
            img = img.reshape((bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))
            bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            # PrintWindow can report success but return a blank GPU surface.
            if bgr.size == 0 or float(np.std(bgr)) < 1.0:
                return None
            return bgr
        except Exception:
            return None
        finally:
            try:
                if bmp is not None:
                    win32gui.DeleteObject(bmp.GetHandle())
            except Exception:
                pass
            try:
                if memdc is not None:
                    memdc.DeleteDC()
            except Exception:
                pass
            try:
                if srcdc is not None:
                    srcdc.DeleteDC()
            except Exception:
                pass
            try:
                if hwindc is not None:
                    win32gui.ReleaseDC(hwnd, hwindc)
            except Exception:
                pass

    def save_latest_gold_debug_capture(self, bg_img):
        """Expose the exact PrintWindow frame used by the matcher for debugging."""
        try:
            now = time.time()
            if now - self.last_gold_debug_capture_time < 2.0:
                return
            self.last_gold_debug_capture_time = now
            output_path = get_writable_path("debug_gold_live.png")
            temporary_path = output_path + ".tmp.png"
            if cv2.imwrite(temporary_path, bg_img):
                os.replace(temporary_path, output_path)
        except Exception:
            pass

    def bg_click(self, hwnd, x, y):
        lparam = win32api.MAKELONG(int(x), int(y))
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
        time.sleep(0.05)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)

    def bg_right_click(self, hwnd, x, y):
        lparam = win32api.MAKELONG(int(x), int(y))
        win32gui.PostMessage(hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lparam)
        time.sleep(0.05)
        win32gui.PostMessage(hwnd, win32con.WM_RBUTTONUP, 0, lparam)

    def resolve_template_path(self, template_path):
        if os.path.isabs(template_path):
            return template_path
        writable_path = get_writable_path(template_path)
        if os.path.exists(writable_path):
            return writable_path
        return get_resource_path(template_path)

    def get_template_scale(self, template_path, image_width, image_height):
        template_name = os.path.basename(template_path)
        ref_size = self.template_reference_sizes.get(template_name)
        if not ref_size:
            ref_size = self.reference_resolution
        if not ref_size or len(ref_size) != 2:
            ref_size = [1600, 900]
        try:
            ref_w, ref_h = float(ref_size[0]), float(ref_size[1])
            if ref_w <= 0 or ref_h <= 0:
                return 1.0, 1.0
            return image_width / ref_w, image_height / ref_h
        except Exception:
            return 1.0, 1.0

    def find_image(self, bg_img, template_path, threshold, x_range=None, y_range=None):
        try:
            template_path = self.resolve_template_path(template_path)
            if not os.path.exists(template_path): return None
            template = cv2.imread(template_path)
            if template is None: return None
            h, w, _ = bg_img.shape
            x_start, x_end = int(x_range[0] * w) if x_range else 0, int(x_range[1] * w) if x_range else w
            y_start, y_end = int(y_range[0] * h) if y_range else 0, int(y_range[1] * h) if y_range else h
            x_start, x_end = max(0, min(x_start, w)), max(0, min(x_end, w))
            y_start, y_end = max(0, min(y_start, h)), max(0, min(y_end, h))
            crop_img = bg_img[y_start:y_end, x_start:x_end]
            if crop_img.size == 0:
                return None

            scale_x, scale_y = self.get_template_scale(template_path, w, h)
            # Search around the expected scale. This absorbs DPI rounding,
            # window-border differences and small FiveM UI-scale changes.
            nearby_scales = (1.0, 0.95, 1.05, 0.90, 1.10, 0.85, 1.15)
            crop_gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
            best_val, best_loc, best_size = -1.0, None, None
            seen_sizes = set()

            for nearby in nearby_scales:
                new_w = max(2, int(round(template.shape[1] * scale_x * nearby)))
                new_h = max(2, int(round(template.shape[0] * scale_y * nearby)))
                if (new_w, new_h) in seen_sizes:
                    continue
                seen_sizes.add((new_w, new_h))
                if crop_img.shape[0] < new_h or crop_img.shape[1] < new_w:
                    continue
                interpolation = cv2.INTER_AREA if new_w < template.shape[1] or new_h < template.shape[0] else cv2.INTER_CUBIC
                scaled_template = cv2.resize(template, (new_w, new_h), interpolation=interpolation)

                color_res = cv2.matchTemplate(crop_img, scaled_template, cv2.TM_CCOEFF_NORMED)
                _, color_val, _, color_loc = cv2.minMaxLoc(color_res)
                gray_template = cv2.cvtColor(scaled_template, cv2.COLOR_BGR2GRAY)
                gray_res = cv2.matchTemplate(crop_gray, gray_template, cv2.TM_CCOEFF_NORMED)
                _, gray_val, _, gray_loc = cv2.minMaxLoc(gray_res)
                if gray_val > color_val:
                    score, location = gray_val, gray_loc
                else:
                    score, location = color_val, color_loc
                if score > best_val:
                    best_val, best_loc, best_size = score, location, (new_w, new_h)
                if score >= max(0.97, threshold):
                    break

            if best_loc is None:
                return None
            if best_val >= threshold:
                tw, th = best_size
                return (x_start + best_loc[0] + tw // 2, y_start + best_loc[1] + th // 2, best_val)
            return (None, None, max(0.0, best_val))
        except Exception:
            return None

    def find_gold_count(self, bg_img, ore_x, ore_y, threshold):
        """Require a numerator of 30 or 40 directly above the detected gold."""
        try:
            template_path = self.resolve_template_path("templates/gold_text.png")
            template = cv2.imread(template_path)
            if template is None:
                return None

            # Remove the ore/background from the saved crop. More importantly,
            # keep only the first two glyph groups ("30"), not "/40". The
            # denominator is identical at 10/40, 20/40 and 30/40 and used to
            # produce false positives when it dominated the match score.
            upper = template[:max(3, int(template.shape[0] * 0.48)), :]
            upper_gray = cv2.cvtColor(upper, cv2.COLOR_BGR2GRAY)
            # The item-slot border is mid-gray; 120 isolates the white count
            # glyphs without pulling the whole crop into the template.
            _, bright = cv2.threshold(upper_gray, 120, 255, cv2.THRESH_BINARY)
            component_count, _, stats, _ = cv2.connectedComponentsWithStats(bright, 8)
            components = []
            for index in range(1, component_count):
                cx, cy, cw, ch, area = stats[index]
                if area >= 6 and ch >= 3:
                    components.append((int(cx), int(cy), int(cw), int(ch), int(area)))
            components.sort(key=lambda item: item[0])
            if len(components) < 2:
                return None

            first_two = components[:2]
            first_digit_x, first_digit_y, first_digit_w, first_digit_h, _ = first_two[0]
            first_digit_template = upper[
                first_digit_y:first_digit_y + first_digit_h,
                first_digit_x:first_digit_x + first_digit_w
            ]
            last_x, last_y, last_w, last_h, _ = components[-1]
            four_w = min(
                last_w, max(first_digit_w + 1, last_w // 2)
            )
            fourth_digit_template = upper[
                last_y:last_y + last_h,
                last_x:last_x + four_w
            ]
            tx = min(item[0] for item in first_two)
            ty = min(item[1] for item in first_two)
            tx_end = max(item[0] + item[2] for item in first_two)
            ty_end = max(item[1] + item[3] for item in first_two)
            tw, th = tx_end - tx, ty_end - ty
            pad = 2
            tx0, ty0 = max(0, tx - pad), max(0, ty - pad)
            tx1, ty1 = min(upper.shape[1], tx + tw + pad), min(upper.shape[0], ty + th + pad)
            numerator_template = upper[ty0:ty1, tx0:tx1]
            if numerator_template.size == 0:
                return None

            h_img, w_img = bg_img.shape[:2]
            ore_path = self.resolve_template_path("templates/gold_ore.png")
            sx, sy = self.get_template_scale(ore_path, w_img, h_img)

            # อ่านเลขหลักแรกจากภาพจริง เพื่อให้ 30-40 ผ่านได้ทั้งหมด
            live_x0 = max(0, ore_x)
            live_x1 = min(
                w_img, ore_x + max(24, int(round(45 * sx)))
            )
            live_y0 = max(
                0, ore_y - max(20, int(round(55 * sy)))
            )
            live_y1 = min(
                h_img, ore_y - max(5, int(round(15 * sy)))
            )
            live_strip = bg_img[live_y0:live_y1, live_x0:live_x1]
            if live_strip.size:
                live_gray = cv2.cvtColor(live_strip, cv2.COLOR_BGR2GRAY)
                _, live_binary = cv2.threshold(
                    live_gray, 120, 255, cv2.THRESH_BINARY
                )
                live_count, _, live_stats, _ = (
                    cv2.connectedComponentsWithStats(live_binary, 8)
                )
                live_glyphs = []
                min_h = max(3, int(round(4 * sy)))
                max_h = max(min_h + 1, int(round(12 * sy)))
                for index in range(1, live_count):
                    gx, gy, gw, gh, area = map(
                        int, live_stats[index]
                    )
                    if (
                        area >= 5
                        and min_h <= gh <= max_h
                        and gw >= 2
                    ):
                        live_glyphs.append((gx, gy, gw, gh, area))
                live_glyphs.sort(key=lambda item: item[0])
                if len(live_glyphs) >= 5:
                    first_live = live_glyphs[0]
                    row_glyphs = [
                        item for item in live_glyphs
                        if abs(item[1] - first_live[1])
                        <= max(2, int(round(2 * sy)))
                    ]
                    if len(row_glyphs) >= 5:
                        gx, gy, gw, gh, _ = first_live
                        live_digit = live_gray[
                            gy:gy + gh, gx:gx + gw
                        ]
                        digit_scores = []
                        for digit_template in (
                            first_digit_template,
                            fourth_digit_template
                        ):
                            scaled_digit = cv2.resize(
                                digit_template,
                                (gw, gh),
                                interpolation=(
                                    cv2.INTER_AREA
                                    if (
                                        gw < digit_template.shape[1]
                                        or gh < digit_template.shape[0]
                                    )
                                    else cv2.INTER_CUBIC
                                )
                            )
                            scaled_gray = cv2.cvtColor(
                                scaled_digit, cv2.COLOR_BGR2GRAY
                            )
                            score_result = cv2.matchTemplate(
                                live_digit,
                                scaled_gray,
                                cv2.TM_CCOEFF_NORMED
                            )
                            digit_scores.append(
                                cv2.minMaxLoc(score_result)[1]
                            )
                        leading_score = max(digit_scores)
                        if leading_score >= 0.72:
                            return (
                                live_x0 + gx + gw // 2,
                                live_y0 + gy + gh // 2,
                                leading_score,
                                live_strip
                            )

            # Search only the count area of this inventory slot. The old wide
            # rectangle could accidentally use a "30" from a neighbouring item.
            x0 = max(0, ore_x - max(4, int(round(10 * sx))))
            x1 = min(w_img, ore_x + max(12, int(round(50 * sx))))
            y0 = max(0, ore_y - max(12, int(round(55 * sy))))
            y1 = min(h_img, ore_y + max(3, int(round(8 * sy))))
            search_img = bg_img[y0:y1, x0:x1]
            if search_img.size == 0:
                return None

            scale_x, scale_y = self.get_template_scale(template_path, w_img, h_img)
            # Text rasterization changes a little more than icons when scaled,
            # so include a wider band around the expected size.
            scale_offsets = (1.0, 0.90, 1.10, 0.82, 1.18, 0.76, 1.24)
            search_gray = cv2.cvtColor(search_img, cv2.COLOR_BGR2GRAY)
            best_val, best_loc, best_size = -1.0, None, None
            seen_sizes = set()
            for nearby in scale_offsets:
                new_w = max(4, int(round(numerator_template.shape[1] * scale_x * nearby)))
                new_h = max(3, int(round(numerator_template.shape[0] * scale_y * nearby)))
                if (new_w, new_h) in seen_sizes:
                    continue
                seen_sizes.add((new_w, new_h))
                if search_gray.shape[0] < new_h or search_gray.shape[1] < new_w:
                    continue
                interpolation = cv2.INTER_AREA if new_w < numerator_template.shape[1] or new_h < numerator_template.shape[0] else cv2.INTER_CUBIC
                scaled = cv2.resize(numerator_template, (new_w, new_h), interpolation=interpolation)
                scaled_gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
                result = cv2.matchTemplate(search_gray, scaled_gray, cv2.TM_CCOEFF_NORMED)
                _, score, _, location = cv2.minMaxLoc(result)
                if score > best_val:
                    best_val, best_loc, best_size = score, location, (new_w, new_h)

            if best_loc is None:
                return (None, None, 0.0, search_img)

            # "20" can still resemble "30" when both tiny digits are matched
            # together because the trailing zero is identical. Verify the first
            # glyph independently: a 3 must match the saved 3 shape, not a 2.
            matched_scale_x = best_size[0] / float(numerator_template.shape[1])
            matched_scale_y = best_size[1] / float(numerator_template.shape[0])
            digit_w = max(2, int(round(first_digit_template.shape[1] * matched_scale_x)))
            digit_h = max(3, int(round(first_digit_template.shape[0] * matched_scale_y)))
            digit_offset_x = int(round((first_digit_x - tx0) * matched_scale_x))
            digit_offset_y = int(round((first_digit_y - ty0) * matched_scale_y))
            digit_x0 = best_loc[0] + digit_offset_x
            digit_y0 = best_loc[1] + digit_offset_y
            digit_crop = search_gray[digit_y0:digit_y0 + digit_h, digit_x0:digit_x0 + digit_w]
            first_digit_score = -1.0
            if digit_crop.shape == (digit_h, digit_w):
                digit_interpolation = cv2.INTER_AREA if digit_w < first_digit_template.shape[1] or digit_h < first_digit_template.shape[0] else cv2.INTER_CUBIC
                scaled_digit = cv2.resize(first_digit_template, (digit_w, digit_h), interpolation=digit_interpolation)
                scaled_digit_gray = cv2.cvtColor(scaled_digit, cv2.COLOR_BGR2GRAY)
                if float(np.std(scaled_digit_gray)) > 0.5:
                    digit_result = cv2.matchTemplate(digit_crop, scaled_digit_gray, cv2.TM_CCOEFF_NORMED)
                    _, first_digit_score, _, _ = cv2.minMaxLoc(digit_result)

            tw, th = best_size
            center_x = x0 + best_loc[0] + tw // 2
            center_y = y0 + best_loc[1] + th // 2
            if best_val >= threshold and first_digit_score >= 0.72:
                return (center_x, center_y, best_val, search_img)
            return (None, None, max(0.0, best_val), search_img)
        except Exception:
            return None

    def choose_next_gold_target(self):
        choices = [
            value for value in range(15, 31)
            if self.previous_gold_discard_target is None
            or abs(value - self.previous_gold_discard_target) > 3
        ]
        self.gold_discard_target = random.choice(choices)
        self.previous_gold_discard_target = self.gold_discard_target
        self.gold_estimated_count = 0
        self.gold_count_synced = True
        self.gold_count_candidate = None
        self.gold_count_candidate_streak = 0
        self.gold_count_committed = None
        self.gold_disposal_stage = None
        self.gold_disposal_started_at = 0.0
        self.gold_disposal_cooldown_until = time.time() + 30.0
        self.log_signal.emit(
            f"[ระบบทอง] เป้าหมายทิ้งรอบใหม่: "
            f"{self.gold_discard_target}/40"
        )

    def observe_gold_count_change(self, bg_img, ore_x, ore_y):
        """Count stable numerator changes after the first confirmed disposal."""
        if not self.gold_count_synced:
            return None
        try:
            h_img, w_img = bg_img.shape[:2]
            ore_path = self.resolve_template_path(
                "templates/gold_ore.png"
            )
            sx, sy = self.get_template_scale(ore_path, w_img, h_img)
            x0 = max(0, ore_x)
            x1 = min(
                w_img, ore_x + max(24, int(round(45 * sx)))
            )
            y0 = max(
                0, ore_y - max(20, int(round(55 * sy)))
            )
            y1 = min(
                h_img, ore_y - max(5, int(round(15 * sy)))
            )
            strip = bg_img[y0:y1, x0:x1]
            if strip.size == 0:
                return self.gold_estimated_count
            gray = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(
                gray, 120, 255, cv2.THRESH_BINARY
            )
            count, _, stats, _ = cv2.connectedComponentsWithStats(
                binary, 8
            )
            glyphs = []
            min_h = max(3, int(round(4 * sy)))
            max_h = max(min_h + 1, int(round(12 * sy)))
            for index in range(1, count):
                gx, gy, gw, gh, area = map(int, stats[index])
                if (
                    area >= 5
                    and min_h <= gh <= max_h
                    and gw >= 2
                ):
                    glyphs.append((gx, gy, gw, gh))
            glyphs.sort(key=lambda item: item[0])
            if len(glyphs) < 4:
                return self.gold_estimated_count
            first_y = glyphs[0][1]
            row = [
                item for item in glyphs
                if abs(item[1] - first_y)
                <= max(2, int(round(2 * sy)))
            ]
            if len(row) < 4:
                return self.gold_estimated_count
            rx0 = max(0, min(item[0] for item in row) - 1)
            ry0 = max(0, min(item[1] for item in row) - 1)
            rx1 = min(
                binary.shape[1],
                max(item[0] + item[2] for item in row) + 1
            )
            ry1 = min(
                binary.shape[0],
                max(item[1] + item[3] for item in row) + 1
            )
            signature_crop = binary[ry0:ry1, rx0:rx1]
            signature = cv2.resize(
                signature_crop,
                (48, 14),
                interpolation=cv2.INTER_NEAREST
            ).tobytes()
            if signature != self.gold_count_candidate:
                self.gold_count_candidate = signature
                self.gold_count_candidate_streak = 1
                return self.gold_estimated_count
            self.gold_count_candidate_streak += 1
            if (
                self.gold_count_candidate_streak >= 2
                and signature != self.gold_count_committed
            ):
                self.gold_count_committed = signature
                self.gold_estimated_count += 1
            return self.gold_estimated_count
        except Exception:
            return self.gold_estimated_count

    def activate_game_window(self):
        try:
            if not self.hwnd or not win32gui.IsWindow(self.hwnd):
                self.log_signal.emit("[ระบบ] ไม่พบหน้าต่าง FiveM สำหรับรับโฟกัส")
                self.record_focus_failure("ไม่พบหน้าต่าง FiveM สำหรับรับโฟกัส")
                return None
            if win32gui.IsIconic(self.hwnd):
                win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
                time.sleep(0.4)
            geometry = self.get_client_geometry()
            if not geometry:
                self.log_signal.emit("[ระบบ] อ่านตำแหน่งหน้าต่าง FiveM ไม่ได้")
                self.record_focus_failure("อ่านตำแหน่งหน้าต่าง FiveM ไม่ได้ 3 ครั้งติด")
                return None
            orig_pos = win32api.GetCursorPos()
            focus_error = None
            try:
                ctypes.windll.user32.SwitchToThisWindow(self.hwnd, True)
                win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
                win32gui.BringWindowToTop(self.hwnd)
                win32gui.SetForegroundWindow(self.hwnd)
            except Exception as error:
                focus_error = error
                attached = False
                try:
                    foreground = win32gui.GetForegroundWindow()
                    foreground_thread = win32process.GetWindowThreadProcessId(
                        foreground
                    )[0] if foreground else 0
                    current_thread = win32api.GetCurrentThreadId()
                    if foreground_thread and foreground_thread != current_thread:
                        attached = bool(
                            ctypes.windll.user32.AttachThreadInput(
                                current_thread, foreground_thread, True
                            )
                        )
                    ctypes.windll.user32.SwitchToThisWindow(self.hwnd, True)
                    win32gui.BringWindowToTop(self.hwnd)
                    win32gui.SetForegroundWindow(self.hwnd)
                except Exception as retry_error:
                    focus_error = retry_error
                finally:
                    if attached:
                        try:
                            ctypes.windll.user32.AttachThreadInput(
                                current_thread, foreground_thread, False
                            )
                        except Exception:
                            pass
            time.sleep(0.3)
            current_fg = win32gui.GetForegroundWindow()
            if current_fg != self.hwnd and win32gui.GetAncestor(current_fg, win32con.GA_ROOT) != self.hwnd:
                detail = f": {focus_error}" if focus_error else ""
                self.log_signal.emit(
                    "[ระบบ] ไม่สามารถโฟกัส FiveM ได้"
                    f"{detail} ยกเลิกรอบนี้เพื่อไม่ให้ส่งปุ่มผิดหน้าต่าง"
                )
                try:
                    win32api.SetCursorPos(orig_pos)
                except Exception:
                    pass
                self.record_focus_failure("โฟกัส FiveM ไม่สำเร็จ 3 ครั้งติด")
                return None
            self.focus_failure_streak = 0
            return orig_pos
        except Exception as error:
            self.log_signal.emit(f"[ระบบ] โฟกัส FiveM ไม่สำเร็จ: {error}")
            self.record_focus_failure("โฟกัส FiveM เกิดข้อผิดพลาด 3 ครั้งติด")
            return None

    def send_game_key(self, key_name, duration=0.10, require_focus=True):
        """Send a hardware key only while FiveM is the foreground window."""
        if require_focus and self.activate_game_window() is None:
            return False
        send_key_direct(key_name, duration=duration)
        return True

    def is_pause_menu_open(self, bg_img=None):
        """Detect the full-screen GTA V Pause Menu."""
        return False

    def ensure_not_in_pause_menu(self):
        return True

    def hold_game_key(self, key_name, duration=1.0, require_focus=True):
        """Hold a hardware key only while FiveM is the foreground window."""
        if require_focus and self.activate_game_window() is None:
            return False
        press_key_hold(key_name)
        try:
            time.sleep(duration)
            return True
        finally:
            release_key_hold(key_name)

    def update_character_idle_state(self, bg_img):
        """Open the inventory after a genuinely static gameplay interval."""
        if self.is_inventory_open(bg_img) or self.gold_disposal_stage:
            self.last_activity_frame = None
            self.character_idle_since = 0.0
            return False
        now = time.time()
        # If inventory is currently open on screen, the character is normally static (mining)
        if self.is_inventory_open(bg_img):
            self.character_idle_since = now
            self.last_activity_frame = None
            return False

        if now - self.last_activity_sample_time < 2.0:
            return False
        self.last_activity_sample_time = now
        h_img, w_img = bg_img.shape[:2]
        crop = bg_img[int(h_img * .18):int(h_img * .82), int(w_img * .20):int(w_img * .80)]
        frame = cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), (96, 54))
        if self.last_activity_frame is None:
            self.last_activity_frame = frame
            self.character_idle_since = now
            return False
        change = float(np.mean(cv2.absdiff(frame, self.last_activity_frame)))
        self.last_activity_frame = frame
        if change > 1.15:
            self.character_idle_since = now
            return False
        if now - self.character_idle_since < 20.0:
            return False
        self.log_signal.emit(
            "[ระบบทอง] ตรวจพบตัวละครยืนนิ่ง 20 วินาที กำลังเปิดกระเป๋าเช็คทองเต็ม"
        )
        if not self.ensure_inventory_open("[ระบบทอง]"):
            self.character_idle_since = now
            return False
        self.idle_inventory_recovery = True
        self.idle_inventory_check_until = time.time() + 8.0
        self.character_idle_since = 0.0
        self.last_activity_frame = None
        return True

    def is_rockstar_confirmation(self, bg_img):
        return False

    def recover_from_rockstar_confirmation(self, bg_img):
        return False

    def resume_farming_after_inventory(self):
        """Close the bag, enter the job interaction and click Auto Farm."""
        if not self.ensure_inventory_closed("[ระบบทอง]"):
            return False
        self.log_signal.emit("[ระบบทอง] กำลังเริ่มระบบฟาร์มใหม่...")
        if not self.hold_game_key("e", 1.5):
            return False
        time.sleep(1.5)
        bg_img = self.capture_background(self.hwnd)
        if bg_img is None:
            return False
        result = self.find_image(bg_img, "templates/auto_farm.png", 0.70)
        if not result or result[0] is None:
            self.log_signal.emit("[ระบบทอง] ไม่พบปุ่ม Auto Farm หลังปิดกระเป๋า")
            return False
        self.bg_click(self.hwnd, result[0], result[1])
        time.sleep(1.0)
        # Farming is monitored from the inventory screen.  Re-open it only
        # after Auto Farm has been clicked, matching the food and car cycles.
        if not self.ensure_inventory_open("[ระบบทอง]"):
            self.log_signal.emit(
                "[ระบบทอง] เริ่มฟาร์มแล้ว แต่เปิดกระเป๋ากลับไม่สำเร็จ"
            )
            return False
        self.log_signal.emit("[ระบบทอง] เริ่มระบบฟาร์มใหม่สำเร็จ")
        return True

    def is_inventory_open(self, bg_img=None):
        """Detect the inventory panel before trusting item-template matches."""
        if bg_img is None:
            bg_img = self.capture_background(self.hwnd)
        if bg_img is None:
            return False
        h_img, w_img = bg_img.shape[:2]
        scaled_bag = self.get_scaled_region(self.bag_region)
        if scaled_bag:
            bag_x, bag_y, bag_w, bag_h = scaled_bag
            x_start = max(0, min(int(bag_x), w_img))
            x_end = max(0, min(int(bag_x + bag_w), w_img))
            y_start = max(0, min(int(bag_y), h_img))
            y_end = max(0, min(int(bag_y + bag_h), h_img))
        else:
            x_start, x_end = int(w_img * 0.25), int(w_img * 0.90)
            y_start, y_end = int(h_img * 0.24), int(h_img * 0.95)

        # Strictly exclude top-right Quest HUD (x > 0.65, y < 0.24) which displays quest gold/diamond icons
        scan_y_start = max(y_start, int(h_img * 0.24))
        if x_end - x_start < 20 or y_end - scan_y_start < 20:
            return False

        bag_crop = bg_img[scan_y_start:y_end, x_start:x_end]
        bag_gray = cv2.cvtColor(bag_crop, cv2.COLOR_BGR2GRAY)
        dark_mask = cv2.inRange(bag_gray, 0, 88)
        dark_ratio = cv2.countNonZero(dark_mask) / float(dark_mask.size)
        if dark_ratio < 0.15:
            return False

        x_range = (x_start / w_img, x_end / w_img)
        y_range = (scan_y_start / h_img, y_end / h_img)
        for template_path, threshold in (
            ("templates/all.png", 0.65),
            ("templates/destroy.png", 0.65),
            ("templates/gold_ore.png", 0.70),
            ("templates/diamond_icon.png", 0.75),
            ("templates/gold.png", 0.70),
            ("templates/diamond_trunk.png", 0.70),
        ):
            result = self.find_image(
                bg_img,
                template_path,
                threshold,
                x_range=x_range,
                y_range=y_range
            )
            if result and result[0] is not None:
                mx, my, _ = result
                # Exclude any match that falls into the quest HUD box
                if my < int(h_img * 0.24) and mx > int(w_img * 0.65):
                    continue
                return True
        return False

    def ensure_inventory_open(self, log_prefix="[ระบบ]"):
        if self.is_inventory_open():
            self.log_signal.emit(
                f"{log_prefix} กระเป๋าเปิดอยู่แล้ว ไม่กด T ซ้ำ"
            )
            return True
        self.log_signal.emit(
            f"{log_prefix} ยังไม่พบหน้ากระเป๋า กำลังกด T..."
        )
        if not self.send_game_key("t"):
            return False
        time.sleep(1.2)
        opened = self.is_inventory_open()
        if opened:
            self.log_signal.emit(
                f"{log_prefix} ตรวจสอบแล้ว: เปิดกระเป๋าสำเร็จ"
            )
        else:
            self.log_signal.emit(
                f"{log_prefix} ส่งปุ่ม T แล้ว แต่ยังตรวจไม่พบหน้ากระเป๋า"
            )
        return opened

    def ensure_inventory_closed(self, log_prefix="[ระบบ]"):
        initial_bg = self.capture_background(self.hwnd)
        if initial_bg is None:
            self.log_signal.emit(
                f"{log_prefix} ยกเลิกการปิดกระเป๋า เพราะจับภาพยืนยันไม่ได้"
            )
            return False
        if not self.is_inventory_open(initial_bg):
            self.log_signal.emit(f"{log_prefix} กระเป๋าปิดอยู่แล้ว")
            return True
        for attempt in range(1, 3):
            if attempt == 1:
                self.log_signal.emit(
                    f"{log_prefix} พบว่ากระเป๋าเปิดอยู่ "
                    "กำลังกด T เพื่อปิด..."
                )
            else:
                self.log_signal.emit(
                    f"{log_prefix} กระเป๋ายังเปิดอยู่ "
                    "กำลังลองกด T ซ้ำครั้งสุดท้าย..."
                )
            # FiveM can swallow a short T press when focus changes or the UI is
            # still animating. Re-focus before every attempt, hold the key a
            # little longer, then verify two fresh frames.
            if self.activate_game_window() is None:
                self.log_signal.emit(
                    f"{log_prefix} ยกเลิกการปิดกระเป๋า เพราะโฟกัส FiveM ไม่สำเร็จ"
                )
                return False
            time.sleep(0.4)
            if not self.send_game_key("t", duration=0.25):
                return False
            time.sleep(3.0)
            first_check = self.capture_background(self.hwnd)
            closed_once = (
                first_check is not None
                and not self.is_inventory_open(first_check)
            )
            if closed_once:
                time.sleep(0.6)
                second_check = self.capture_background(self.hwnd)
                if (
                    second_check is not None
                    and not self.is_inventory_open(second_check)
                ):
                    self.log_signal.emit(
                        f"{log_prefix} ตรวจสอบแล้ว: ปิดกระเป๋าสำเร็จ"
                    )
                    return True
            if attempt < 2:
                time.sleep(0.5)
        self.log_signal.emit(
            f"{log_prefix} ยังปิดกระเป๋าไม่สำเร็จหลังลอง 2 ครั้ง"
        )
        self.send_bug_webhook(
            "ปิดกระเป๋าไม่สำเร็จ",
            f"{log_prefix} ลองกด T เพื่อปิดกระเป๋าแล้ว 2 ครั้ง",
            alert_key="inventory_close_failed",
        )
        try:
            debug_bg = self.capture_background(self.hwnd)
            if debug_bg is not None:
                cv2.imwrite(
                    get_writable_path("debug_inventory_close_failed.png"),
                    debug_bg,
                )
                self.log_signal.emit(
                    f"{log_prefix} บันทึกภาพ Debug: debug_inventory_close_failed.png"
                )
        except Exception:
            pass
        return False

    def process_hud_preview(self, bg_img):
        try:
            h_img, w_img, _ = bg_img.shape
            scaled = self.get_scaled_region(self.hud_region)
            if not scaled: return
            hx, hy, hw, hh = scaled
            x_start, x_end = max(0, min(hx, w_img)), max(0, min(hx + hw, w_img))
            y_start, y_end = max(0, min(hy, h_img)), max(0, min(hy + hh, h_img))
            if (x_end - x_start) < 10 or (y_end - y_start) < 10: return
            hud_crop = bg_img[y_start:y_end, x_start:x_end]
            
            # Check if screen/HUD region is dark/loading screen
            if float(np.std(hud_crop)) < 8.0 or float(np.mean(hud_crop)) < 12.0:
                self.hud_preview_signal.emit(hud_crop, np.zeros_like(hud_crop), -1, -1)
                return

            hsv = cv2.cvtColor(hud_crop, cv2.COLOR_BGR2HSV)
            lower_pink, upper_pink = np.array([130, 45, 70]), np.array([170, 255, 255])
            mask = cv2.inRange(hsv, lower_pink, upper_pink)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            crop_w = mask.shape[1]
            hunger_px = int(np.sum(mask[:, :crop_w//2] > 0))
            thirst_px = int(np.sum(mask[:, crop_w//2:] > 0))
            color_mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            color_mask[mask > 0] = [180, 50, 240]
            self.hud_preview_signal.emit(hud_crop, color_mask, hunger_px, thirst_px)
        except Exception: pass

    def execute_feeding_sequence(self, need_food, need_water):
        self.log_signal.emit(f"[ระบบป้อนอาหาร] เริ่มกระบวนการกิน (น้ำ: {need_water}, ข้าว: {need_food})...")
        orig_pos = self.activate_game_window()
        if orig_pos is None:
            self.log_signal.emit("[ระบบป้อนอาหาร] ยกเลิกรอบกิน เพราะ FiveM ไม่ได้อยู่ด้านหน้า")
            return False
        # ปิดกระเป๋าอย่างปลอดภัยด้วยปุ่ม T (ห้ามกด Esc เพราะจะเปิด Pause Menu/Rockstar)
        if not self.ensure_inventory_closed("[ระบบป้อนอาหาร]"):
            self.log_signal.emit("[ระบบป้อนอาหาร] ตรวจพบว่าปิดกระเป๋าไม่สำเร็จ ยกเลิกรอบกิน")
            return False
        self.safe_sleep(0.5)
        if not self.is_running or self.is_exiting: return False
        if not self.send_game_key("x"):
            return False
        self.safe_sleep(0.8)
        if not self.is_running or self.is_exiting: return False
        if need_water:
            self.log_signal.emit("[ระบบป้อนอาหาร] กำลังกินน้ำ (ช่อง 6)...")
            if not self.send_game_key("6"):
                return False
            self.safe_sleep(8.0)
            if not self.is_running or self.is_exiting: return False
        if need_food:
            self.log_signal.emit("[ระบบป้อนอาหาร] กำลังกินอาหาร (ช่อง 7)...")
            if not self.send_game_key("7"):
                return False
            self.safe_sleep(8.0)
            if not self.is_running or self.is_exiting: return False
        self.ensure_not_in_pause_menu()
        self.log_signal.emit("[ระบบป้อนอาหาร] กลับไปทำอาชีพ (กด E ค้าง 1.5 วินาที)...")
        if not self.hold_game_key("e", 1.5):
            return False
        self.safe_sleep(1.5)
        bg_after = self.capture_background(self.hwnd)
        if bg_after is not None:
            h_img, w_img, _ = bg_after.shape
            scaled_af = self.get_scaled_region(self.auto_farm_region)
            af_range_x = (scaled_af[0]/w_img, (scaled_af[0]+scaled_af[2])/w_img) if scaled_af else None
            af_range_y = (scaled_af[1]/h_img, (scaled_af[1]+scaled_af[3])/h_img) if scaled_af else None
            
            btn_result = self.find_image(bg_after, "templates/auto_farm.png", 0.85, x_range=af_range_x, y_range=af_range_y)
            if not btn_result or btn_result[0] is None:
                # [แก้ไข] ค้นหาปุ่มเริ่มงานทั่วหน้าจอ ป้องกันตั้งพิกัดคลาดเคลื่อน
                btn_result = self.find_image(bg_after, "templates/auto_farm.png", 0.70)
                
            if btn_result and btn_result[0] is not None:
                bx, by, bval = btn_result
                win32api.SetCursorPos(self.client_to_screen(bx, by))
                time.sleep(0.1)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                self.safe_sleep(2.0)
        self.log_signal.emit("[ระบบป้อนอาหาร] กำลังเปิดกระเป๋าอีกครั้ง (ปุ่ม T)...")
        if not self.send_game_key("t"):
            return False
        self.safe_sleep(1.0)
        if orig_pos:
            try: win32api.SetCursorPos(orig_pos)
            except: pass
        self.log_signal.emit("[ระบบป้อนอาหาร] กินเสร็จเรียบร้อย!")
        return True

    def check_and_run_auto_feed(self):
        bg_img = self.capture_background(self.hwnd)
        if bg_img is None: return
        h_img, w_img, _ = bg_img.shape
        scaled = self.get_scaled_region(self.hud_region)
        if not scaled: return
        hx, hy, hw, hh = scaled
        x_start, x_end = max(0, min(hx, w_img)), max(0, min(hx + hw, w_img))
        y_start, y_end = max(0, min(hy, h_img)), max(0, min(hy + hh, h_img))
        if x_end - x_start < 10 or y_end - y_start < 10: return
        hud_crop = bg_img[y_start:y_end, x_start:x_end]
        
        # ป้องกันสั่งกินอาหารตอนจอเกมยังโหลดไม่เสร็จหรือจอดำ
        if float(np.std(hud_crop)) < 8.0 or float(np.mean(hud_crop)) < 12.0:
            return

        hsv = cv2.cvtColor(hud_crop, cv2.COLOR_BGR2HSV)
        lower_pink, upper_pink = np.array([130, 45, 70]), np.array([170, 255, 255])
        mask = cv2.inRange(hsv, lower_pink, upper_pink)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        crop_w = mask.shape[1]
        hunger_px = int(np.sum(mask[:, :crop_w//2] > 0))
        thirst_px = int(np.sum(mask[:, crop_w//2:] > 0))
        
        # ถ้าทั้ง 2 ค่าเป็น 0 พอดี ให้ข้ามไปก่อน (HUD อาจยังไม่โผล่ในเกม)
        if hunger_px == 0 and thirst_px == 0:
            return

        need_food = hunger_px < self.hunger_limit
        need_water = thirst_px < self.thirst_limit
        if need_food or need_water:
            now = time.time()
            if now - self.last_feeding_attempt_time < 60.0:
                return
            self.last_feeding_attempt_time = now
            self.execute_feeding_sequence(need_food, need_water)

    def double_click_at(self, abs_x, abs_y):
        try:
            win32api.SetCursorPos((abs_x, abs_y))
            time.sleep(0.1)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        except Exception: pass

    def check_diamonds_exceed_30(self, slot_img):
        """Return True only when the displayed diamond count is at least 30.

        FiveM renders the count as tiny text such as ``31/40``.  The old
        detector treated the narrowest character as the slash, but the digit
        ``1`` is actually narrower than ``/``.  That made 31/40 fail.  Split
        the five glyphs as two numerator digits + slash + ``40`` instead, then
        distinguish a leading 3/4 from a leading 1/2 by the lower-half stroke.
        """
        try:
            h, w = slot_img.shape[:2]
            if h < 10 or w < 10:
                return False

            # Number text "X/Y" is in the top-right area of the slot.
            # The match centre can move slightly when the diamond artwork is
            # re-cropped.  Keep enough of the slot's upper half so the count is
            # not clipped to only its first four pixel rows.
            # Keep only the thin counter strip.  Using 40% of the slot also
            # included the bright diamond artwork below the text; its columns
            # merged with the first digit and made valid 31/40–39/40 fail.
            num_h = max(12, int(h * 0.20))
            num_w = max(12, int(w * 0.68))
            num_area = slot_img[:num_h, w - num_w:]
            gray = cv2.cvtColor(num_area, cv2.COLOR_BGR2GRAY)

            # A slightly lower threshold preserves all seven pixel rows of the
            # tiny anti-aliased font while the dark inventory background stays
            # black.
            _, thresh = cv2.threshold(gray, 105, 255, cv2.THRESH_BINARY)

            # Analyze column projection to find character groups.
            col_has = np.any(thresh > 0, axis=0)
            groups = []
            in_g = False
            start = 0
            for i in range(len(col_has)):
                if col_has[i] and not in_g:
                    start = i
                    in_g = True
                elif not col_has[i] and in_g:
                    if i - start >= 2:
                        groups.append((start, i))
                    in_g = False
            if in_g and len(col_has) - start >= 2:
                groups.append((start, len(col_has)))

            # NN/40 contains five groups.  Do not guess the slash from width:
            # in 31/40 the "1" is narrower than the slash.
            if len(groups) < 5:
                return False

            # Use the rightmost five groups so an unrelated bright edge on the
            # left cannot shift the count characters.
            count_groups = groups[-5:]
            first_x0, first_x1 = count_groups[0]
            first_glyph = thresh[:, first_x0:first_x1]
            row_has = np.any(first_glyph > 0, axis=1)
            active_rows = np.flatnonzero(row_has)
            if active_rows.size < 5 or first_glyph.shape[1] < 3:
                return False
            first_glyph = first_glyph[
                active_rows[0]:active_rows[-1] + 1, :
            ]

            # For this font, a leading 2 has its lower-middle stroke on the
            # left.  A leading 3 (and 4) has that stroke on the right.  This
            # rejects 10/40 and 20/40 while accepting 30/40 through 40/40.
            gh, gw = first_glyph.shape
            lower_y0 = max(0, int(round(gh * 0.52)))
            lower_y1 = max(lower_y0 + 1, int(round(gh * 0.86)))
            side_w = max(1, int(round(gw * 0.45)))
            lower_band = first_glyph[lower_y0:lower_y1, :]
            left_stroke = int(np.count_nonzero(lower_band[:, :side_w]))
            right_stroke = int(np.count_nonzero(lower_band[:, gw-side_w:]))
            return right_stroke > 0 and right_stroke >= left_stroke + 1
        except Exception:
            return False

    def execute_store_diamonds_sequence(self):
        self.log_signal.emit("[ระบบเก็บเพชร] เริ่มกระบวนการเก็บเพชรลงรถ...")
        orig_pos = self.activate_game_window()
        if orig_pos is None:
            self.log_signal.emit(
                "[ระบบเก็บเพชร] ยกเลิกรอบเก็บ "
                "เพราะ FiveM ไม่ได้อยู่ด้านหน้า"
            )
            return False
        if not self.ensure_inventory_closed("[ระบบเก็บเพชร]"):
            self.log_signal.emit(
                "[ระบบเก็บเพชร] ยกเลิกรอบ "
                "เพราะตรวจว่ายังปิดกระเป๋าไม่ได้"
            )
            return False
        if not self.send_game_key("x"):
            return False
        time.sleep(1.0)
        # The trunk requires H, but FiveM/NUI only receives it reliably when
        # its client has both keyboard focus and the pointer inside the game.
        # Do this immediately before H so the key cannot reach another window.
        if self.activate_game_window() is None:
            return False
        geometry = self.get_client_geometry()
        if not geometry:
            self.log_signal.emit("[ระบบเก็บเพชร] อ่านพื้นที่ FiveM ไม่ได้ จึงไม่กด H")
            return False
        game_x, game_y, game_w, game_h = geometry
        win32api.SetCursorPos((game_x + game_w // 2, game_y + game_h // 2))
        time.sleep(0.2)
        if not self.send_game_key("h", duration=0.15):
            return False
        time.sleep(1.3)
        trunk_opened = False
        stored_successfully = False
        bg_img = self.capture_background(self.hwnd)
        if bg_img is not None:
            h_img, w_img, _ = bg_img.shape
            tr_x, tr_y = self.get_region_ranges(self.trunk_ready_search_region, w_img, h_img, (0.0, 1.0), (0.0, 1.0))
            btn_ready = self.find_image(bg_img, "templates/trunk_ready.png", 0.60, x_range=tr_x, y_range=tr_y)
            if btn_ready and btn_ready[0] is not None:
                bx, by, bval = btn_ready
                screen_x, screen_y = self.client_to_screen(bx, by)
                self.double_click_at(screen_x, screen_y)
                trunk_opened = True
                time.sleep(4.0)
        if not trunk_opened:
            self.log_signal.emit(
                "[ระบบเก็บเพชร] ไม่พบปุ่มเปิดท้ายรถ ยกเลิกรอบนี้"
            )
            self.ensure_inventory_open("[ระบบเก็บเพชร]")
            if orig_pos:
                try:
                    win32api.SetCursorPos(orig_pos)
                except Exception:
                    pass
            return False
        bg_trunk = self.capture_background(self.hwnd)
        if bg_trunk is not None:
            h_img, w_img, _ = bg_trunk.shape
            scaled_bag = self.get_scaled_region(self.bag_region)
            default_x = (scaled_bag[0]/w_img, (scaled_bag[0]+scaled_bag[2])/w_img) if scaled_bag else (0.33, 0.85)
            default_y = (max(0.24, scaled_bag[1]/h_img), (scaled_bag[1]+scaled_bag[3])/h_img) if scaled_bag else (0.24, 0.90)
            
            dia_x, dia_y = self.get_region_ranges(self.diamond_trunk_search_region, w_img, h_img, default_x, default_y)
            diamond_result = self.find_image(bg_trunk, "templates/diamond_trunk.png", 0.70, x_range=dia_x, y_range=dia_y)
            if diamond_result and diamond_result[0] is not None:
                if diamond_result[1] < int(h_img * 0.24) and diamond_result[0] > int(w_img * 0.65):
                    diamond_result = None
            
            if diamond_result and diamond_result[0] is not None:
                dx, dy, dval = diamond_result
                screen_x, screen_y = self.client_to_screen(dx, dy)
                self.double_click_at(screen_x, screen_y)
                time.sleep(1.0)
                bg_pop = self.capture_background(self.hwnd)
                if bg_pop is not None:
                    at_x, at_y = self.get_region_ranges(self.all_trunk_search_region, w_img, h_img, (0.0, 1.0), (0.0, 1.0))
                    btn_all = self.find_image(bg_pop, "templates/all_trunk.png", 0.60, x_range=at_x, y_range=at_y)
                    if btn_all and btn_all[0] is not None:
                        ax, ay, aval = btn_all
                        win32api.SetCursorPos(self.client_to_screen(ax, ay))
                        time.sleep(0.1)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                        time.sleep(0.05)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                        time.sleep(0.5)
                        bg_confirm = self.capture_background(self.hwnd)
                        if bg_confirm is not None:
                            ct_x, ct_y = self.get_region_ranges(self.confirm_trunk_search_region, w_img, h_img, (0.0, 1.0), (0.0, 1.0))
                            btn_conf = self.find_image(bg_confirm, "templates/confirm_trunk.png", 0.60, x_range=ct_x, y_range=ct_y)
                            if btn_conf and btn_conf[0] is not None:
                                cx, cy, cval = btn_conf
                                win32api.SetCursorPos(self.client_to_screen(cx, cy))
                                time.sleep(0.1)
                                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                                time.sleep(0.05)
                                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                                time.sleep(1.5)
                                stored_successfully = True
        if not stored_successfully:
            self.log_signal.emit(
                "[ระบบเก็บเพชร] ไม่พบเพชรหรือปุ่มยืนยัน จึงยังไม่ได้เก็บเข้ารถ"
            )
        if trunk_opened:
            # ปิดหน้าต่างท้ายรถ/กระเป๋าอย่างปลอดภัย (ไม่กด Esc เปล่าๆ เพื่อไม่ให้เปิด Pause Menu)
            self.ensure_inventory_closed("[ระบบเก็บเพชร]")
            time.sleep(0.5)
            self.ensure_not_in_pause_menu()
        self.ensure_not_in_pause_menu()
        if not self.hold_game_key("e", 1.5):
            return False
        time.sleep(1.5)
        bg_final = self.capture_background(self.hwnd)
        if bg_final is not None:
            # [แก้ไข] ค้นหาปุ่มเริ่มงานทั่วหน้าจอ ป้องกันตั้งพิกัดคลาดเคลื่อน
            btn_result = self.find_image(bg_final, "templates/auto_farm.png", 0.70)
            if btn_result and btn_result[0] is not None:
                bx, by, _ = btn_result
                win32api.SetCursorPos(self.client_to_screen(bx, by))
                time.sleep(0.1)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                time.sleep(2.0)
        self.ensure_inventory_open("[ระบบเก็บเพชร]")
        if orig_pos:
            try: win32api.SetCursorPos(orig_pos)
            except: pass
        if stored_successfully:
            self.log_signal.emit(
                "[ระบบเก็บเพชร] เก็บเพชรเข้ารถสำเร็จ!"
            )
        return stored_successfully

    def check_and_run_store_diamonds(self, trigger_storage=False):
        bg_img = self.capture_background(self.hwnd)
        if bg_img is None: return
        h_img, w_img, _ = bg_img.shape
        scaled_bag = self.get_scaled_region(self.bag_region)
        default_x = (scaled_bag[0]/w_img, (scaled_bag[0]+scaled_bag[2])/w_img) if scaled_bag else (0.33, 0.85)
        default_y = (max(0.24, scaled_bag[1]/h_img), (scaled_bag[1]+scaled_bag[3])/h_img) if scaled_bag else (0.24, 0.90)
        dia_x, dia_y = self.get_region_ranges(self.diamond_search_region, w_img, h_img, default_x, default_y)
        diamond_result = self.find_image(bg_img, "templates/diamond_icon.png", 0.86, x_range=dia_x, y_range=dia_y)
        if diamond_result and diamond_result[0] is not None:
            if diamond_result[1] < int(h_img * 0.24) and diamond_result[0] > int(w_img * 0.65):
                diamond_result = None
        if diamond_result and diamond_result[0] is not None:
            dx, dy, val = diamond_result
            # Load template to get actual dimensions for proper slot extraction
            tpl_w_path = get_writable_path("templates/diamond_icon.png")
            tpl_path = tpl_w_path if os.path.exists(tpl_w_path) else get_resource_path("templates/diamond_icon.png")
            tpl = cv2.imread(tpl_path)
            if tpl is not None:
                th, tw = tpl.shape[:2]
            else:
                th, tw = 55, 43
            # Extract slot area centered on match with adaptive margin
            margin = max(12, int(max(tw, th) * 0.35))
            x_start = max(0, dx - tw // 2 - margin)
            x_end = min(w_img, dx + tw // 2 + margin)
            y_start = max(0, dy - th // 2 - margin)
            y_end = min(h_img, dy + th // 2 + margin)
            slot_img = np.zeros((10, 10, 3), dtype=np.uint8)
            passed = False
            status_str = "ไม่ผ่านเกณฑ์ (< 30 เม็ด)"
            slot_w, slot_h = x_end - x_start, y_end - y_start
            if slot_w >= 20 and slot_h >= 20:
                slot_img = bg_img[y_start:y_end, x_start:x_end]
                passed = self.check_diamonds_exceed_30(slot_img)
                if passed:
                    status_str = "ผ่านเกณฑ์ >= 30 เม็ด (เตรียมเก็บของ)"
            if passed:
                self.diamond_pass_streak += 1
            else:
                self.diamond_pass_streak = 0
            confirmed = passed and self.diamond_pass_streak >= 2
            if passed and not confirmed:
                status_str = "พบเพชร >= 30 เม็ด กำลังยืนยันภาพซ้ำก่อนเก็บ"
            self.diamond_preview_signal.emit(slot_img, val, confirmed, status_str)
            if confirmed and trigger_storage:
                now = time.time()
                # Never repeat the long storage sequence continuously when the
                # inventory has not changed or a prior storage attempt failed.
                if now - self.last_diamond_storage_time >= 120.0:
                    self.last_diamond_storage_time = now
                    self.diamond_pass_streak = 0
                    self.execute_store_diamonds_sequence()
        else:
            self.diamond_pass_streak = 0
            val = diamond_result[2] if diamond_result else 0.0
            slot_img = np.zeros((10, 10, 3), dtype=np.uint8)
            self.diamond_preview_signal.emit(slot_img, val, False, "ไม่พบรูปเพชรในกระเป๋า")

    def check_and_run_timed_diamond_store(self):
        """Store any detected diamonds when the configured timer is due."""
        bg_img = self.capture_background(self.hwnd)
        if bg_img is None:
            return
        h_img, w_img = bg_img.shape[:2]
        scaled_bag = self.get_scaled_region(self.bag_region)
        default_x = (scaled_bag[0] / w_img, (scaled_bag[0] + scaled_bag[2]) / w_img) if scaled_bag else (0.33, 0.85)
        default_y = (max(0.24, scaled_bag[1] / h_img), (scaled_bag[1] + scaled_bag[3]) / h_img) if scaled_bag else (0.24, 0.90)
        dia_x, dia_y = self.get_region_ranges(
            self.diamond_search_region, w_img, h_img, default_x, default_y
        )
        diamond_result = self.find_image(
            bg_img, "templates/diamond_icon.png", 0.86,
            x_range=dia_x, y_range=dia_y
        )
        if diamond_result and diamond_result[0] is not None:
            if diamond_result[1] < int(h_img * 0.24) and diamond_result[0] > int(w_img * 0.65):
                diamond_result = None
        elapsed = time.time() - self.diamond_cycle_started_at
        interval_seconds = self.diamond_interval_minutes * 60
        remaining = max(0, int(interval_seconds - elapsed))
        if diamond_result and diamond_result[0] is not None:
            dx, dy, val = diamond_result
            preview_size = 76
            x0, x1 = max(0, dx - preview_size // 2), min(w_img, dx + preview_size // 2)
            y0, y1 = max(0, dy - preview_size // 2), min(h_img, dy + preview_size // 2)
            slot_img = bg_img[y0:y1, x0:x1]
            if elapsed >= interval_seconds:
                now = time.time()
                if now - self.last_diamond_storage_time < 120.0:
                    retry_in = int(
                        120.0 - (now - self.last_diamond_storage_time)
                    )
                    self.diamond_preview_signal.emit(
                        slot_img,
                        val,
                        False,
                        f"เก็บไม่สำเร็จ รอลองใหม่อีก "
                        f"{retry_in} วินาที"
                    )
                    return
                self.last_diamond_storage_time = now
                self.diamond_preview_signal.emit(
                    slot_img, val, True,
                    f"ครบ {self.diamond_interval_minutes} นาที กำลังเก็บเพชรเข้ารถ"
                )
                if self.execute_store_diamonds_sequence():
                    self.diamond_cycle_started_at = time.time()
                    self.log_signal.emit(
                        f"[ระบบเก็บเพชร] ขั้นต่อไป: "
                        f"เก็บเข้ารถรอบใหม่ในอีก "
                        f"{self.diamond_interval_minutes} นาที"
                    )
            else:
                self.diamond_preview_signal.emit(
                    slot_img, val, False,
                    f"โหมดจับเวลา: เหลือ {remaining // 60}:{remaining % 60:02d} นาที"
                )
        else:
            val = diamond_result[2] if diamond_result else 0.0
            self.diamond_preview_signal.emit(
                np.zeros((10, 10, 3), dtype=np.uint8),
                val, False,
                f"โหมดจับเวลา: ยังไม่พบเพชร (เหลือ {remaining // 60}:{remaining % 60:02d} นาที)"
            )

    def check_and_run_no_car_full_mode(self):
        """Stop and notify once after confirming the exact 40/40 capture."""
        bg_img = self.capture_background(self.hwnd)
        if bg_img is None:
            return
        h_img, w_img = bg_img.shape[:2]
        scaled_bag = self.get_scaled_region(self.bag_region)
        default_x = (scaled_bag[0] / w_img, (scaled_bag[0] + scaled_bag[2]) / w_img) if scaled_bag else (0.33, 0.85)
        default_y = (max(0.24, scaled_bag[1] / h_img), (scaled_bag[1] + scaled_bag[3]) / h_img) if scaled_bag else (0.24, 0.90)
        dia_x, dia_y = self.get_region_ranges(
            self.diamond_search_region, w_img, h_img, default_x, default_y
        )
        full_result = self.find_image(
            bg_img, "templates/diamond_full.png", 0.88,
            x_range=dia_x, y_range=dia_y
        )
        if full_result and full_result[0] is not None:
            if full_result[1] < int(h_img * 0.24) and full_result[0] > int(w_img * 0.65):
                full_result = None
        if full_result and full_result[0] is not None:
            dx, dy, val = full_result
            template = cv2.imread(self.resolve_template_path("templates/diamond_full.png"))
            th, tw = template.shape[:2] if template is not None else (86, 86)
            x0, x1 = max(0, dx - tw // 2), min(w_img, dx + tw // 2)
            y0, y1 = max(0, dy - th // 2), min(h_img, dy + th // 2)
            slot_img = bg_img[y0:y1, x0:x1]
            self.diamond_full_streak += 1
            confirmed = self.diamond_full_streak >= 2
            status = "พบ 40/40 กำลังยืนยันภาพซ้ำ"
            if confirmed:
                status = "เพชรเต็ม 40/40 — หยุดฟาร์มแล้ว"
            self.diamond_preview_signal.emit(slot_img, val, confirmed, status)
            if confirmed and not self.diamond_full_notified:
                self.diamond_full_notified = True
                self.is_running = False
                self.running_state_signal.emit(False)
                self.log_signal.emit("[ระบบเพชร] ตรวจพบ 40/40 หยุดฟาร์มโหมดไม่มีรถ")
                self.send_diamond_full_webhook()
        else:
            self.diamond_full_streak = 0
            self.diamond_full_notified = False
            val = full_result[2] if full_result else 0.0
            self.diamond_preview_signal.emit(
                np.zeros((10, 10, 3), dtype=np.uint8),
                val, False, "โหมดไม่มีรถ: รอเพชรเต็ม 40/40"
            )

    def execute_remote_check_bag(self):
        """Open inventory, capture screen and return gold/diamond status."""
        try:
            orig_pos = self.activate_game_window()
            if orig_pos is None:
                return {
                    "success": False,
                    "status_info": "ไม่สามารถโฟกัส FiveM ได้",
                    "gold_info": "ไม่ทราบ",
                }

            if not self.is_inventory_open():
                self.ensure_inventory_open("[Discord Remote]")
                time.sleep(0.8)

            bg_img = self.capture_background(self.hwnd)
            if bg_img is None:
                return {
                    "success": False,
                    "status_info": "จับภาพ FiveM ไม่สำเร็จ",
                    "gold_info": "ไม่ทราบ",
                }

            gold_info = f"เป้าหมายทิ้ง: {self.gold_discard_target}/40 (ประเมินทองปัจจุบัน: {self.gold_estimated_count})"
            status_info = "🟢 กำลังฟาร์ม" if self.is_running else "🔴 หยุดพัก"

            temp_path = get_writable_path("discord_bag_capture.png")
            cv2.imwrite(temp_path, bg_img)

            if orig_pos:
                try:
                    win32api.SetCursorPos(orig_pos)
                except Exception:
                    pass

            return {
                "success": True,
                "image_path": temp_path,
                "gold_info": gold_info,
                "status_info": status_info,
            }
        except Exception as error:
            return {
                "success": False,
                "status_info": f"ข้อผิดพลาด: {error}",
                "gold_info": "ผิดพลาด",
            }

    def execute_remote_close_bag(self):
        """Press T to close inventory/chat and capture confirmation screenshot."""
        try:
            if not self.hwnd:
                self.hwnd = self.get_window_hwnd(WINDOW_NAME)
            if not self.hwnd:
                return {"success": False, "message": "ไม่พบหน้าต่าง FiveM กรุณาเปิดเกมก่อนสั่งปิดกระเป๋า"}

            self.log_signal.emit("[ระบบปิดกระเป๋า] 🚪 กำลังกดปุ่ม T เพื่อปิดกระเป๋า...")
            self.activate_game_window()
            time.sleep(0.2)

            self.send_game_key("t", duration=0.20)
            time.sleep(0.6)

            proof_path = get_writable_path("discord_close_bag_capture.png")
            final_img = self.capture_background(self.hwnd)
            if final_img is not None:
                cv2.imwrite(proof_path, final_img)

            self.log_signal.emit("[ระบบปิดกระเป๋า] ✅ กดปุ่ม T ปิดกระเป๋าเรียบร้อยแล้ว!")
            return {
                "success": True,
                "message": "กดปุ่ม T ปิดกระเป๋าเรียบร้อยแล้ว!",
                "image_path": proof_path if os.path.isfile(proof_path) else None,
            }
        except Exception as error:
            return {"success": False, "message": f"เกิดข้อผิดพลาดในการกด T ปิดกระเป๋า: {error}"}

    def execute_remote_discard_gold(self):
        """Open inventory, click All and Confirm to discard gold, then resume farming."""
        try:
            orig_pos = self.activate_game_window()
            if orig_pos is None:
                return {"success": False, "message": "ไม่สามารถโฟกัส FiveM ได้"}

            if not self.is_inventory_open():
                self.ensure_inventory_open("[Discord Remote]")
                time.sleep(0.8)

            bg_img = self.capture_background(self.hwnd)
            if bg_img is None:
                return {"success": False, "message": "จับภาพ FiveM ไม่สำเร็จ"}

            h_img, w_img, _ = bg_img.shape
            all_x, all_y = self.get_region_ranges(
                self.all_search_region, w_img, h_img, (0.35, 0.65), (0.35, 0.75)
            )
            all_result = self.find_image(
                bg_img,
                TEMPLATES["all"],
                self.thresholds["all"],
                x_range=all_x,
                y_range=all_y,
            )
            if all_result and all_result[0] is not None:
                x_all, y_all, _ = all_result
                self.bg_click(self.hwnd, x_all, y_all)
                time.sleep(0.8)

                bg_conf = self.capture_background(self.hwnd)
                if bg_conf is not None:
                    conf_x, conf_y = self.get_region_ranges(
                        self.confirm_search_region,
                        w_img,
                        h_img,
                        (0.35, 0.65),
                        (0.35, 0.75),
                    )
                    conf_res = self.find_image(
                        bg_conf,
                        TEMPLATES["confirm"],
                        self.thresholds["confirm"],
                        x_range=conf_x,
                        y_range=conf_y,
                    )
                    if conf_res and conf_res[0] is not None:
                        x_c, y_c, _ = conf_res
                        self.bg_click(self.hwnd, x_c, y_c)
                        time.sleep(self.delays["confirm"])

            self.choose_next_gold_target()
            time.sleep(1.0)
            self.resume_farming_after_inventory()

            bg_after = self.capture_background(self.hwnd)
            temp_path = get_writable_path("discord_discard_result.png")
            if bg_after is not None:
                cv2.imwrite(temp_path, bg_after)

            if orig_pos:
                try:
                    win32api.SetCursorPos(orig_pos)
                except Exception:
                    pass

            return {
                "success": True,
                "message": (
                    f"ทิ้งทองสำเร็จและเริ่มฟาร์มต่อเรียบร้อย! "
                    f"(เป้าหมายรอบใหม่: {self.gold_discard_target}/40)"
                ),
                "image_path": temp_path if os.path.isfile(temp_path) else None,
            }
        except Exception as error:
            return {"success": False, "message": f"เกิดข้อผิดพลาด: {error}"}

    def execute_remote_screenshot(self):
        """Capture and return the current FiveM screen image path."""
        try:
            bg_img = self.capture_background(self.hwnd)
            if bg_img is None:
                return {"success": False, "image_path": None}
            temp_path = get_writable_path("discord_screen_capture.png")
            cv2.imwrite(temp_path, bg_img)
            return {"success": True, "image_path": temp_path}
        except Exception:
            return {"success": False, "image_path": None}

    def execute_remote_store_diamonds(self):
        """Execute the full diamond storing sequence from Discord command."""
        try:
            success = self.execute_store_diamonds_sequence()
            bg_after = self.capture_background(self.hwnd)
            temp_path = get_writable_path("discord_store_capture.png")
            if bg_after is not None:
                cv2.imwrite(temp_path, bg_after)

            msg = "เก็บเพชรลงรถสำเร็จเรียบร้อยแล้ว!" if success else "กระบวนการเก็บเพชรเสร็จสิ้น (โปรดตรวจสอบว่าตัวละครอยู่ใกล้ท้ายรถ)"
            return {
                "success": success,
                "message": msg,
                "image_path": temp_path if os.path.isfile(temp_path) else None,
            }
        except Exception as error:
            return {"success": False, "message": f"เกิดข้อผิดพลาดในการเก็บเพชร: {error}"}

    def execute_remote_feed(self):
        """Execute the feeding sequence from Discord command."""
        try:
            self.execute_feeding_sequence(need_food=True, need_water=True)
            return {"success": True, "message": "ป้อนอาหารและน้ำให้ตัวละครเรียบร้อยแล้ว!"}
        except Exception as error:
            return {"success": False, "message": f"เกิดข้อผิดพลาดในการป้อนอาหาร: {error}"}

    def execute_remote_mark_map(self):
        """
        Execute Map Waypoint Marking sequence as requested by user:
        1. Press P (open Pause Menu Map)
        2. Press Enter (enter Map)
        3. Move mouse to right-side Legend list and use Down Arrow / Scroll to find 'Mine'
        4. Click 'Mine' + Press Enter to mark Waypoint
        5. Press P to exit map immediately
        """
        try:
            if not self.hwnd:
                self.hwnd = self.get_window_hwnd(WINDOW_NAME)
            if not self.hwnd:
                return {"success": False, "message": "ไม่พบหน้าต่าง FiveM กรุณาเปิดเกมก่อนสั่งมาร์คแมพ"}

            self.log_signal.emit("[ระบบมาร์คแมพ] 🚀 เริ่มต้นกระบวนการมาร์คแมพจุดขุด (P -> Enter -> เลื่อนหา Mine -> Enter -> P)...")
            self.activate_game_window()
            time.sleep(0.3)

            # 1. Open Map with 'P'
            self.log_signal.emit("[ระบบมาร์คแมพ] 🗺️ 1. กำลังเปิดหน้าต่างแผนที่ (กด P)...")
            self.send_game_key("P", duration=0.15)
            time.sleep(1.6)

            # 2. Press 'Enter' to enter Map view
            self.log_signal.emit("[ระบบมาร์คแมพ] 🔘 2. กำลังเข้าสู่หน้าจอแผนที่ (กด Enter)...")
            self.send_game_key("Enter", duration=0.15)
            time.sleep(0.8)

            # Move mouse away to the left side of map so it does NOT hover or click on any legend items
            geometry = self.get_client_geometry(self.hwnd)
            if geometry:
                w_client, h_client = geometry[2], geometry[3]
                safe_client_x = int(w_client * 0.30)
                safe_client_y = int(h_client * 0.50)
                screen_pt = self.client_to_screen(safe_client_x, safe_client_y)
                try:
                    win32api.SetCursorPos(screen_pt)
                    time.sleep(0.10)
                except Exception:
                    pass

            # Load user's latest exact Mine Job templates (high resolution legend row)
            clean_templates = []
            for t_file in [
                "templates/map_mine_job_exact_up.png",
                "templates/map_mine_job_text_clean.png"
            ]:
                t_path = self.resolve_template_path(t_file)
                if os.path.isfile(t_path):
                    tpl_img = cv2.imread(t_path)
                    if tpl_img is not None:
                        clean_templates.append((tpl_img, os.path.basename(t_file)))

            found_mine = False
            target_pos = None
            marked_path = get_writable_path("discord_mark_map_capture.png")

            # 3. Dynamic Up-Arrow scan (steps UPWARDS from bottom to find Mine Job)
            self.log_signal.emit("[ระบบมาร์คแมพ] ⬆️ 3. กำลังกดลูกศรขึ้น (Up Arrow) และสแกนหาแถบ 'Mine Job 🚚'...")
            for step in range(36):
                # Send 1 UP-Arrow key to move upwards
                try:
                    win32api.keybd_event(win32con.VK_UP, 0x48, 1, 0)
                    time.sleep(0.02)
                    win32api.keybd_event(win32con.VK_UP, 0x48, 1 | win32con.KEYEVENTF_KEYUP, 0)
                except Exception:
                    self.send_game_key("up", duration=0.02)

                time.sleep(0.09)

                map_img = self.capture_background(self.hwnd)
                if map_img is not None:
                    h_img, w_img = map_img.shape[:2]
                    # Check Right Legend area (65% - 100% width)
                    crop_legend = map_img[:, int(w_img * 0.65):w_img]
                    for tpl_img, t_name in clean_templates:
                        if crop_legend.shape[0] >= tpl_img.shape[0] and crop_legend.shape[1] >= tpl_img.shape[1]:
                            res = cv2.matchTemplate(crop_legend, tpl_img, cv2.TM_CCOEFF_NORMED)
                            _, max_val, _, max_loc = cv2.minMaxLoc(res)
                            if max_val >= 0.78:
                                found_mine = True
                                target_x = int(w_img * 0.65) + max_loc[0] + tpl_img.shape[1] // 2
                                target_y = max_loc[1] + tpl_img.shape[0] // 2
                                target_pos = (target_x, target_y)
                                self.log_signal.emit(f"[ระบบมาร์คแมพ] 🎯 สแกนพบแถบ 'Mine Job 🚚' สำเร็จ ({t_name} ความแม่นยำ {int(max_val * 100)}% ขั้นที่ {step+1})!")
                                break

                if found_mine:
                    break

            if not found_mine:
                self.log_signal.emit("[ระบบมาร์คแมพ] ⚠️ สแกนครบทุกแถวแล้วไม่พบ 'Mine Job' — ปิดแผนที่เพื่อความปลอดภัย")
                time.sleep(0.5)
                self.send_game_key("P", duration=0.15)
                return {
                    "success": False,
                    "message": "สแกนครบทุกแถวแล้วไม่พบแถบ Mine Job บนแผนที่"
                }

            # 4. Press Enter ONCE to mark Waypoint on Mine Job
            self.log_signal.emit("[ระบบมาร์คแมพ] 📍 4. กด Enter 1 ครั้งเพื่อปักหมุด Waypoint...")
            time.sleep(0.10)
            try:
                win32api.keybd_event(win32con.VK_RETURN, 0x1C, 0, 0)
                time.sleep(0.08)
                win32api.keybd_event(win32con.VK_RETURN, 0x1C, win32con.KEYEVENTF_KEYUP, 0)
            except Exception:
                self.send_game_key("Enter", duration=0.10)

            time.sleep(0.6)  # หน่วงเวลารอให้หมุดม่วงแสดงบนแผนที่

            # Capture screenshot proof
            final_img = self.capture_background(self.hwnd)
            if final_img is not None:
                if target_pos:
                    cv2.circle(final_img, (target_pos[0], target_pos[1]), 20, (0, 255, 0), 3)
                cv2.imwrite(marked_path, final_img)

            # 5. Press 'P' to exit map immediately
            self.log_signal.emit("[ระบบมาร์คแมพ] 🚪 5. กำลังกด P เพื่อออกจากแผนที่ทันที...")
            self.send_game_key("P", duration=0.15)
            time.sleep(0.4)

            self.log_signal.emit("[ระบบมาร์คแมพ] ✅ ปักหมุด Waypoint จุด Mine และออกจากแผนที่เรียบร้อยแล้ว!")
            return {
                "success": True,
                "message": "ปักหมุด Waypoint จุดขุด (Mine) บนแผนที่และออกจากแผนที่เรียบร้อยแล้ว!",
                "image_path": marked_path if os.path.isfile(marked_path) else None,
            }
        except Exception as error:
            try:
                self.send_game_key("P", duration=0.15)
            except Exception:
                pass
            return {"success": False, "message": f"เกิดข้อผิดพลาดในการมาร์คแมพ: {error}"}

    def execute_remote_mark_car_pound(self):
        """
        Execute Map Waypoint Marking for Point 2: Car Pound (พาวรถ 2/2):
        Pure dynamic step-by-step visual recognition.
        """
        try:
            if not self.hwnd:
                self.hwnd = self.get_window_hwnd(WINDOW_NAME)
            if not self.hwnd:
                return {"success": False, "message": "ไม่พบหน้าต่าง FiveM กรุณาเปิดเกมก่อนสั่งมาร์คแมพ"}

            self.log_signal.emit("[ระบบมาร์คแมพ] 🚀 เริ่มต้นกระบวนการมาร์คแมพจุดที่ 2 (พาวรถ Car Pound 2/2)...")
            self.activate_game_window()
            time.sleep(0.3)

            # 1. Open Map with 'P'
            self.log_signal.emit("[ระบบมาร์คแมพ] 🗺️ 1. กำลังเปิดหน้าต่างแผนที่ (กด P)...")
            self.send_game_key("P", duration=0.15)
            time.sleep(1.6)

            # 2. Press 'Enter' to enter Map view
            self.log_signal.emit("[ระบบมาร์คแมพ] 🔘 2. กำลังเข้าสู่หน้าจอแผนที่ (กด Enter)...")
            self.send_game_key("Enter", duration=0.15)
            time.sleep(0.8)

            # Move mouse away to safe position
            geometry = self.get_client_geometry(self.hwnd)
            if geometry:
                w_client, h_client = geometry[2], geometry[3]
                safe_client_x = int(w_client * 0.30)
                safe_client_y = int(h_client * 0.50)
                screen_pt = self.client_to_screen(safe_client_x, safe_client_y)
                try:
                    win32api.SetCursorPos(screen_pt)
                    time.sleep(0.10)
                except Exception:
                    pass

            # Load Car Pound templates
            car_templates = []
            for t_file in ["templates/map_car_pound_2_2.png", "templates/map_car_pound_text.png"]:
                t_path = self.resolve_template_path(t_file)
                if os.path.isfile(t_path):
                    tpl_img = cv2.imread(t_path)
                    if tpl_img is not None:
                        car_templates.append((tpl_img, os.path.basename(t_file)))

            found_car = False
            target_pos = None
            marked_path = get_writable_path("discord_mark_map_capture.png")

            # 3. Dynamic step-by-step scan for Car Pound
            self.log_signal.emit("[ระบบมาร์คแมพ] 🔍 3. กำลังสแกนตรวจจับแถบ 'Car Pound' ทีละแถว...")
            for step in range(38):
                map_img = self.capture_background(self.hwnd)
                if map_img is not None and car_templates:
                    h_img, w_img = map_img.shape[:2]
                    crop_legend = map_img[:, int(w_img * 0.60):w_img]
                    
                    for tpl_img, t_name in car_templates:
                        if crop_legend.shape[0] >= tpl_img.shape[0] and crop_legend.shape[1] >= tpl_img.shape[1]:
                            res = cv2.matchTemplate(crop_legend, tpl_img, cv2.TM_CCOEFF_NORMED)
                            _, max_val, _, max_loc = cv2.minMaxLoc(res)
                            if max_val >= 0.50:
                                found_car = True
                                target_x = int(w_img * 0.60) + max_loc[0] + tpl_img.shape[1] // 2
                                target_y = max_loc[1] + tpl_img.shape[0] // 2
                                target_pos = (target_x, target_y)
                                self.log_signal.emit(f"[ระบบมาร์คแมพ] 🎯 สแกนพบ 'Car Pound' สำเร็จ (ความแม่นยำ {int(max_val * 100)}% แถวที่ {step+1})!")
                                break

                if found_car:
                    # Switch sub-location to 2/2 using Right Arrow
                    self.log_signal.emit("[ระบบมาร์คแมพ] 🔄 ปรับเลือกเป็น Car Pound ❮ 2/2 ❯...")
                    try:
                        win32api.keybd_event(win32con.VK_RIGHT, 0x4D, 1, 0)
                        time.sleep(0.02)
                        win32api.keybd_event(win32con.VK_RIGHT, 0x4D, 1 | win32con.KEYEVENTF_KEYUP, 0)
                    except Exception:
                        self.send_game_key("right", duration=0.02)
                    time.sleep(0.30)
                    break

                # Send 1 Down-Arrow key
                try:
                    win32api.keybd_event(win32con.VK_DOWN, 0x50, 1, 0)
                    time.sleep(0.02)
                    win32api.keybd_event(win32con.VK_DOWN, 0x50, 1 | win32con.KEYEVENTF_KEYUP, 0)
                except Exception:
                    self.send_game_key("down", duration=0.02)

                time.sleep(0.08)

            if not found_car:
                self.log_signal.emit("[ระบบมาร์คแมพ] ⚠️ สแกนครบทุกแถวแล้วไม่พบ 'Car Pound' — ปิดแผนที่เพื่อความปลอดภัย")
                time.sleep(0.5)
                self.send_game_key("P", duration=0.15)
                return {
                    "success": False,
                    "message": "สแกนครบทุกแถวแล้วไม่พบแถบ Car Pound บนแผนที่"
                }

            # 4. Press Enter ONCE to mark Waypoint
            self.log_signal.emit("[ระบบมาร์คแมพ] 📍 4. กด Enter 1 ครั้งเพื่อปักหมุด Waypoint...")
            time.sleep(0.10)
            try:
                win32api.keybd_event(win32con.VK_RETURN, 0x1C, 0, 0)
                time.sleep(0.08)
                win32api.keybd_event(win32con.VK_RETURN, 0x1C, win32con.KEYEVENTF_KEYUP, 0)
            except Exception:
                self.send_game_key("Enter", duration=0.10)

            time.sleep(0.6)

            # Capture screenshot proof
            final_img = self.capture_background(self.hwnd)
            if final_img is not None:
                if target_pos:
                    cv2.circle(final_img, (target_pos[0], target_pos[1]), 20, (0, 255, 0), 3)
                cv2.imwrite(marked_path, final_img)

            # 5. Press 'P' to exit map immediately
            self.log_signal.emit("[ระบบมาร์คแมพ] 🚪 5. กำลังกด P เพื่อออกจากแผนที่ทันที...")
            self.send_game_key("P", duration=0.15)
            time.sleep(0.4)

            self.log_signal.emit("[ระบบมาร์คแมพ] ✅ ปักหมุด Waypoint พาวรถ (Car Pound 2/2) และออกจากแผนที่เรียบร้อยแล้ว!")
            return {
                "success": True,
                "message": "ปักหมุด Waypoint พาวรถ (Car Pound 2/2) บนแผนที่และออกจากแผนที่เรียบร้อยแล้ว!",
                "image_path": marked_path if os.path.isfile(marked_path) else None,
            }
        except Exception as error:
            try:
                self.send_game_key("P", duration=0.15)
            except Exception:
                pass
            return {"success": False, "message": f"เกิดข้อผิดพลาดในการมาร์คแมพพาวรถ: {error}"}

    def execute_remote_spawn_vehicle(self):
        """
        Execute Vehicle Spawn / Garage withdrawal sequence:
        1. Hold E for 2.0 seconds to open garage menu
        2. Wait for garage UI to open
        3. Scan and click car card (TALEPOD / In Garage)
        4. Scan and click 'Select Vehicle' button
        5. Capture confirmation proof
        """
        try:
            if not self.hwnd:
                self.hwnd = self.get_window_hwnd(WINDOW_NAME)
            if not self.hwnd:
                return {"success": False, "message": "ไม่พบหน้าต่าง FiveM กรุณาเปิดเกมก่อนสั่งเบิกรถ"}

            self.log_signal.emit("[ระบบเบิกรถ] 🚀 เริ่มต้นกระบวนการเบิกรถ (กด E ค้าง 2วิ -> เลือกรถ -> กด Select Vehicle)...")
            self.activate_game_window()
            time.sleep(0.3)

            # 1. Hold E for 2.0 seconds to trigger Open Garage
            self.log_signal.emit("[ระบบเบิกรถ] 🔑 1. กำลังกด E ค้าง 2.0 วินาทีเพื่อเปิดเมนูการาจ...")
            try:
                win32api.keybd_event(ord('E'), 0x12, 0, 0)
                time.sleep(2.0)
                win32api.keybd_event(ord('E'), 0x12, win32con.KEYEVENTF_KEYUP, 0)
            except Exception:
                self.send_game_key("E", duration=2.0)

            time.sleep(1.2)  # Wait for Garage NUI interface to open and render

            # Load vehicle card templates
            car_templates = []
            for t_file in [
                "templates/garage_car_card_default.png",
                "templates/garage_in_garage_badge.png"
            ]:
                t_path = self.resolve_template_path(t_file)
                if os.path.isfile(t_path):
                    tpl_img = cv2.imread(t_path)
                    if tpl_img is not None:
                        car_templates.append((tpl_img, os.path.basename(t_file)))

            # Load Select Vehicle button templates
            btn_templates = []
            for t_file in [
                "templates/garage_btn_select_vehicle.png",
                "templates/garage_select_vehicle_text.png"
            ]:
                t_path = self.resolve_template_path(t_file)
                if os.path.isfile(t_path):
                    tpl_img = cv2.imread(t_path)
                    if tpl_img is not None:
                        btn_templates.append((tpl_img, os.path.basename(t_file)))

            # 2. Scan and click car card
            self.log_signal.emit("[ระบบเบิกรถ] 🚗 2. กำลังสแกนหาการ์ดรถและคลิกเลือก...")
            car_clicked = False
            for try_idx in range(3):
                bg_img = self.capture_background(self.hwnd)
                if bg_img is not None and car_templates:
                    h_img, w_img = bg_img.shape[:2]
                    for tpl_img, t_name in car_templates:
                        if bg_img.shape[0] >= tpl_img.shape[0] and bg_img.shape[1] >= tpl_img.shape[1]:
                            res = cv2.matchTemplate(bg_img, tpl_img, cv2.TM_CCOEFF_NORMED)
                            _, max_val, _, max_loc = cv2.minMaxLoc(res)
                            if max_val >= 0.50:
                                click_x = max_loc[0] + tpl_img.shape[1] // 2
                                click_y = max_loc[1] + tpl_img.shape[0] // 2
                                screen_pt = self.client_to_screen(click_x, click_y)
                                try:
                                    win32api.SetCursorPos(screen_pt)
                                    time.sleep(0.10)
                                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                                    time.sleep(0.06)
                                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                                    self.log_signal.emit(f"[ระบบเบิกรถ] 🎯 คลิกเลือกการ์ดรถสำเร็จ ({t_name} ความแม่นยำ {int(max_val * 100)}%)!")
                                    car_clicked = True
                                    break
                                except Exception:
                                    pass
                if car_clicked:
                    break
                time.sleep(0.4)

            time.sleep(0.8)  # Wait for 'Select Vehicle' button to become active

            # 3. Scan and click 'Select Vehicle' button
            self.log_signal.emit("[ระบบเบิกรถ] 🔘 3. กำลังค้นหาและกดปุ่ม 'Select Vehicle'...")
            btn_clicked = False
            for try_idx in range(3):
                bg_img = self.capture_background(self.hwnd)
                if bg_img is not None and btn_templates:
                    for tpl_img, t_name in btn_templates:
                        if bg_img.shape[0] >= tpl_img.shape[0] and bg_img.shape[1] >= tpl_img.shape[1]:
                            res = cv2.matchTemplate(bg_img, tpl_img, cv2.TM_CCOEFF_NORMED)
                            _, max_val, _, max_loc = cv2.minMaxLoc(res)
                            if max_val >= 0.50:
                                click_x = max_loc[0] + tpl_img.shape[1] // 2
                                click_y = max_loc[1] + tpl_img.shape[0] // 2
                                screen_pt = self.client_to_screen(click_x, click_y)
                                try:
                                    win32api.SetCursorPos(screen_pt)
                                    time.sleep(0.10)
                                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                                    time.sleep(0.06)
                                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                                    self.log_signal.emit(f"[ระบบเบิกรถ] 🎯 กดปุ่ม 'Select Vehicle' สำเร็จ ({t_name} ความแม่นยำ {int(max_val * 100)}%)!")
                                    btn_clicked = True
                                    break
                                except Exception:
                                    pass
                if btn_clicked:
                    break
                time.sleep(0.4)

            time.sleep(1.0)

            # Capture screenshot proof
            proof_path = get_writable_path("discord_spawn_vehicle_capture.png")
            final_img = self.capture_background(self.hwnd)
            if final_img is not None:
                cv2.imwrite(proof_path, final_img)

            if car_clicked or btn_clicked:
                # 4. Wait 4.0 seconds after spawning car then press B to fasten seatbelt
                self.log_signal.emit("[ระบบเบิกรถ] ⏳ 4. กำลังรอรถเกิดและขึ้นรถ (4.0 วินาที)...")
                time.sleep(4.0)

                self.log_signal.emit("[ระบบเบิกรถ] 🔒 5. กำลังกด B เพื่อรัดเข็มขัดนิรภัย...")
                self.send_game_key("B", duration=0.15)
                time.sleep(0.5)

                self.log_signal.emit("[ระบบเบิกรถ] ✅ สั่งเบิกรถและรัดเข็มขัดนิรภัย (B) เรียบร้อยแล้ว!")
                return {
                    "success": True,
                    "message": "สั่งเบิกรถและรัดเข็มขัดนิรภัย (B) เรียบร้อยแล้ว!",
                    "image_path": proof_path if os.path.isfile(proof_path) else None,
                }
            else:
                self.log_signal.emit("[ระบบเบิกรถ] ⚠️ ไม่พบเมนูหรือปุ่มเบิกรถ กรุณาตรวจสอบว่าตัวละครยืนอยู่ในจุดเบิกรถหรือไม่")
                return {
                    "success": False,
                    "message": "ไม่พบเมนูหรือปุ่มเบิกรถ กรุณาตรวจสอบว่าตัวละครยืนอยู่ในจุดเบิกรถหรือไม่",
                    "image_path": proof_path if os.path.isfile(proof_path) else None,
                }
        except Exception as error:
            return {"success": False, "message": f"เกิดข้อผิดพลาดในการเบิกรถ: {error}"}

    def execute_remote_auto_drive(self):
        """
        Execute Auto Drive sequence:
        1. Press '-' (or 'ข') to open Vehicle Control menu
        2. Wait for vehicle menu to open
        3. Scan and click 'Auto Drive' button
        4. Capture confirmation proof
        """
        try:
            if not self.hwnd:
                self.hwnd = self.get_window_hwnd(WINDOW_NAME)
            if not self.hwnd:
                return {"success": False, "message": "ไม่พบหน้าต่าง FiveM กรุณาเปิดเกมก่อนสั่งขับออโต้"}

            self.log_signal.emit("[ระบบขับออโต้] 🚀 เริ่มต้นกระบวนการเปิดระบบขับออโต้ (กด '-' -> คลิก Auto Drive)...")
            self.activate_game_window()
            time.sleep(0.3)

            # 1. Press '-' (or 'ข') key to open vehicle menu
            self.log_signal.emit("[ระบบขับออโต้] 🔑 1. กำลังกดปุ่ม '-' (ข) เพื่อเปิดเมนูควบคุมรถ...")
            try:
                win32api.keybd_event(0xBD, 0x0C, 0, 0)
                time.sleep(0.08)
                win32api.keybd_event(0xBD, 0x0C, win32con.KEYEVENTF_KEYUP, 0)
            except Exception:
                self.send_game_key("-", duration=0.08)

            time.sleep(0.8)  # Wait for vehicle control menu to render

            # Load Auto Drive templates
            auto_templates = []
            for t_file in [
                "templates/car_menu_auto_drive_btn.png",
                "templates/car_menu_auto_drive_text.png",
                "templates/car_menu_start_stop.png"
            ]:
                t_path = self.resolve_template_path(t_file)
                if os.path.isfile(t_path):
                    tpl_img = cv2.imread(t_path)
                    if tpl_img is not None:
                        auto_templates.append((tpl_img, os.path.basename(t_file)))

            # 2. Scan and click Auto Drive button
            self.log_signal.emit("[ระบบขับออโต้] 🔘 2. กำลังสแกนหาปุ่ม 'Auto Drive' และคลิก...")
            btn_clicked = False
            target_pt = None
            for try_idx in range(4):
                bg_img = self.capture_background(self.hwnd)
                if bg_img is not None and auto_templates:
                    h_img, w_img = bg_img.shape[:2]
                    for tpl_img, t_name in auto_templates:
                        if bg_img.shape[0] >= tpl_img.shape[0] and bg_img.shape[1] >= tpl_img.shape[1]:
                            res = cv2.matchTemplate(bg_img, tpl_img, cv2.TM_CCOEFF_NORMED)
                            _, max_val, _, max_loc = cv2.minMaxLoc(res)
                            if max_val >= 0.50:
                                if "start_stop" in t_name:
                                    # Auto Drive is directly below START STOP
                                    click_x = max_loc[0] + tpl_img.shape[1] // 2
                                    click_y = max_loc[1] + tpl_img.shape[0] + 20
                                else:
                                    click_x = max_loc[0] + tpl_img.shape[1] // 2
                                    click_y = max_loc[1] + tpl_img.shape[0] // 2
                                
                                screen_pt = self.client_to_screen(click_x, click_y)
                                target_pt = (click_x, click_y)
                                try:
                                    win32api.SetCursorPos(screen_pt)
                                    time.sleep(0.10)
                                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                                    time.sleep(0.06)
                                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                                    self.log_signal.emit(f"[ระบบขับออโต้] 🎯 คลิกปุ่ม 'Auto Drive' สำเร็จ ({t_name} ความแม่นยำ {int(max_val * 100)}%)!")
                                    btn_clicked = True
                                    break
                                except Exception:
                                    pass
                if btn_clicked:
                    break
                time.sleep(0.3)

            time.sleep(0.8)

            # Capture screenshot proof
            proof_path = get_writable_path("discord_auto_drive_capture.png")
            final_img = self.capture_background(self.hwnd)
            if final_img is not None:
                if target_pt:
                    cv2.circle(final_img, target_pt, 22, (0, 255, 0), 3)
                cv2.imwrite(proof_path, final_img)

            if btn_clicked:
                # 3. Press ESC to close vehicle control menu
                time.sleep(0.3)
                self.log_signal.emit("[ระบบขับออโต้] 🚪 3. กำลังกด ESC เพื่อปิดเมนูควบคุมรถ...")
                self.send_game_key("Esc", duration=0.15)
                time.sleep(0.3)

                self.log_signal.emit("[ระบบขับออโต้] ✅ เปิดระบบขับรถอัตโนมัติ (Auto Drive) และปิดเมนูเรียบร้อยแล้ว!")
                return {
                    "success": True,
                    "message": "เปิดระบบขับรถอัตโนมัติ (Auto Drive) และกด ESC ปิดเมนูเรียบร้อยแล้ว!",
                    "image_path": proof_path if os.path.isfile(proof_path) else None,
                }
            else:
                self.log_signal.emit("[ระบบขับออโต้] ⚠️ ไม่พบเมนูควบคุมรถหรือปุ่ม Auto Drive กรุณาตรวจสอบว่าตัวละครนั่งอยู่ในรถหรือไม่")
                return {
                    "success": False,
                    "message": "ไม่พบเมนูควบคุมรถหรือปุ่ม Auto Drive กรุณาตรวจสอบว่าตัวละครนั่งอยู่ในรถหรือไม่",
                    "image_path": proof_path if os.path.isfile(proof_path) else None,
                }
        except Exception as error:
            return {"success": False, "message": f"เกิดข้อผิดพลาดในการเปิดระบบขับออโต้: {error}"}


    def run(self):
        while not self.is_exiting:
            try:
                # 1. Continuous HWND validity check
                if not self.hwnd or not win32gui.IsWindow(self.hwnd) or not win32gui.IsWindowVisible(self.hwnd):
                    self.hwnd = None
                    new_hwnd = self.get_window_hwnd(WINDOW_NAME)
                    if new_hwnd:
                        self.hwnd = new_hwnd
                        window_title = win32gui.GetWindowText(self.hwnd)
                        self.connection_signal.emit(True, window_title)
                        self.log_signal.emit(f"[ระบบ] 🟢 เชื่อมต่อ FiveM สำเร็จ: {window_title[:30]}")
                        self.watchdog_reconnecting = False
                        self.capture_failure_streak = 0
                    else:
                        self.connection_signal.emit(False, "กำลังค้นหาหน้าต่างเกม FiveM...")
                        time.sleep(1.5)
                        continue

                # 2. Capture background
                bg_img = self.capture_background(self.hwnd)
                if bg_img is None:
                    self.capture_failure_streak += 1
                    if self.capture_failure_streak >= 3:
                        self.reset_runtime_watchdog("จับภาพ FiveM ไม่สำเร็จ (เกมอาจกำลังรีโหลดหรือย่อจอ)")
                    time.sleep(1.0)
                    continue

                self.capture_failure_streak = 0
                if self.watchdog_reconnecting:
                    self.watchdog_reconnecting = False
                    resume_text = (
                        "บอทกลับมาทำงานต่ออัตโนมัติ 🟢"
                        if self.is_running
                        else "ระบบพร้อมแล้ว กด F9 เพื่อเริ่มบอท"
                    )
                    self.log_signal.emit(f"[Watchdog] เชื่อมต่อ FiveM ใหม่สำเร็จ — {resume_text}")

                if time.time() < self.watchdog_resume_at:
                    time.sleep(0.3)
                    continue

                self.save_latest_gold_debug_capture(bg_img)
                if self.hud_region: self.process_hud_preview(bg_img)
                if self.force_feed_test:
                    self.force_feed_test = False
                    self.execute_feeding_sequence(need_food=True, need_water=True)
                    continue
                if self.force_store_test:
                    self.force_store_test = False
                    self.execute_store_diamonds_sequence()
                    continue
                if not self.is_running:
                    time.sleep(0.5)
                    continue
                if self.recover_from_rockstar_confirmation(bg_img):
                    time.sleep(0.5)
                    continue
                match_status = {}
                h_img, w_img, _ = bg_img.shape

                if (
                    self.gold_disposal_stage
                    and time.time() - self.gold_disposal_started_at > 20.0
                ):
                    self.log_signal.emit(
                        "[ระบบทอง] ขั้นตอนทิ้งทองหมดเวลา ยกเลิกรอบนี้"
                    )
                    self.send_bug_webhook(
                        "ทิ้งทองหมดเวลา",
                        f"ค้างอยู่ที่ขั้นตอน {self.gold_disposal_stage}",
                        alert_key="gold_disposal_timeout",
                    )
                    self.gold_disposal_stage = None

                if self.gold_disposal_stage == "await_destroy":
                    dest_x, dest_y = self.get_region_ranges(
                        self.destroy_search_region,
                        w_img,
                        h_img,
                        (0.25, 0.85),
                        (0.15, 0.90)
                    )
                    destroy_result = self.find_image(
                        bg_img,
                        TEMPLATES["destroy"],
                        self.thresholds["destroy"],
                        x_range=dest_x,
                        y_range=dest_y
                    )
                    if (
                        destroy_result
                        and destroy_result[0] is not None
                    ):
                        x, y, val = destroy_result
                        match_status["destroy"] = (True, val)
                        self.match_signal.emit(match_status)
                        self.bg_click(self.hwnd, x, y)
                        self.gold_disposal_stage = "await_all"
                        time.sleep(self.delays["destroy"])
                    else:
                        time.sleep(0.3)
                    continue

                if self.gold_disposal_stage == "await_all":
                    all_x, all_y = self.get_region_ranges(
                        self.all_search_region,
                        w_img,
                        h_img,
                        (0.35, 0.65),
                        (0.35, 0.75)
                    )
                    all_result = self.find_image(
                        bg_img,
                        TEMPLATES["all"],
                        self.thresholds["all"],
                        x_range=all_x,
                        y_range=all_y
                    )
                    if all_result and all_result[0] is not None:
                        x_all, y_all, val_all = all_result
                        match_status["all"] = (True, val_all)
                        self.match_signal.emit(match_status)
                        self.bg_click(self.hwnd, x_all, y_all)
                        self.gold_disposal_stage = "await_confirm"
                        time.sleep(0.5)
                    else:
                        time.sleep(0.3)
                    continue

                if self.gold_disposal_stage == "await_confirm":
                    conf_x, conf_y = self.get_region_ranges(
                        self.confirm_search_region,
                        w_img,
                        h_img,
                        (0.35, 0.65),
                        (0.35, 0.75)
                    )
                    confirm_result = self.find_image(
                        bg_img,
                        TEMPLATES["confirm"],
                        self.thresholds["confirm"],
                        x_range=conf_x,
                        y_range=conf_y
                    )
                    if (
                        confirm_result
                        and confirm_result[0] is not None
                    ):
                        x_conf, y_conf, val_conf = confirm_result
                        match_status["confirm"] = (True, val_conf)
                        self.match_signal.emit(match_status)
                        self.bg_click(self.hwnd, x_conf, y_conf)
                        time.sleep(self.delays["confirm"])
                        was_idle_recovery = self.idle_inventory_recovery
                        self.choose_next_gold_target()
                        if was_idle_recovery:
                            self.log_signal.emit(
                                "[ระบบทอง] ทิ้งทองเสร็จแล้ว รอ 10 วินาทีก่อนออกจากกระเป๋า"
                            )
                            time.sleep(10.0)
                            self.idle_inventory_recovery = False
                            self.idle_inventory_check_until = 0.0
                            self.resume_farming_after_inventory()
                    else:
                        time.sleep(0.3)
                    continue

                match_status["all"] = (False, 0.0)
                match_status["confirm"] = (False, 0.0)
                match_status["destroy"] = (False, 0.0)

                if self.update_character_idle_state(bg_img):
                    time.sleep(0.5)
                    continue

                if (
                    self.idle_inventory_recovery
                    and time.time() > self.idle_inventory_check_until
                ):
                    self.log_signal.emit(
                        "[ระบบทอง] ตรวจแล้วไม่พบทองเต็ม กำลังปิดกระเป๋าและกลับไปฟาร์ม"
                    )
                    self.idle_inventory_recovery = False
                    self.idle_inventory_check_until = 0.0
                    self.resume_farming_after_inventory()
                    continue

                gold_ore_path, gold_text_path = "templates/gold_ore.png", "templates/gold_text.png"
                preview_ore_img, preview_text_img = np.zeros((10, 10, 3), dtype=np.uint8), np.zeros((10, 10, 3), dtype=np.uint8)
                preview_ore_score, preview_text_score, preview_target_thresh = 0.0, 0.0, self.thresholds["gold"]
                
                gold_x, gold_y = self.get_region_ranges(self.gold_search_region, w_img, h_img, (0.25, 0.85), (0.24, 0.90))
                ore_result = self.find_image(bg_img, gold_ore_path, 0.72, x_range=gold_x, y_range=gold_y)
                if ore_result and ore_result[0] is not None:
                    if ore_result[1] < int(h_img * 0.24) and ore_result[0] > int(w_img * 0.65):
                        ore_result = None
                if ore_result: preview_ore_score = ore_result[2]
                if ore_result and ore_result[0] is not None:
                    ore_x, ore_y, ore_val = ore_result
                    h_img, w_img, _ = bg_img.shape
                    abs_ore_path = self.resolve_template_path(gold_ore_path)
                    ore_tpl = cv2.imread(abs_ore_path)
                    if ore_tpl is not None:
                        ore_sx, ore_sy = self.get_template_scale(abs_ore_path, w_img, h_img)
                        ow = max(1, int(ore_tpl.shape[1] * ore_sx))
                        oh = max(1, int(ore_tpl.shape[0] * ore_sy))
                        tl_x, tl_y = max(0, min(w_img - 1, ore_x - ow // 2)), max(0, min(h_img - 1, ore_y - oh // 2))
                        preview_ore_img = bg_img[tl_y:min(h_img, tl_y+oh), tl_x:min(w_img, tl_x+ow)]

                    # Requiring a literal 95% full-crop match was brittle:
                    # anti-aliasing alone can change the score after scaling.
                    # The combined ore + count check safely allows a lower text
                    # threshold while still requiring the actual "30/40" glyphs.
                    target_thresh = max(0.76, min(float(self.thresholds["gold"]), 0.84))
                    preview_target_thresh = target_thresh
                    estimated_count = self.observe_gold_count_change(
                        bg_img, ore_x, ore_y
                    )
                    # A confirmed idle/full recovery must not wait for the
                    # normal 30-second random-disposal cooldown.  Previously
                    # its 8-second inspection window expired first.
                    can_dispose_now = (
                        self.idle_inventory_recovery
                        or time.time() >= self.gold_disposal_cooldown_until
                    )
                    random_target_reached = (
                        estimated_count is not None
                        and self.gold_discard_target is not None
                        and estimated_count >= self.gold_discard_target
                    )
                    count_result = (
                        self.find_gold_count(
                            bg_img, ore_x, ore_y, target_thresh
                        )
                        if can_dispose_now
                        else None
                    )
                    # At 40/40 the saved 30/40 template can miss its strict
                    # leading-digit sub-check by a fraction.  During idle
                    # recovery, accept a strong count-template match only when
                    # it is physically beside the already-confirmed gold icon.
                    if (
                        can_dispose_now
                        and self.idle_inventory_recovery
                        and (
                            not count_result
                            or count_result[0] is None
                        )
                    ):
                        full_text = self.find_image(
                            bg_img,
                            gold_text_path,
                            0.78,
                            x_range=gold_x,
                            y_range=gold_y,
                        )
                        if full_text and full_text[0] is not None:
                            text_x, text_y, text_score = full_text
                            max_distance = 95.0 * max(
                                w_img / 1600.0, h_img / 900.0
                            )
                            distance = float(np.hypot(
                                text_x - ore_x, text_y - ore_y
                            ))
                            if distance <= max_distance:
                                count_result = (
                                    text_x,
                                    text_y,
                                    text_score,
                                    np.zeros((10, 10, 3), dtype=np.uint8),
                                )
                                self.log_signal.emit(
                                    "[ระบบทอง] ยืนยันทองเต็ม 40/40 จากภาพสำรอง กำลังทิ้งทอง"
                                )
                    if can_dispose_now and (
                        count_result or random_target_reached
                    ):
                        if random_target_reached:
                            count_result = (
                                ore_x,
                                ore_y,
                                1.0,
                                np.zeros(
                                    (10, 10, 3),
                                    dtype=np.uint8
                                )
                            )
                            self.log_signal.emit(
                                f"[ระบบทอง] ถึงเป้าหมายสุ่ม "
                                f"{self.gold_discard_target}/40 "
                                "กำลังทิ้งทอง"
                            )
                        count_x, count_y, count_score, count_crop = count_result
                        preview_text_score = count_score
                        preview_text_img = count_crop
                        is_matched = count_x is not None
                        match_status["gold"] = (is_matched, count_score)
                        if is_matched:
                            self.match_signal.emit(match_status)
                            self.bg_right_click(self.hwnd, ore_x, ore_y)
                            self.gold_disposal_stage = "await_destroy"
                            self.gold_disposal_started_at = time.time()
                            time.sleep(self.delays["gold"])
                            self.gold_preview_signal.emit(preview_ore_img, preview_text_img, preview_ore_score, preview_text_score, preview_target_thresh)
                            continue
                    else:
                        match_status["gold"] = (False, 0.0)
                else:
                    match_status["gold"] = (False, ore_result[2] if ore_result else 0.0)
                
                self.gold_preview_signal.emit(preview_ore_img, preview_text_img, preview_ore_score, preview_text_score, preview_target_thresh)
                if self.hud_region and self.auto_feed_enabled and time.time() - self.last_hud_check_time > 10.0:
                    self.last_hud_check_time = time.time()
                    self.check_and_run_auto_feed()

                if self.auto_store_enabled and time.time() - self.last_diamond_check_time > 5.0:
                    self.last_diamond_check_time = time.time()
                    if self.diamond_mode == "no_car_full":
                        self.check_and_run_no_car_full_mode()
                    else:
                        self.check_and_run_timed_diamond_store()

                self.match_signal.emit(match_status)
                time.sleep(0.3)
            except Exception as error:
                message = f"{type(error).__name__}: {error}"
                now = time.time()
                if now - self.last_runtime_error_occurrence_time > 10.0:
                    self.runtime_error_streak = 0
                self.runtime_error_streak += 1
                self.last_runtime_error_occurrence_time = now
                if message != self.last_runtime_error or now - self.last_runtime_error_time > 10.0:
                    self.log_signal.emit(f"[ข้อผิดพลาดในลูป] {message}")
                    self.send_bug_webhook(
                        "ข้อผิดพลาดในลูป",
                        message,
                        alert_key=f"runtime:{type(error).__name__}",
                    )
                    self.last_runtime_error = message
                    self.last_runtime_error_time = now
                if self.runtime_error_streak >= 5:
                    self.reset_runtime_watchdog(
                        "เกิดข้อผิดพลาดในลูป 5 ครั้งภายใน 10 วินาที"
                    )
                time.sleep(1.5)

    def stop(self):
        self.is_exiting = True
        self.quit()
        self.wait()

# ==========================================
# MAIN GUI WINDOW
# ==========================================
class MainWindow(QMainWindow):
    hotkey_toggle_signal = Signal()
    hotkey_close_signal = Signal()

    def __init__(self):
        super().__init__()
        self.config_path = get_writable_path("config.json")
        self.private_settings_path = get_writable_path("private-settings.json")
        self.last_toggle_time = 0.0
        self.load_config()
        self.load_private_settings()
        self.setWindowTitle("ระบบมาโครทิ้งทองอัตโนมัติ (Background)")
        self.setMinimumSize(480, 360)
        if self.saved_geometry and len(self.saved_geometry) == 4:
            gx, gy, gw, gh = self.saved_geometry
            self.resize(max(480, gw), max(360, gh))
            self.move(gx, gy)
        else:
            self.resize(680, 520)
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                target_x = max(geo.left(), geo.right() - 700)
                target_y = geo.top() + 30
                self.move(target_x, target_y)
        self.setStyleSheet("""
            QMainWindow { background-color: #f8fafc; }
            QWidget { color: #334155; font-family: 'Segoe UI', sans-serif; }
            QGroupBox { border: 1px solid #cbd5e1; border-radius: 8px; margin-top: 15px; font-weight: bold; font-size: 13px; color: #475569; background-color: #ffffff; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QFrame#Card { background-color: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px; }
            QLabel { font-size: 12px; }
            QLabel#Title { font-size: 18px; font-weight: bold; color: #1e293b; }
            QPushButton { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; font-weight: bold; font-size: 11px; padding: 6px 10px; }
            QPushButton:hover { background-color: #f1f5f9; border: 1px solid #94a3b8; }
            QPushButton#StartBtn { background-color: #0d9488; border: none; border-radius: 6px; color: white; font-weight: bold; font-size: 14px; padding: 12px; }
            QPushButton#StartBtn:hover { background-color: #0f766e; }
            QPushButton#StartBtn[running="true"] { background-color: #ef4444; }
            QSlider::groove:horizontal { border: 1px solid #cbd5e1; height: 5px; background: #e2e8f0; border-radius: 2px; }
            QSlider::handle:horizontal { background: #0d9488; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }
            QSlider::sub-page:horizontal { background: #0d9488; border-radius: 2px; }
            QTextEdit#Log { background-color: #ffffff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; font-family: 'Consolas', monospace; font-size: 11px; selection-background-color: #0d9488; selection-color: #ffffff; }
            QTabWidget::pane { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; }
            QTabBar::tab { background-color: #e2e8f0; color: #475569; border: 1px solid #cbd5e1; padding: 7px 12px; }
            QTabBar::tab:selected { background-color: #ffffff; color: #0f766e; border-bottom-color: #ffffff; }
            QTabBar::tab:hover:!selected { background-color: #f1f5f9; }
            QWidget#ConfigTab, QWidget#CropsTab, QWidget#CropsScrollContent { background-color: #f8fafc; color: #334155; }
            QWidget#PreviewTab { background-color: #ffffff; color: #334155; }
            QWidget#CropsScrollViewport { background-color: #f8fafc; }
            QComboBox, QLineEdit { background-color: #ffffff; color: #334155; border: 1px solid #94a3b8; border-radius: 4px; padding: 4px 7px; selection-background-color: #0d9488; selection-color: #ffffff; }
            QComboBox:disabled, QLineEdit:disabled { background-color: #f1f5f9; color: #94a3b8; }
            QComboBox::drop-down { background-color: #f1f5f9; border-left: 1px solid #cbd5e1; width: 24px; }
            QComboBox QAbstractItemView { background-color: #ffffff; color: #334155; border: 1px solid #94a3b8; selection-background-color: #0d9488; selection-color: #ffffff; outline: none; }
            QCheckBox { color: #334155; spacing: 6px; }
            QScrollArea { background-color: #f8fafc; border: none; }
            QScrollBar:vertical { background: #f1f5f9; width: 12px; margin: 0; }
            QScrollBar::handle:vertical { background: #94a3b8; min-height: 24px; border-radius: 5px; margin: 2px; }
            QScrollBar::handle:vertical:hover { background: #64748b; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar:horizontal { background: #f1f5f9; height: 12px; margin: 0; }
            QScrollBar::handle:horizontal { background: #94a3b8; min-width: 24px; border-radius: 5px; margin: 2px; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
            QToolTip { background-color: #ffffff; color: #334155; border: 1px solid #94a3b8; padding: 4px; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        title_label = QLabel("มาโครทิ้งทอง FiveM Background")
        title_label.setObjectName("Title")

        self.update_btn = QPushButton(f"🔄 เช็คอัปเดต (v{get_current_version()})")
        self.update_btn.setStyleSheet("QPushButton { background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 12px; color: #334155; font-size: 11px; font-weight: bold; padding: 4px 10px; } QPushButton:hover { background-color: #e2e8f0; color: #0f172a; }")
        self.update_btn.clicked.connect(self.check_update_manually)

        self.status_bar = QFrame()
        self.status_bar.setStyleSheet("QFrame { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 12px; padding: 4px 12px; }")
        status_bar_layout = QHBoxLayout(self.status_bar)
        status_bar_layout.setContentsMargins(5, 2, 5, 2)
        self.status_dot = QLabel("⬤")
        self.status_dot.setStyleSheet("color: #ef4444; font-size: 10px;")
        self.status_text = QLabel("กำลังค้นหาหน้าต่างเกม FiveM...")
        status_bar_layout.addWidget(self.status_dot)
        status_bar_layout.addWidget(self.status_text)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.update_btn)
        header_layout.addWidget(self.status_bar)
        main_layout.addLayout(header_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)

        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        
        left_tabs = QTabWidget()
        
        # Tab 1: Configuration
        tab_config = QWidget()
        tab_config.setObjectName("ConfigTab")
        config_tab_main_layout = QVBoxLayout(tab_config)
        config_tab_main_layout.setContentsMargins(0, 0, 0, 0)

        config_scroll = QScrollArea()
        config_scroll.setWidgetResizable(True)
        config_scroll.setObjectName("ConfigScrollArea")
        config_scroll_content = QWidget()
        config_scroll_content.setObjectName("ConfigScrollContent")
        config_tab_layout = QVBoxLayout(config_scroll_content)
        config_tab_layout.setContentsMargins(8, 8, 8, 8)
        config_tab_layout.setSpacing(8)
        
        setup_box = QGroupBox("ตั้งค่าขอบเขตพิกัดหน้าต่างเกม")
        setup_layout = QVBoxLayout(setup_box)
        setup_layout.setSpacing(8)
        self.hud_lbl = QLabel(self.get_region_text(self.hud_region))
        self.hud_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        hud_btn = QPushButton("เลือกพื้นที่หลอดอาหาร/น้ำ")
        hud_btn.clicked.connect(self.select_hud_region)
        self.bag_lbl = QLabel(self.get_region_text(self.bag_region))
        self.bag_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        bag_btn = QPushButton("เลือกพื้นที่กระเป๋าฝั่งขวา")
        bag_btn.clicked.connect(self.select_bag_region)
        self.af_lbl = QLabel(self.get_region_text(self.auto_farm_region))
        self.af_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        af_btn = QPushButton("ลงทะเบียนปุ่มฟาร์มอัตโนมัติ (Crop)")
        af_btn.clicked.connect(self.select_auto_farm_region)
        setup_layout.addWidget(QLabel("ขอบเขตหลอดสุขภาพ (HUD):"))
        setup_layout.addWidget(self.hud_lbl)
        setup_layout.addWidget(hud_btn)
        setup_layout.addWidget(QFrame())
        setup_layout.addWidget(QLabel("ขอบเขตกระเป๋าฝั่งขวา:"))
        setup_layout.addWidget(self.bag_lbl)
        setup_layout.addWidget(bag_btn)
        setup_layout.addWidget(QFrame())
        setup_layout.addWidget(QLabel("พิกัดปุ่มเริ่มงานอัตโนมัติ:"))
        setup_layout.addWidget(self.af_lbl)
        setup_layout.addWidget(af_btn)
        config_tab_layout.addWidget(setup_box)

        sliders_box = QGroupBox("เกณฑ์ขั้นต่ำหลอดอาหาร/น้ำ (พิกเซลสีชมพู)")
        sliders_layout = QVBoxLayout(sliders_box)
        sliders_layout.addWidget(QLabel("เกณฑ์หลอดอาหาร (หากน้อยกว่าจะกิน):"))
        self.hunger_val_lbl = QLabel(f"{self.hunger_limit}")
        hunger_slider = QSlider(Qt.Horizontal)
        hunger_slider.setRange(5, 150)
        hunger_slider.setValue(self.hunger_limit)
        hunger_slider.valueChanged.connect(self.on_hunger_limit_changed)
        sliders_layout.addWidget(self.hunger_val_lbl)
        sliders_layout.addWidget(hunger_slider)
        sliders_layout.addWidget(QLabel("เกณฑ์หลอดน้ำ (หากน้อยกว่าจะดื่ม):"))
        self.thirst_val_lbl = QLabel(f"{self.thirst_limit}")
        thirst_slider = QSlider(Qt.Horizontal)
        thirst_slider.setRange(5, 150)
        thirst_slider.setValue(self.thirst_limit)
        thirst_slider.valueChanged.connect(self.on_thirst_limit_changed)
        sliders_layout.addWidget(self.thirst_val_lbl)
        sliders_layout.addWidget(thirst_slider)
        config_tab_layout.addWidget(sliders_box)

        roi_box = QGroupBox("ระบบทดสอบการทำงาน")
        roi_layout = QVBoxLayout(roi_box)
        self.test_feed_btn = QPushButton("ทดสอบระบบกินข้าว/น้ำ")
        self.test_feed_btn.setStyleSheet("QPushButton { background-color: #0284c7; border: none; color: white; font-weight: bold; font-size: 12px; border-radius: 6px; padding: 8px; }")
        self.test_feed_btn.clicked.connect(self.test_feed_sequence)
        self.test_store_btn = QPushButton("ทดสอบระบบเก็บของลงรถ")
        self.test_store_btn.setStyleSheet("QPushButton { background-color: #0d9488; border: none; color: white; font-weight: bold; font-size: 12px; border-radius: 6px; padding: 8px; }")
        self.test_store_btn.clicked.connect(self.test_store_sequence)
        roi_layout.addWidget(self.test_feed_btn)
        roi_layout.addWidget(self.test_store_btn)
        config_tab_layout.addWidget(roi_box)

        # Quick Connect Server Box
        server_box = QGroupBox("🚀 เข้าเซิร์ฟเวอร์ FiveM อัตโนมัติ (Quick Connect)")
        server_box.setObjectName("ConfigGroup")
        server_layout = QVBoxLayout(server_box)
        server_layout.setSpacing(6)
        
        server_input_row = QHBoxLayout()
        self.server_address_input = QLineEdit()
        self.server_address_input.setPlaceholderText("IP เซิร์ฟเวอร์ หรือ cfx.re/join/xxxxxx (เช่น 103.xxx.xxx:30120)")
        self.server_address_input.setText(self.server_address)
        self.server_address_input.editingFinished.connect(self.on_server_address_edited)
        self.btn_connect_server = QPushButton("🚀 เข้าเกม FiveM ทันที")
        self.btn_connect_server.setStyleSheet("QPushButton { background-color: #6366f1; border: none; color: white; font-weight: bold; font-size: 12px; border-radius: 6px; padding: 6px 12px; }")
        self.btn_connect_server.clicked.connect(lambda: self.launch_and_connect_server())
        
        server_input_row.addWidget(self.server_address_input)
        server_input_row.addWidget(self.btn_connect_server)
        server_layout.addLayout(server_input_row)
        config_tab_layout.addWidget(server_box)

        # Map Waypoint Box
        map_box = QGroupBox("📍 ระบบมาร์คแมพจุดขุด (Map Waypoint)")
        map_box.setObjectName("ConfigGroup")
        map_layout = QVBoxLayout(map_box)
        map_layout.setSpacing(6)

        self.map_mark_lbl = QLabel(
            f"พิกัดมาร์ค: {self.get_region_text(self.map_mark_coordinate)}"
            if self.map_mark_coordinate
            else "พิกัดมาร์ค: อัตโนมัติ (ตรวจจับไอคอนรถสีเหลือง 🚚)"
        )
        self.map_mark_lbl.setStyleSheet("color: #475569; font-size: 11px;")

        map_btn_row = QHBoxLayout()
        self.btn_test_mark_map = QPushButton("📍 map1 (จุดขุด)")
        self.btn_test_mark_map.setStyleSheet("QPushButton { background-color: #8b5cf6; border: none; color: white; font-weight: bold; font-size: 11px; border-radius: 6px; padding: 6px 8px; }")
        self.btn_test_mark_map.clicked.connect(self.test_mark_map_sequence)

        self.btn_test_mark_map2 = QPushButton("🚗 map2 (พาวรถ)")
        self.btn_test_mark_map2.setStyleSheet("QPushButton { background-color: #ec4899; border: none; color: white; font-weight: bold; font-size: 11px; border-radius: 6px; padding: 6px 8px; }")
        self.btn_test_mark_map2.clicked.connect(self.test_mark_map2_sequence)

        self.btn_test_spawn_car = QPushButton("🚙 เบิกรถ")
        self.btn_test_spawn_car.setStyleSheet("QPushButton { background-color: #0284c7; border: none; color: white; font-weight: bold; font-size: 11px; border-radius: 6px; padding: 6px 6px; }")
        self.btn_test_spawn_car.clicked.connect(self.test_spawn_vehicle_sequence)

        self.btn_test_auto_drive = QPushButton("🚘 ขับออโต้")
        self.btn_test_auto_drive.setStyleSheet("QPushButton { background-color: #059669; border: none; color: white; font-weight: bold; font-size: 11px; border-radius: 6px; padding: 6px 6px; }")
        self.btn_test_auto_drive.clicked.connect(self.test_auto_drive_sequence)

        self.btn_crop_map_mark = QPushButton("🎯 พิกัด")
        self.btn_crop_map_mark.setStyleSheet("QPushButton { font-size: 11px; padding: 6px 6px; }")
        self.btn_crop_map_mark.clicked.connect(self.select_map_mark_region)

        self.btn_reset_map_mark = QPushButton("🔄 ออโต้")
        self.btn_reset_map_mark.setStyleSheet("QPushButton { font-size: 11px; padding: 6px 6px; }")
        self.btn_reset_map_mark.clicked.connect(self.reset_map_mark_coordinate)

        map_btn_row.addWidget(self.btn_test_mark_map)
        map_btn_row.addWidget(self.btn_test_mark_map2)
        map_btn_row.addWidget(self.btn_test_spawn_car)
        map_btn_row.addWidget(self.btn_test_auto_drive)
        map_btn_row.addWidget(self.btn_crop_map_mark)
        map_btn_row.addWidget(self.btn_reset_map_mark)

        map_layout.addWidget(self.map_mark_lbl)
        map_layout.addLayout(map_btn_row)
        config_tab_layout.addWidget(map_box)

        toggle_box = QGroupBox("เปิด/ปิดฟังก์ชัน")
        toggle_layout = QVBoxLayout(toggle_box)
        self.auto_feed_cb = QCheckBox("ระบบกินข้าว/น้ำอัตโนมัติ")
        self.auto_feed_cb.setChecked(self.auto_feed_enabled)
        self.auto_feed_cb.toggled.connect(self.on_auto_feed_toggled)
        self.auto_store_cb = QCheckBox("เปิดระบบจัดการเพชรอัตโนมัติ")
        self.auto_store_cb.setChecked(self.auto_store_enabled)
        self.auto_store_cb.toggled.connect(self.on_auto_store_toggled)
        self.diamond_mode_combo = QComboBox()
        self.diamond_mode_combo.addItem("มีรถ: เก็บเพชรทุก 40 นาที", "car_timer")
        self.diamond_mode_combo.addItem("ไม่มีรถ: เต็ม 40/40 แล้วหยุด + แจ้ง Discord", "no_car_full")
        mode_index = self.diamond_mode_combo.findData(self.diamond_mode)
        self.diamond_mode_combo.setCurrentIndex(max(0, mode_index))
        self.diamond_mode_combo.currentIndexChanged.connect(self.on_diamond_mode_changed)
        self.webhook_input = QLineEdit()
        self.webhook_input.setEchoMode(QLineEdit.Password)
        self.webhook_input.setPlaceholderText("Discord Webhook (แจ้งเพชรเต็มและแจ้งบัค)")
        self.webhook_input.setText(self.discord_webhook_url)
        self.webhook_input.editingFinished.connect(self.on_webhook_edited)
        toggle_layout.addWidget(self.auto_feed_cb)
        toggle_layout.addWidget(self.auto_store_cb)
        toggle_layout.addWidget(QLabel("โหมดเพชร:"))
        toggle_layout.addWidget(self.diamond_mode_combo)
        toggle_layout.addWidget(self.webhook_input)
        config_tab_layout.addWidget(toggle_box)

        # Discord Remote Control Settings Group
        remote_box = QGroupBox("🎮 สั่งการระยะไกลผ่าน Discord (Discord Remote)")
        remote_box.setObjectName("ConfigGroup")
        remote_layout = QVBoxLayout(remote_box)
        remote_layout.setSpacing(6)

        self.discord_remote_cb = QCheckBox("เปิดใช้งานบอท Discord สั่งการระยะไกล")
        self.discord_remote_cb.setChecked(self.discord_remote_enabled)
        self.discord_remote_cb.stateChanged.connect(self.on_discord_remote_toggled)

        self.discord_token_input = QLineEdit()
        self.discord_token_input.setEchoMode(QLineEdit.Password)
        self.discord_token_input.setPlaceholderText("Discord Bot Token (สร้างจาก Developer Portal)")
        self.discord_token_input.setText(self.discord_bot_token)
        self.discord_token_input.editingFinished.connect(self.on_discord_remote_edited)

        self.discord_admin_input = QLineEdit()
        self.discord_admin_input.setPlaceholderText("Discord User ID เจ้าของ (เช่น 123456789012345678)")
        self.discord_admin_input.setText(self.discord_admin_id)
        self.discord_admin_input.editingFinished.connect(self.on_discord_remote_edited)

        prefix_row = QHBoxLayout()
        prefix_lbl = QLabel("Prefix คำสั่ง:")
        prefix_lbl.setStyleSheet("font-size: 11px; color: #475569; font-weight: bold;")
        self.discord_prefix_input = QLineEdit()
        self.discord_prefix_input.setPlaceholderText("เช่น ! หรือ ? หรือ !2")
        self.discord_prefix_input.setText(self.discord_command_prefix)
        self.discord_prefix_input.setFixedWidth(80)
        self.discord_prefix_input.editingFinished.connect(self.on_discord_remote_edited)
        prefix_row.addWidget(prefix_lbl)
        prefix_row.addWidget(self.discord_prefix_input)
        prefix_row.addStretch()

        remote_status_layout = QHBoxLayout()
        self.discord_status_lbl = QLabel("สถานะ: 🔴 ออฟไลน์")
        self.discord_status_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        self.discord_connect_btn = QPushButton("🔄 เชื่อมต่อใหม่")
        self.discord_connect_btn.setStyleSheet("QPushButton { font-size: 11px; padding: 3px 8px; }")
        self.discord_connect_btn.clicked.connect(self.restart_discord_bot)
        remote_status_layout.addWidget(self.discord_status_lbl)
        remote_status_layout.addStretch()
        remote_status_layout.addWidget(self.discord_connect_btn)

        remote_layout.addWidget(self.discord_remote_cb)
        remote_layout.addWidget(self.discord_token_input)
        remote_layout.addWidget(self.discord_admin_input)
        remote_layout.addLayout(prefix_row)
        remote_layout.addLayout(remote_status_layout)
        config_tab_layout.addWidget(remote_box)

        config_scroll.setWidget(config_scroll_content)
        config_tab_main_layout.addWidget(config_scroll)

        # Tab 2: Custom Crops
        tab_crops = QWidget()
        tab_crops.setObjectName("CropsTab")
        crops_tab_layout = QVBoxLayout(tab_crops)
        crops_tab_layout.setSpacing(6)
        
        crops_scroll = QScrollArea()
        crops_scroll.setWidgetResizable(True)
        crops_scroll.viewport().setObjectName("CropsScrollViewport")
        crops_scroll_content = QWidget()
        crops_scroll_content.setObjectName("CropsScrollContent")
        crops_scroll_layout = QVBoxLayout(crops_scroll_content)
        crops_scroll_layout.setSpacing(10)
        
        def create_crop_row(layout, label_text, template_name, region_key):
            row_layout = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-weight: bold; color: #475569; font-size: 11px;")
            lbl.setMinimumWidth(180)
            btn_preview = QPushButton("👁️")
            btn_preview.setFixedWidth(30)
            btn_preview.setToolTip("พรีวิวรูปที่ครอปไว้")
            btn_preview.setStyleSheet("QPushButton { font-size: 14px; padding: 2px; }")
            btn_preview.clicked.connect(lambda checked=False, tn=template_name: self.preview_template(tn))
            btn_crop = QPushButton("ครอปรูป")
            btn_crop.setStyleSheet("QPushButton { font-size: 11px; padding: 4px; }")
            btn_crop.clicked.connect(lambda checked=False, tn=template_name: self.crop_template_wizard(tn))
            btn_reg = QPushButton("พื้นที่สแกน")
            btn_reg.setStyleSheet("QPushButton { font-size: 11px; padding: 4px; background-color: #f8fafc; border: 1px solid #cbd5e1; }")
            btn_reg.clicked.connect(lambda checked=False, rk=region_key: self.select_item_search_region(rk))
            row_layout.addWidget(lbl)
            row_layout.addWidget(btn_preview)
            row_layout.addWidget(btn_crop)
            row_layout.addWidget(btn_reg)
            layout.addLayout(row_layout)
            
        g_gold = QGroupBox("🔶 หมวดฟาร์มทอง (ในกระเป๋าตัวละคร)")
        l_gold = QVBoxLayout(g_gold)
        create_crop_row(l_gold, "รูปแร่ทองคำ (ก้อนทอง):", "gold_ore.png", "gold_ore")
        create_crop_row(l_gold, "รูปตัวเลข (แร่ทอง):", "gold_text.png", "gold_text")
        create_crop_row(l_gold, "ปุ่มทำลาย:", "destroy.png", "destroy")
        create_crop_row(l_gold, "ปุ่มทั้งหมด (กระเป๋า):", "all.png", "all")
        create_crop_row(l_gold, "ปุ่มตกลง (กระเป๋า):", "confirm.png", "confirm")
        crops_scroll_layout.addWidget(g_gold)
        
        g_diamond = QGroupBox("💎 หมวดเพชร (ตรวจนับในกระเป๋า)")
        l_diamond = QVBoxLayout(g_diamond)
        create_crop_row(l_diamond, "รูปเพชร (กระเป๋าตัวละคร):", "diamond_icon.png", "diamond")
        crops_scroll_layout.addWidget(g_diamond)
        
        g_trunk = QGroupBox("🚗 หมวดเก็บลงท้ายรถ")
        l_trunk = QVBoxLayout(g_trunk)
        create_crop_row(l_trunk, "รูปเพชร (ท้ายรถ):", "diamond_trunk.png", "diamond_trunk")
        create_crop_row(l_trunk, "ปุ่มเปิดท้ายรถ:", "trunk_ready.png", "trunk_ready")
        create_crop_row(l_trunk, "ปุ่มทั้งหมด (ท้ายรถ):", "all_trunk.png", "all_trunk")
        create_crop_row(l_trunk, "ปุ่มตกลง (ท้ายรถ):", "confirm_trunk.png", "confirm_trunk")
        crops_scroll_layout.addWidget(g_trunk)
        
        g_other = QGroupBox("⚙️ หมวดอื่นๆ")
        l_other = QVBoxLayout(g_other)
        create_crop_row(l_other, "ปุ่มเริ่มงาน (Auto Farm):", "auto_farm.png", "auto_farm")
        crops_scroll_layout.addWidget(g_other)
        
        btn_reset = QPushButton("รีเซ็ตรูปภาพทั้งหมดเป็นค่าเริ่มต้น")
        btn_reset.setStyleSheet("QPushButton { background-color: #ef4444; color: white; font-weight: bold; border-radius: 4px; padding: 6px; }")
        btn_reset.clicked.connect(self.reset_all_templates)
        crops_scroll_layout.addWidget(btn_reset)
        
        crops_scroll.setWidget(crops_scroll_content)
        crops_tab_layout.addWidget(crops_scroll)
        
        left_tabs.addTab(tab_config, "ตั้งค่าพิกัด & เกณฑ์")
        left_tabs.addTab(tab_crops, "ลงทะเบียนรูปภาพ (Crop)")
        left_column.addWidget(left_tabs)

        right_panel = QVBoxLayout()
        monitors_layout = QHBoxLayout()
        self.monitor_cards = {}
        
        def create_monitor_card(name, display_name):
            card = QFrame()
            card.setObjectName("Card")
            card.setMinimumWidth(80)
            card.setMaximumHeight(85)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(6, 6, 6, 6)
            card_layout.setAlignment(Qt.AlignCenter)
            led = QLabel("⬤")
            led.setStyleSheet("color: #94a3b8; font-size: 16px;")
            lbl = QLabel(display_name)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
            conf_bar = QLabel("0.0%")
            card_layout.addWidget(led)
            card_layout.addWidget(lbl)
            card_layout.addWidget(conf_bar)
            monitors_layout.addWidget(card)
            self.monitor_cards[name] = {"led": led, "conf": conf_bar, "frame": card}

        create_monitor_card("gold", "1. ทองคำ")
        create_monitor_card("destroy", "2. ทำลาย")
        create_monitor_card("all", "3. ทั้งหมด")
        create_monitor_card("confirm", "4. ดำเนินการ")
        right_panel.addLayout(monitors_layout)
        
        self.preview_tabs = QTabWidget()
        self.hud_tab = QWidget()
        self.hud_tab.setObjectName("PreviewTab")
        hud_layout = QHBoxLayout(self.hud_tab)
        self.lbl_crop = QLabel("รอรูป...")
        self.lbl_crop.setFixedSize(90, 45)
        self.lbl_crop.setStyleSheet("border: 1px solid #cbd5e1; background-color: #f1f5f9;")
        self.lbl_mask = QLabel("รอมาร์ก...")
        self.lbl_mask.setFixedSize(90, 45)
        self.lbl_mask.setStyleSheet("border: 1px solid #cbd5e1; background-color: #f1f5f9;")
        hud_layout.addWidget(self.lbl_crop)
        hud_layout.addWidget(self.lbl_mask)
        data_layout = QVBoxLayout()
        self.lbl_hud_hunger = QLabel("หลอดอาหาร: - px")
        self.lbl_hud_thirst = QLabel("หลอดน้ำ: - px")
        self.lbl_hud_status = QLabel("สถานะ: รอดำเนินการ")
        data_layout.addWidget(self.lbl_hud_hunger)
        data_layout.addWidget(self.lbl_hud_thirst)
        data_layout.addWidget(self.lbl_hud_status)
        hud_layout.addLayout(data_layout)
        
        self.gold_tab = QWidget()
        self.gold_tab.setObjectName("PreviewTab")
        gold_layout = QHBoxLayout(self.gold_tab)
        self.lbl_gold_ore = QLabel("รอรูปทอง...")
        self.lbl_gold_ore.setFixedSize(90, 45)
        self.lbl_gold_ore.setStyleSheet("border: 1px solid #cbd5e1; background-color: #f1f5f9;")
        self.lbl_gold_text = QLabel("รอรูปเลข...")
        self.lbl_gold_text.setFixedSize(90, 45)
        self.lbl_gold_text.setStyleSheet("border: 1px solid #cbd5e1; background-color: #f1f5f9;")
        gold_layout.addWidget(self.lbl_gold_ore)
        gold_layout.addWidget(self.lbl_gold_text)
        gold_data_layout = QVBoxLayout()
        self.lbl_gold_ore_val = QLabel("การเจอก้อนทอง: - %")
        self.lbl_gold_text_val = QLabel("ความเหมือนตัวเลข: - %")
        self.lbl_gold_thresh_val = QLabel("เกณฑ์ตัดสินใจทิ้ง: - %")
        gold_data_layout.addWidget(self.lbl_gold_ore_val)
        gold_data_layout.addWidget(self.lbl_gold_text_val)
        gold_data_layout.addWidget(self.lbl_gold_thresh_val)
        gold_layout.addLayout(gold_data_layout)
        self.diamond_tab = QWidget()
        self.diamond_tab.setObjectName("PreviewTab")
        diamond_layout = QHBoxLayout(self.diamond_tab)
        self.lbl_diamond_slot = QLabel("รอรูปเพชร...")
        self.lbl_diamond_slot.setFixedSize(90, 45)
        self.lbl_diamond_slot.setStyleSheet("border: 1px solid #cbd5e1; background-color: #f1f5f9;")
        diamond_layout.addWidget(self.lbl_diamond_slot)
        diamond_data_layout = QVBoxLayout()
        self.lbl_diamond_score = QLabel("ความเหมือนรูปเพชร: - %")
        self.lbl_diamond_status = QLabel("สถานะ: รอดำเนินการ")
        diamond_data_layout.addWidget(self.lbl_diamond_score)
        diamond_data_layout.addWidget(self.lbl_diamond_status)
        diamond_layout.addLayout(diamond_data_layout)
        self.preview_tabs.addTab(self.hud_tab, "พรีวิวหลอดอาหาร/น้ำ")
        self.preview_tabs.addTab(self.gold_tab, "พรีวิวสแกนเศษทองคำ")
        self.preview_tabs.addTab(self.diamond_tab, "พรีวิวสแกนเพชร")
        right_panel.addWidget(self.preview_tabs)

        right_panel.addWidget(QLabel("บันทึกการทำงานของบอท:"))
        self.log_console = QTextEdit()
        self.log_console.setObjectName("Log")
        self.log_console.setReadOnly(True)
        right_panel.addWidget(self.log_console)
        content_layout.addLayout(left_column, 3)
        content_layout.addLayout(right_panel, 4)
        main_layout.addLayout(content_layout)

        footer_layout = QHBoxLayout()
        self.start_btn = QPushButton("เริ่มทำงานบอท [F9]")
        self.start_btn.setObjectName("StartBtn")
        self.start_btn.setProperty("running", "false")
        self.start_btn.setMinimumHeight(45)
        self.start_btn.clicked.connect(self.toggle_macro)
        instruct_lbl = QLabel("<b>คู่มือปุ่มลัด (Hotkey):</b><br>🟢 <b>[F9]</b> - เริ่ม / หยุดบอทชั่วคราว<br>🔴 <b>[F10]</b> - ปิดโปรแกรม")
        instruct_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        footer_layout.addWidget(self.start_btn, 3)
        footer_layout.addWidget(instruct_lbl, 2)
        main_layout.addLayout(footer_layout)

        self.worker = MacroWorker()
        self.sync_worker_config()
        self.worker.log_signal.connect(self.write_log)
        self.worker.connection_signal.connect(self.update_connection_status)
        self.worker.match_signal.connect(self.update_match_monitors)
        self.worker.hud_preview_signal.connect(self.update_hud_preview)
        self.worker.gold_preview_signal.connect(self.update_gold_preview)
        self.worker.diamond_preview_signal.connect(self.update_diamond_preview)
        self.worker.running_state_signal.connect(self.on_worker_running_state)
        self.worker.start()

        self.hotkey_toggle_signal.connect(self.toggle_macro)
        self.hotkey_close_signal.connect(self.close)
        keyboard.add_hotkey(
            "F9",
            self.hotkey_toggle_signal.emit,
            trigger_on_release=True
        )
        keyboard.add_hotkey(
            "F10",
            self.hotkey_close_signal.emit,
            trigger_on_release=True
        )
        self.write_log("ยินดีต้อนรับสู่แผงควบคุมระบบฟาร์มทิ้งทองอัตโนมัติ (Background)")
        self.setup_realtime_updater()

        self.discord_remote = DiscordRemoteWorker() if DiscordRemoteWorker else None
        if self.discord_remote:
            self.discord_remote.status_signal.connect(self.on_discord_remote_status)
            self.discord_remote.log_signal.connect(self.write_log)
            self.discord_remote.action_requested.connect(self.on_discord_remote_action)
            self.discord_remote.configure(
                self.discord_bot_token,
                self.discord_admin_id,
                self.discord_remote_enabled,
                prefix=self.discord_command_prefix,
            )
            if self.discord_remote_enabled and self.discord_bot_token:
                self.discord_remote.start_bot()

    def sync_worker_config(self):
        for k, v in self.thresholds.items(): self.worker.set_config(k, "threshold", v)
        for k, v in self.delays.items(): self.worker.set_config(k, "delay", v)
        self.worker.set_config("hud", "region", self.hud_region)
        self.worker.set_config("auto_farm", "region", self.auto_farm_region)
        self.worker.set_config("bag", "region", self.bag_region)
        self.worker.set_config("gold_search", "region", self.gold_search_region)
        self.worker.set_config("destroy_search", "region", self.destroy_search_region)
        self.worker.set_config("all_search", "region", self.all_search_region)
        self.worker.set_config("confirm_search", "region", self.confirm_search_region)
        self.worker.set_config("diamond_search", "region", self.diamond_search_region)
        self.worker.set_config("diamond_trunk_search", "region", self.diamond_trunk_search_region)
        self.worker.set_config("trunk_ready_search", "region", self.trunk_ready_search_region)
        self.worker.set_config("all_trunk_search", "region", self.all_trunk_search_region)
        self.worker.set_config("confirm_trunk_search", "region", self.confirm_trunk_search_region)
        self.worker.set_config("hunger", "limit", self.hunger_limit)
        self.worker.set_config("thirst", "limit", self.thirst_limit)
        self.worker.set_config("auto_feed", "toggle", self.auto_feed_enabled)
        self.worker.set_config("auto_store", "toggle", self.auto_store_enabled)
        self.worker.set_config("mode", "diamond", self.diamond_mode)
        self.worker.set_config("interval", "diamond", self.diamond_interval_minutes)
        self.worker.set_config("webhook", "diamond", self.discord_webhook_url)
        self.worker.set_config("coordinate", "map_mark", self.map_mark_coordinate)
        self.worker.set_config("ref_res", "ref_res", self.reference_resolution)
        self.worker.set_config("template_refs", "template_refs", self.template_reference_sizes)

    @Slot(str)
    def write_log(self, text):
        self.log_console.append(f"{time.strftime('[%H:%M:%S]')} {text}")
        sb = self.log_console.verticalScrollBar()
        sb.setValue(sb.maximum())

    @Slot(bool, str)
    def update_connection_status(self, connected, title):
        if connected:
            self.status_dot.setStyleSheet("color: #22c55e; font-size: 10px;")
            self.status_text.setText(f"เชื่อมต่อแล้ว: {title[:25]}...")
        else:
            self.status_dot.setStyleSheet("color: #eab308; font-size: 10px;")
            self.status_text.setText(title)

    @Slot(dict)
    def update_match_monitors(self, states):
        for name, data in states.items():
            if name in self.monitor_cards:
                matched, confidence = data
                self.monitor_cards[name]["conf"].setText(f"{confidence*100:.1f}%")
                if matched:
                    self.monitor_cards[name]["led"].setStyleSheet("color: #0d9488; font-size: 18px;")
                    self.monitor_cards[name]["frame"].setStyleSheet("border: 1px solid #0d9488; background-color: #f0fdf4;")
                else:
                    self.monitor_cards[name]["led"].setStyleSheet("color: #94a3b8; font-size: 16px;")
                    self.monitor_cards[name]["frame"].setStyleSheet("border: 1px solid #cbd5e1; background-color: #f1f5f9;")

    @Slot(np.ndarray, np.ndarray, int, int)
    def update_hud_preview(self, crop, mask, hunger_px, thirst_px):
        try:
            if hunger_px < 0 or thirst_px < 0:
                self.lbl_hud_hunger.setText("หลอดอาหาร: รอโหลดเกม...")
                self.lbl_hud_thirst.setText("หลอดน้ำ: รอโหลดเกม...")
                self.lbl_hud_status.setText("สถานะ: ⏳ กำลังรอโหลด HUD ในเกม...")
                return
            h, w, c = crop.shape
            self.lbl_crop.setPixmap(QPixmap.fromImage(QImage(crop.tobytes(), w, h, c*w, QImage.Format_BGR888)).scaled(self.lbl_crop.width(), self.lbl_crop.height(), Qt.KeepAspectRatio))
            mh, mw, mc = mask.shape
            self.lbl_mask.setPixmap(QPixmap.fromImage(QImage(mask.tobytes(), mw, mh, mc*mw, QImage.Format_BGR888)).scaled(self.lbl_mask.width(), self.lbl_mask.height(), Qt.KeepAspectRatio))
            self.lbl_hud_hunger.setText(f"หลอดอาหาร: {hunger_px} px (เกณฑ์: {self.hunger_limit})")
            self.lbl_hud_thirst.setText(f"หลอดน้ำ: {thirst_px} px (เกณฑ์: {self.thirst_limit})")
            if hunger_px < self.hunger_limit and thirst_px < self.thirst_limit: self.lbl_hud_status.setText("สถานะ: 🔴 หิว & กระหายน้ำรุนแรง!")
            elif hunger_px < self.hunger_limit: self.lbl_hud_status.setText("สถานะ: 🟡 อาหารหมดเตือนให้กิน!")
            elif thirst_px < self.thirst_limit: self.lbl_hud_status.setText("สถานะ: 🟡 น้ำหมดเตือนให้ดื่ม!")
            else: self.lbl_hud_status.setText("สถานะ: 🟢 ปกติ (กำลังฟาร์ม)")
        except Exception: pass

    @Slot(np.ndarray, np.ndarray, float, float, float)
    def update_gold_preview(self, ore_crop, text_crop, ore_score, text_score, target_thresh):
        try:
            if ore_crop.size > 100:
                h, w, c = ore_crop.shape
                self.lbl_gold_ore.setPixmap(QPixmap.fromImage(QImage(ore_crop.tobytes(), w, h, c*w, QImage.Format_BGR888)).scaled(self.lbl_gold_ore.width(), self.lbl_gold_ore.height(), Qt.KeepAspectRatio))
            if text_crop.size > 100:
                h, w, c = text_crop.shape
                self.lbl_gold_text.setPixmap(QPixmap.fromImage(QImage(text_crop.tobytes(), w, h, c*w, QImage.Format_BGR888)).scaled(self.lbl_gold_text.width(), self.lbl_gold_text.height(), Qt.KeepAspectRatio))
            self.lbl_gold_ore_val.setText(f"การเจอก้อนทอง: {ore_score*100:.1f}%")
            self.lbl_gold_text_val.setText(f"ความเหมือนตัวเลข: {text_score*100:.1f}%")
            self.lbl_gold_thresh_val.setText(f"เกณฑ์ตัดสินใจทิ้ง: {target_thresh*100:.1f}%")
        except Exception: pass

    def toggle_macro(self):
        now = time.monotonic()
        if now - self.last_toggle_time < 0.8:
            return
        self.last_toggle_time = now
        self.worker.is_running = not self.worker.is_running
        if self.worker.is_running:
            self.worker.last_activity_frame = None
            self.worker.character_idle_since = 0.0
            self.worker.last_activity_sample_time = 0.0
            self.worker.idle_inventory_recovery = False
            self.worker.idle_inventory_check_until = 0.0
            self.worker.reset_diamond_cycle()
            self.start_btn.setText("หยุดทำงานบอทชั่วคราว [F9]")
            self.start_btn.setProperty("running", "true")
        else:
            self.start_btn.setText("เริ่มทำงานบอท [F9]")
            self.start_btn.setProperty("running", "false")
        self.start_btn.style().unpolish(self.start_btn)
        self.start_btn.style().polish(self.start_btn)

    @Slot(bool)
    def on_worker_running_state(self, running):
        self.worker.is_running = running
        self.start_btn.setText(
            "หยุดทำงานบอทชั่วคราว [F9]" if running else "เริ่มทำงานบอท [F9]"
        )
        self.start_btn.setProperty("running", "true" if running else "false")
        self.start_btn.style().unpolish(self.start_btn)
        self.start_btn.style().polish(self.start_btn)

    def closeEvent(self, event):
        keyboard.unhook_all_hotkeys()
        if self.discord_remote:
            self.discord_remote.stop_bot()
        self.save_config()
        self.worker.stop()
        event.accept()

    @Slot(np.ndarray, float, bool, str)
    def update_diamond_preview(self, slot_crop, match_score, passed, status_str):
        try:
            if slot_crop.size > 100:
                h, w, c = slot_crop.shape
                self.lbl_diamond_slot.setPixmap(QPixmap.fromImage(QImage(slot_crop.tobytes(), w, h, c*w, QImage.Format_BGR888)).scaled(self.lbl_diamond_slot.width(), self.lbl_diamond_slot.height(), Qt.KeepAspectRatio))
            self.lbl_diamond_score.setText(f"ความเหมือนรูปเพชร: {match_score*100:.1f}% (เกณฑ์: 86.0%)")
            self.lbl_diamond_status.setText(f"สถานะ: {status_str}")
        except Exception: pass

    def select_bag_region(self):
        if not self.worker.hwnd: return
        self.hide()
        time.sleep(0.3)
        self.selector = RegionSelector(self.bag_region_selected, self.show)
        self.selector.show()
        
    def bag_region_selected(self, x, y, w, h):
        try:
            self.bag_region, self.reference_resolution = self.selection_to_client_region(x, y, w, h)
            self.bag_lbl.setText(self.get_region_text(self.bag_region))
            self.sync_worker_config()
            self.save_config()
        finally:
            self.show()

    def load_config(self):
        self.thresholds = {"gold": 0.84, "destroy": 0.75, "all": 0.65, "confirm": 0.65}
        self.delays = {"gold": 0.8, "destroy": 0.8, "all": 0.5, "confirm": 8.0}
        self.hud_region, self.auto_farm_region, self.bag_region = None, None, None
        self.gold_search_region = None
        self.destroy_search_region = None
        self.all_search_region = None
        self.confirm_search_region = None
        self.diamond_search_region = None
        self.diamond_trunk_search_region = None
        self.trunk_ready_search_region = None
        self.all_trunk_search_region = None
        self.confirm_trunk_search_region = None
        self.hunger_limit, self.thirst_limit = 20, 20
        self.auto_feed_enabled, self.auto_store_enabled = True, True
        self.diamond_mode = "car_timer"
        self.diamond_interval_minutes = 40
        self.discord_webhook_url = ""
        self.discord_bot_token = ""
        self.discord_admin_id = ""
        self.discord_remote_enabled = False
        self.reference_resolution = None
        self.template_reference_sizes = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "thresholds" in data:
                        self.thresholds.update(data["thresholds"])
                        if self.thresholds.get("gold", 0.84) > 0.90: self.thresholds["gold"] = 0.84
                    if "delays" in data: self.delays.update(data["delays"])
                    self.hud_region = data.get("hud_region", None)
                    self.auto_farm_region = data.get("auto_farm_region", None)
                    self.bag_region = data.get("bag_region", None)
                    self.gold_search_region = data.get("gold_search_region", None)
                    self.destroy_search_region = data.get("destroy_search_region", None)
                    self.all_search_region = data.get("all_search_region", None)
                    self.confirm_search_region = data.get("confirm_search_region", None)
                    self.diamond_search_region = data.get("diamond_search_region", None)
                    self.diamond_trunk_search_region = data.get("diamond_trunk_search_region", None)
                    self.trunk_ready_search_region = data.get("trunk_ready_search_region", None)
                    self.all_trunk_search_region = data.get("all_trunk_search_region", None)
                    self.confirm_trunk_search_region = data.get("confirm_trunk_search_region", None)
                    self.hunger_limit = data.get("hunger_limit", 20)
                    self.thirst_limit = data.get("thirst_limit", 20)
                    self.auto_feed_enabled = data.get("auto_feed_enabled", True)
                    self.auto_store_enabled = data.get("auto_store_enabled", True)
                    self.map_mark_coordinate = data.get("map_mark_coordinate", None)
                    self.diamond_mode = data.get("diamond_mode", "car_timer")
                    # Car storage now uses a fixed 40-minute interval. Ignore
                    # the legacy saved value so existing installations migrate.
                    self.diamond_interval_minutes = 40
                    self.reference_resolution = data.get("reference_resolution", None)
                    self.template_reference_sizes = data.get("template_reference_sizes", {})
                    self.saved_geometry = data.get("window_geometry", None)
            except Exception: pass

    def save_config(self):
        try:
            data = {
                "thresholds": self.thresholds, "delays": self.delays,
                "hud_region": self.hud_region, "auto_farm_region": self.auto_farm_region,
                "bag_region": self.bag_region,
                "gold_search_region": self.gold_search_region,
                "destroy_search_region": self.destroy_search_region,
                "all_search_region": self.all_search_region,
                "confirm_search_region": self.confirm_search_region,
                "diamond_search_region": self.diamond_search_region,
                "diamond_trunk_search_region": self.diamond_trunk_search_region,
                "trunk_ready_search_region": self.trunk_ready_search_region,
                "all_trunk_search_region": self.all_trunk_search_region,
                "confirm_trunk_search_region": self.confirm_trunk_search_region,
                "hunger_limit": self.hunger_limit, "thirst_limit": self.thirst_limit,
                "auto_feed_enabled": self.auto_feed_enabled, "auto_store_enabled": self.auto_store_enabled,
                "map_mark_coordinate": self.map_mark_coordinate,
                "diamond_mode": self.diamond_mode,
                "diamond_interval_minutes": self.diamond_interval_minutes,
                "reference_resolution": self.reference_resolution,
                "template_reference_sizes": self.template_reference_sizes,
                "window_geometry": [self.x(), self.y(), self.width(), self.height()]
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception: pass

    def load_private_settings(self):
        is_beta_app = (
            "beta" in sys.argv[0].lower()
            or "beta" in os.getcwd().lower()
            or os.environ.get("FIVEM_FARMING_CHANNEL") == "beta"
        )
        default_prefix = "?" if is_beta_app else "!"
        self.discord_webhook_url = getattr(self, "discord_webhook_url", "")
        self.diamond_mode = getattr(self, "diamond_mode", "car_timer")
        self.diamond_interval_minutes = 40
        self.discord_bot_token = ""
        self.discord_admin_id = ""
        self.discord_remote_enabled = False
        self.discord_command_prefix = default_prefix
        self.server_address = ""

        try:
            if os.path.exists(self.private_settings_path):
                with open(self.private_settings_path, "r", encoding="utf-8") as stream:
                    private_data = json.load(stream)
                self.discord_webhook_url = str(
                    private_data.get("discord_webhook_url", self.discord_webhook_url)
                ).strip()
                self.diamond_mode = str(
                    private_data.get("diamond_mode", self.diamond_mode)
                )
                self.diamond_interval_minutes = 40
                self.discord_bot_token = str(private_data.get("discord_bot_token", "")).strip()
                self.discord_admin_id = str(private_data.get("discord_admin_id", "")).strip()
                self.discord_remote_enabled = bool(private_data.get("discord_remote_enabled", False))
                self.discord_command_prefix = str(private_data.get("discord_command_prefix", default_prefix)).strip() or default_prefix
                self.server_address = str(private_data.get("server_address", "")).strip()
        except Exception:
            pass

    def save_private_settings(self):
        try:
            with open(self.private_settings_path, "w", encoding="utf-8") as stream:
                json.dump(
                    {
                        "discord_webhook_url": self.discord_webhook_url,
                        "diamond_mode": self.diamond_mode,
                        "diamond_interval_minutes": self.diamond_interval_minutes,
                        "discord_bot_token": self.discord_bot_token,
                        "discord_admin_id": self.discord_admin_id,
                        "discord_remote_enabled": self.discord_remote_enabled,
                        "discord_command_prefix": self.discord_command_prefix,
                        "server_address": self.server_address,
                    },
                    stream, indent=2, ensure_ascii=False
                )
        except Exception:
            pass

    def get_region_text(self, region):
        if not region: return "ยังไม่ได้ตั้งค่า"
        try:
            if len(region) == 2:
                return f"X:{region[0]}, Y:{region[1]}"
            if len(region) >= 4:
                return f"X:{region[0]}, Y:{region[1]} ({region[2]}x{region[3]})"
            return str(region)
        except Exception:
            return "ยังไม่ได้ตั้งค่า"

    def selection_to_client_region(self, x, y, w, h):
        geometry = self.worker.get_client_geometry()
        if not geometry:
            raise RuntimeError("ไม่พบพื้นที่หน้าต่างเกม")
        client_x, client_y, client_w, client_h = geometry
        x0 = max(0, min(int(x - client_x), client_w))
        y0 = max(0, min(int(y - client_y), client_h))
        x1 = max(0, min(int(x + w - client_x), client_w))
        y1 = max(0, min(int(y + h - client_y), client_h))
        if x1 - x0 < 3 or y1 - y0 < 3:
            raise RuntimeError("พื้นที่ที่เลือกไม่อยู่ในหน้าต่าง FiveM")
        return [x0, y0, x1 - x0, y1 - y0], [client_w, client_h]

    def save_template_from_game_capture(self, template_name, x, y, w, h):
        region, ref_size = self.selection_to_client_region(x, y, w, h)
        background = self.worker.capture_background(self.worker.hwnd)
        if background is None:
            raise RuntimeError("จับภาพเบื้องหลัง FiveM ไม่สำเร็จ")
        rx, ry, rw, rh = region
        crop = background[ry:ry+rh, rx:rx+rw]
        if crop.size == 0:
            raise RuntimeError("รูปที่เลือกว่างเปล่า")
        templates_dir = get_writable_path("templates")
        os.makedirs(templates_dir, exist_ok=True)
        template_path = os.path.join(templates_dir, template_name)
        if not cv2.imwrite(template_path, crop):
            raise RuntimeError("บันทึกรูปต้นแบบไม่สำเร็จ")
        self.reference_resolution = ref_size
        self.template_reference_sizes[template_name] = ref_size
        return region, ref_size

    def select_hud_region(self):
        if not self.worker.hwnd: return
        self.hide()
        time.sleep(0.3)
        self.selector = RegionSelector(self.hud_region_selected, self.show)
        self.selector.show()
        
    def hud_region_selected(self, x, y, w, h):
        try:
            self.hud_region, self.reference_resolution = self.selection_to_client_region(x, y, w, h)
            self.hud_lbl.setText(self.get_region_text(self.hud_region))
            self.sync_worker_config()
            self.save_config()
        finally:
            self.show()
        
    def select_auto_farm_region(self):
        if not self.worker.hwnd: return
        self.hide()
        time.sleep(0.3)
        self.selector = RegionSelector(self.auto_farm_region_selected, self.show)
        self.selector.show()
        
    def auto_farm_region_selected(self, x, y, w, h):
        try:
            self.auto_farm_region, self.reference_resolution = self.save_template_from_game_capture("auto_farm.png", x, y, w, h)
            self.af_lbl.setText(self.get_region_text(self.auto_farm_region))
            self.sync_worker_config()
            self.save_config()
        except Exception as e:
            self.write_log(f"[!] เกิดข้อผิดพลาดในการบันทึกรูปปุ่ม: {e}")
        finally:
            self.show()

    def preview_template(self, template_name):
        writable_p = get_writable_path(os.path.join("templates", template_name))
        bundled_p = get_resource_path(os.path.join("templates", template_name))
        img_path = None
        source = ""
        if os.path.exists(writable_p):
            img_path = writable_p
            source = "(ครอปเอง)"
        elif os.path.exists(bundled_p):
            img_path = bundled_p
            source = "(ค่าเริ่มต้น)"
        if img_path is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "ไม่พบรูป", f"ไม่พบรูป {template_name}\nยังไม่ได้ครอปรูปนี้")
            return
        pixmap = QPixmap(img_path)
        if pixmap.isNull():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "โหลดรูปไม่ได้", f"ไม่สามารถโหลดรูป {template_name}")
            return
        from PySide6.QtWidgets import QDialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"พรีวิว: {template_name} {source}")
        dlg_layout = QVBoxLayout(dialog)
        info_lbl = QLabel(f"ไฟล์: {os.path.basename(img_path)}\nขนาด: {pixmap.width()}x{pixmap.height()} px\nที่มา: {source}")
        info_lbl.setStyleSheet("font-size: 11px; color: #64748b; padding: 4px;")
        dlg_layout.addWidget(info_lbl)
        img_lbl = QLabel()
        display_pixmap = pixmap.scaled(max(pixmap.width() * 3, 200), max(pixmap.height() * 3, 200), Qt.KeepAspectRatio, Qt.FastTransformation)
        img_lbl.setPixmap(display_pixmap)
        img_lbl.setAlignment(Qt.AlignCenter)
        img_lbl.setStyleSheet("border: 2px solid #cbd5e1; background-color: #1e293b; padding: 8px;")
        dlg_layout.addWidget(img_lbl)
        dialog.setMinimumSize(250, 200)
        dialog.exec()

    def crop_template_wizard(self, template_name):
        if not self.worker.hwnd: return
        self.hide()
        time.sleep(0.3)
        self.current_cropping_template = template_name
        self.selector = RegionSelector(self.template_cropped_callback, self.show)
        self.selector.show()

    def template_cropped_callback(self, x, y, w, h):
        try:
            region, _ = self.save_template_from_game_capture(self.current_cropping_template, x, y, w, h)
            self.sync_worker_config()
            self.save_config()
            self.write_log(f"บันทึกเทมเพลต {self.current_cropping_template} ขนาด {region[2]}x{region[3]} สำเร็จ!")
        except Exception as e:
            self.write_log(f"เกิดข้อผิดพลาดในการครอป: {str(e)}")
        finally:
            self.show()

    def reset_all_templates(self):
        try:
            templates_dir = get_writable_path("templates")
            # In source-code mode this folder is also the only copy of the
            # templates. Deleting it would make every detector stop working.
            if not getattr(sys, "frozen", False):
                self.write_log("โหมดนี้ไม่มีรูปค่าเริ่มต้นแยกต่างหาก จึงไม่ได้ลบรูปที่ใช้งานอยู่")
                return
            if os.path.exists(templates_dir):
                import shutil
                af_p = os.path.join(templates_dir, "auto_farm.png")
                has_af = os.path.exists(af_p)
                af_data = None
                if has_af:
                    with open(af_p, 'rb') as f:
                        af_data = f.read()
                shutil.rmtree(templates_dir)
                os.makedirs(templates_dir, exist_ok=True)
                if has_af and af_data:
                    with open(af_p, 'wb') as f:
                        f.write(af_data)
            auto_farm_ref = self.template_reference_sizes.get("auto_farm.png")
            self.template_reference_sizes = {}
            if auto_farm_ref:
                self.template_reference_sizes["auto_farm.png"] = auto_farm_ref
            self.sync_worker_config()
            self.save_config()
            self.write_log("รีเซ็ตรูปภาพไอคอนทั้งหมดกลับเป็นค่าเริ่มต้น!")
        except Exception as e:
            self.write_log(f"เกิดข้อผิดพลาด: {str(e)}")

    def select_item_search_region(self, item_name):
        if not self.worker.hwnd: return
        self.hide()
        time.sleep(0.3)
        self.current_region_item = item_name
        self.selector = RegionSelector(self.item_search_region_selected, self.show)
        self.selector.show()

    def item_search_region_selected(self, x, y, w, h):
        try:
            rel_region, ref_size = self.selection_to_client_region(x, y, w, h)
            self.reference_resolution = ref_size
            
            if self.current_region_item == "gold":
                self.gold_search_region = rel_region
            elif self.current_region_item == "destroy":
                self.destroy_search_region = rel_region
            elif self.current_region_item == "all":
                self.all_search_region = rel_region
            elif self.current_region_item == "confirm":
                self.confirm_search_region = rel_region
            elif self.current_region_item == "diamond":
                self.diamond_search_region = rel_region
            elif self.current_region_item == "trunk_ready":
                self.trunk_ready_search_region = rel_region
            elif self.current_region_item == "all_trunk":
                self.all_trunk_search_region = rel_region
            elif self.current_region_item == "confirm_trunk":
                self.confirm_trunk_search_region = rel_region
            elif self.current_region_item == "gold_ore":
                self.gold_search_region = rel_region
            elif self.current_region_item == "gold_text":
                self.gold_search_region = rel_region
            elif self.current_region_item == "diamond_trunk":
                self.diamond_trunk_search_region = rel_region
            elif self.current_region_item == "auto_farm":
                self.auto_farm_region = rel_region
                self.reference_resolution = ref_size
                
            self.sync_worker_config()
            self.save_config()
            self.write_log(f"บันทึกขอบเขตการค้นหาสำหรับ {self.current_region_item} เรียบร้อยแล้ว!")
        except Exception as e:
            self.write_log(f"เกิดข้อผิดพลาดในการบันทึกขอบเขต: {str(e)}")
        finally:
            self.show()

    def on_hunger_limit_changed(self, value):
        self.hunger_limit = value
        self.hunger_val_lbl.setText(f"{value}")
        self.worker.set_config("hunger", "limit", value)
        self.save_config()

    def on_thirst_limit_changed(self, value):
        self.thirst_limit = value
        self.thirst_val_lbl.setText(f"{value}")
        self.worker.set_config("thirst", "limit", value)
        self.save_config()

    def test_feed_sequence(self):
        if self.worker.hwnd: self.worker.force_feed_test = True

    def test_store_sequence(self):
        if self.worker.hwnd: self.worker.force_store_test = True

    def on_auto_feed_toggled(self, checked):
        self.auto_feed_enabled = checked
        self.worker.set_config("auto_feed", "toggle", checked)
        self.save_config()

    def on_auto_store_toggled(self, checked):
        self.auto_store_enabled = checked
        self.worker.set_config("auto_store", "toggle", checked)
        self.save_config()

    def on_diamond_mode_changed(self, _index=None):
        self.diamond_mode = str(self.diamond_mode_combo.currentData())
        self.worker.set_config("mode", "diamond", self.diamond_mode)
        self.worker.reset_diamond_cycle()
        self.save_config()
        self.save_private_settings()

    def on_webhook_edited(self):
        self.discord_webhook_url = self.webhook_input.text().strip()
        self.worker.set_config("webhook", "diamond", self.discord_webhook_url)
        self.save_private_settings()

    def on_discord_remote_toggled(self, state):
        self.discord_remote_enabled = bool(state)
        self.save_private_settings()
        if self.discord_remote:
            self.discord_remote.configure(
                self.discord_bot_token,
                self.discord_admin_id,
                self.discord_remote_enabled,
                prefix=self.discord_command_prefix,
            )
            if self.discord_remote_enabled:
                self.discord_remote.start_bot()
            else:
                self.discord_remote.stop_bot()

    def test_mark_map_sequence(self):
        if not self.worker.hwnd:
            self.write_log("[!] ไม่พบหน้าต่าง FiveM กรุณาเปิดเกมก่อนทดสอบมาร์คแมพ")
            return
        self.write_log("[ระบบมาร์คแมพ] กำลังทดสอบปักหมุด map1 (Mine Job)...")
        threading.Thread(target=self.worker.execute_remote_mark_map, daemon=True).start()

    def test_mark_map2_sequence(self):
        if not self.worker.hwnd:
            self.write_log("[!] ไม่พบหน้าต่าง FiveM กรุณาเปิดเกมก่อนทดสอบมาร์คแมพ")
            return
        self.write_log("[ระบบมาร์คแมพ] กำลังทดสอบปักหมุด map2 (พาวรถ Car Pound 2/2)...")
        threading.Thread(target=self.worker.execute_remote_mark_car_pound, daemon=True).start()

    def test_spawn_vehicle_sequence(self):
        if not self.worker.hwnd:
            self.write_log("[!] ไม่พบหน้าต่าง FiveM กรุณาเปิดเกมก่อนทดสอบเบิกรถ")
            return
        self.write_log("[ระบบเบิกรถ] กำลังทดสอบเบิกรถ (กด E ค้าง 2วิ)...")
        threading.Thread(target=self.worker.execute_remote_spawn_vehicle, daemon=True).start()

    def test_auto_drive_sequence(self):
        if not self.worker.hwnd:
            self.write_log("[!] ไม่พบหน้าต่าง FiveM กรุณาเปิดเกมก่อนทดสอบขับออโต้")
            return
        self.write_log("[ระบบขับออโต้] กำลังทดสอบเปิดระบบขับออโต้ (กด '-' -> คลิก Auto Drive)...")
        threading.Thread(target=self.worker.execute_remote_auto_drive, daemon=True).start()

    def test_close_bag_sequence(self):
        if not self.worker.hwnd:
            self.write_log("[!] ไม่พบหน้าต่าง FiveM กรุณาเปิดเกมก่อนสั่งปิดกระเป๋า")
            return
        self.write_log("[ระบบปิดกระเป๋า] กำลังทดสอบกด T ปิดกระเป๋า...")
        threading.Thread(target=self.worker.execute_remote_close_bag, daemon=True).start()

    def select_map_mark_region(self):
        if not self.worker.hwnd: return
        self.hide()
        time.sleep(0.3)
        self.selector = RegionSelector(self.map_mark_region_selected, self.show)
        self.selector.show()

    def map_mark_region_selected(self, x, y, w, h):
        try:
            region, self.reference_resolution = self.save_template_from_game_capture("map_mine_blip.png", x, y, w, h)
            rx, ry, rw, rh = region
            self.map_mark_coordinate = [rx + rw // 2, ry + rh // 2]
            if hasattr(self, "map_mark_lbl"):
                self.map_mark_lbl.setText(f"พิกัดมาร์ค: X:{self.map_mark_coordinate[0]}, Y:{self.map_mark_coordinate[1]} (ครอปไอคอนแล้ว)")
            self.sync_worker_config()
            self.save_config()
            self.write_log(f"[ระบบมาร์คแมพ] บันทึกพิกัดและไอคอนจุดมาร์ค ({self.map_mark_coordinate[0]}, {self.map_mark_coordinate[1]}) เรียบร้อยแล้ว")
        except Exception as e:
            self.write_log(f"[!] เกิดข้อผิดพลาดในการบันทึกจุดมาร์ค: {e}")
        finally:
            self.show()

    def reset_map_mark_coordinate(self):
        self.map_mark_coordinate = None
        if hasattr(self, "map_mark_lbl"):
            self.map_mark_lbl.setText("พิกัดมาร์ค: อัตโนมัติ (ตรวจจับไอคอนรถสีเหลือง 🚚)")
        self.sync_worker_config()
        self.save_config()
        self.write_log("[ระบบมาร์คแมพ] รีเซ็ตเป็นโหมดค้นหาไอคอนอัตโนมัติเรียบร้อยแล้ว")

    def on_discord_remote_edited(self):
        self.discord_bot_token = self.discord_token_input.text().strip()
        self.discord_admin_id = self.discord_admin_input.text().strip()
        self.discord_command_prefix = self.discord_prefix_input.text().strip() or "!"
        self.save_private_settings()
        if self.discord_remote:
            self.discord_remote.configure(
                self.discord_bot_token,
                self.discord_admin_id,
                self.discord_remote_enabled,
                prefix=self.discord_command_prefix,
            )

    def on_server_address_edited(self):
        self.server_address = self.server_address_input.text().strip()
        self.save_private_settings()

    def launch_and_connect_server(self, server_address=""):
        target = str(server_address).strip() or self.server_address
        if not target and hasattr(self, "server_address_input"):
            target = self.server_address_input.text().strip()
        if not target:
            self.write_log("[ระบบเข้าเกม] ⚠️ ยังไม่ได้ระบุ IP เซิร์ฟเวอร์ หรือ ลิงก์ cfx")
            return False, "ยังไม่ได้ระบุ IP เซิร์ฟเวอร์ หรือ ลิงก์ cfx (เช่น !เข้าเกม 27.254.168.168:30120 หรือ !เข้าเกม cfx.re/join/xxxxxx)"
        
        clean_target = target.strip()
        # 1. Strip URI schemes
        if clean_target.lower().startswith("fivem://connect/"):
            clean_target = clean_target[len("fivem://connect/"):].strip()
        elif clean_target.lower().startswith("fivem://"):
            clean_target = clean_target[len("fivem://"):].strip()
        elif clean_target.lower().startswith("https://cfx.re/join/"):
            clean_target = "cfx.re/join/" + clean_target.split("cfx.re/join/")[-1].strip()
        elif clean_target.lower().startswith("http://cfx.re/join/"):
            clean_target = "cfx.re/join/" + clean_target.split("cfx.re/join/")[-1].strip()

        # 2. Strip leading F8 words like "connect " or "join "
        while True:
            lower = clean_target.lower()
            if lower.startswith("connect "):
                clean_target = clean_target[8:].strip()
            elif lower.startswith("connect:"):
                clean_target = clean_target[8:].strip()
            elif lower.startswith("connect/"):
                clean_target = clean_target[8:].strip()
            elif lower.startswith("join "):
                clean_target = clean_target[5:].strip()
            else:
                break

        clean_target = clean_target.strip("\"' ")
        self.server_address = clean_target
        if hasattr(self, "server_address_input"):
            self.server_address_input.setText(clean_target)
        self.save_private_settings()

        uri = f"fivem://connect/{clean_target}"

        self.write_log(f"[ระบบเข้าเกม] 🚀 กำลังสั่งเปิด FiveM และเชื่อมต่อไปยัง: {clean_target}")
        try:
            os.startfile(uri)
            return True, f"กำลังเปิด FiveM เพื่อเชื่อมต่อไปยัง: `{clean_target}`"
        except Exception as e:
            try:
                subprocess.Popen(["cmd", "/c", "start", "", uri], shell=True)
                return True, f"กำลังเปิด FiveM เพื่อเชื่อมต่อไปยัง: `{clean_target}`"
            except Exception as e2:
                self.write_log(f"[ระบบเข้าเกม] ❌ ไม่สามารถเปิด FiveM ได้: {e2}")
                return False, f"ไม่สามารถเปิด FiveM ได้: {e2}"

    def restart_discord_bot(self):
        self.on_discord_remote_edited()
        if not self.discord_remote:
            self.discord_status_lbl.setText("สถานะ: ❌ ระบบบอทไม่พร้อม")
            return
        self.discord_status_lbl.setText("สถานะ: 🟡 กำลังเชื่อมต่อ...")
        self.discord_remote.stop_bot()
        time.sleep(0.5)
        self.discord_remote.start_bot()

    @Slot(bool, str)
    def on_discord_remote_status(self, connected, text):
        if connected:
            self.discord_status_lbl.setText(f"สถานะ: 🟢 {text}")
            self.discord_status_lbl.setStyleSheet(
                "color: #16a34a; font-size: 11px; font-weight: bold;"
            )
        else:
            self.discord_status_lbl.setText(f"สถานะ: 🔴 {text}")
            self.discord_status_lbl.setStyleSheet(
                "color: #dc2626; font-size: 11px;"
            )

    @Slot(str, object)
    def on_discord_remote_action(self, action_name, callback):
        try:
            if action_name == "connect_server":
                payload = callback if isinstance(callback, dict) else {}
                cb = payload.get("callback")
                server_addr = str(payload.get("server", "")).strip() or self.server_address
                if not server_addr and hasattr(self, "server_address_input"):
                    server_addr = self.server_address_input.text().strip()
                if not server_addr:
                    if cb:
                        cb({"success": False, "message": "ยังไม่ได้ระบุ IP เซิร์ฟเวอร์ (เช่น !เข้าเกม 103.xxx.xxx:30120 หรือ !เข้าเกม cfx.re/join/xxxxxx)"})
                    return
                success, msg = self.launch_and_connect_server(server_addr)
                if cb:
                    cb({"success": success, "message": msg})
                return
            elif action_name == "mark_map":
                res = self.worker.execute_remote_mark_map()
                callback(res)
            elif action_name == "mark_map2":
                res = self.worker.execute_remote_mark_car_pound()
                callback(res)
            elif action_name == "spawn_vehicle":
                res = self.worker.execute_remote_spawn_vehicle()
                callback(res)
            elif action_name == "auto_drive":
                res = self.worker.execute_remote_auto_drive()
                callback(res)
            elif action_name == "check_bag":
                res = self.worker.execute_remote_check_bag()
                callback(res)
            elif action_name == "close_bag":
                res = self.worker.execute_remote_close_bag()
                callback(res)
            elif action_name == "discard_gold":
                res = self.worker.execute_remote_discard_gold()
                callback(res)
            elif action_name == "screenshot":
                res = self.worker.execute_remote_screenshot()
                callback(res)
            elif action_name == "start_macro":
                if not self.worker.is_running:
                    self.toggle_macro()
                callback({"success": True, "message": "เริ่มการทำงานของบอทแล้ว [F9]"})
            elif action_name == "stop_macro":
                if self.worker.is_running:
                    self.toggle_macro()
                callback({"success": True, "message": "หยุดพักบอทชั่วคราวแล้ว [F9]"})
            elif action_name == "feed":
                res = self.worker.execute_remote_feed()
                callback(res)
            elif action_name == "store_diamonds":
                res = self.worker.execute_remote_store_diamonds()
                callback(res)
            elif action_name == "get_status":
                running_text = (
                    "🟢 กำลังทำงาน (Farming)"
                    if self.worker.is_running
                    else "🔴 หยุดพัก (Paused)"
                )
                fivem_conn = (
                    "🟢 เชื่อมต่อแล้ว"
                    if self.worker.hwnd
                    else "🔴 ไม่พบหน้าต่าง FiveM"
                )
                gold_target = (
                    f"{self.worker.gold_discard_target}/40"
                    if self.worker.gold_discard_target
                    else "สุ่มอัตโนมัติ"
                )
                diamond_mode = (
                    "มีรถ (เก็บทุก 40 นาที)"
                    if self.diamond_mode == "car_timer"
                    else "ไม่มีรถ (หยุดเมื่อ 40/40)"
                )
                food_status = (
                    "เปิดใช้งาน" if self.auto_feed_enabled else "ปิดใช้งาน"
                )
                callback({
                    "running_text": running_text,
                    "fivem_connected": fivem_conn,
                    "gold_target": gold_target,
                    "diamond_mode": diamond_mode,
                    "food_status": food_status,
                })
            else:
                callback({
                    "success": False,
                    "message": f"ไม่รู้จักคำสั่ง: {action_name}",
                })
        except Exception as error:
            callback({"success": False, "message": f"เกิดข้อผิดพลาด: {error}"})

    def setup_realtime_updater(self):
        QTimer.singleShot(5000, self.check_update_silently)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.check_update_silently)
        self.update_timer.start(15 * 60 * 1000)

    def check_update_silently(self):
        self.silent_update_worker = RealtimeUpdateWorker(mode="check")
        self.silent_update_worker.check_finished.connect(
            lambda has_up, rem_v, err: self.on_update_checked(has_up, rem_v, err, interactive=False)
        )
        self.silent_update_worker.start()

    def check_update_manually(self):
        self.update_btn.setEnabled(False)
        self.update_btn.setText("🔄 กำลังตรวจ...")
        self.manual_update_worker = RealtimeUpdateWorker(mode="check")
        self.manual_update_worker.check_finished.connect(
            lambda has_up, rem_v, err: self.on_update_checked(has_up, rem_v, err, interactive=True)
        )
        self.manual_update_worker.start()

    def on_update_checked(self, has_update, remote_version, error_msg, interactive=False):
        cur_v = get_current_version()
        self.update_btn.setEnabled(True)
        self.update_btn.setText(f"🔄 เช็คอัปเดต (v{cur_v})")
        if has_update:
            reply = QMessageBox.question(
                self,
                "อัปเดต FiveM Farming",
                f"🎉 พบเวอร์ชันใหม่: v{remote_version}\n(เวอร์ชันปัจจุบัน: v{cur_v})\n\nต้องการดาวน์โหลดและเริ่มระบบใหม่ทันทีหรือไม่?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.perform_hot_update()
        else:
            if interactive:
                if error_msg:
                    QMessageBox.warning(self, "ตรวจสอบอัปเดต", f"ไม่สามารถตรวจสอบอัปเดตได้: {error_msg}")
                else:
                    QMessageBox.information(self, "ตรวจสอบอัปเดต", f"✅ คุณกำลังใช้งานเวอร์ชันล่าสุด (v{cur_v}) อยู่แล้วครับ")

    def perform_hot_update(self):
        self.update_btn.setEnabled(False)
        self.update_btn.setText("⏳ กำลังดาวน์โหลด...")
        self.write_log("[ระบบอัปเดต] กำลังดาวน์โหลดเวอร์ชันล่าสุดจาก GitHub...")
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(500)
        self.downloader_worker = RealtimeUpdateWorker(mode="download")
        self.downloader_worker.download_finished.connect(self.on_hot_update_finished)
        self.downloader_worker.start()

    def on_hot_update_finished(self, success, message):
        if success:
            self.write_log("[ระบบอัปเดต] ดาวน์โหลดสำเร็จ กำลังเริ่มระบบใหม่...")
            QMessageBox.information(self, "อัปเดตสำเร็จ", "🎉 อัปเดตเวอร์ชันใหม่สำเร็จแล้ว!\nโปรแกรมจะเริ่มทำงานใหม่ในทันทีครับ")
            app_dir = os.path.dirname(os.path.abspath(__file__))
            pythonw = os.path.join(app_dir, "templates", "_runtime", "pythonw.exe")
            macro_py = os.path.join(app_dir, "gui_macro.py")
            if os.path.isfile(pythonw) and os.path.isfile(macro_py):
                child_env = os.environ.copy()
                child_env["FIVEM_CAPTURE_BITBLT"] = "1"
                subprocess.Popen(
                    [pythonw, macro_py],
                    cwd=app_dir,
                    env=child_env,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                )
            else:
                subprocess.Popen([sys.executable, sys.argv[0]], cwd=app_dir)
            QApplication.quit()
            sys.exit(0)
        else:
            self.update_btn.setEnabled(True)
            self.update_btn.setText(f"🔄 เช็คอัปเดต (v{get_current_version()})")
            QMessageBox.critical(self, "อัปเดตไม่สำเร็จ", message)



def check_license_or_prompt():
    """Verify saved KeyAuth license or prompt user to enter key before running."""
    try:
        from keyauth_helper import KeyAuthClient, load_saved_key, save_key, get_hwid
    except Exception:
        # Fallback inline implementation if helper file is missing
        import hashlib, subprocess, urllib.request, urllib.parse, ssl
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ctx = ssl.create_default_context()

        def get_hwid():
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
                guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                if guid: return hashlib.sha256(str(guid).strip().encode("utf-8")).hexdigest()
            except Exception:
                pass
            try:
                cmd = subprocess.Popen("wmic csproduct get uuid", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
                out, _ = cmd.communicate()
                lines = [l.strip() for l in out.splitlines() if l.strip()]
                if len(lines) >= 2 and lines[1]: return hashlib.sha256(lines[1].encode("utf-8")).hexdigest()
            except Exception:
                pass
            fallback = f"{os.environ.get('COMPUTERNAME', 'PC')}-{os.environ.get('USERNAME', 'USER')}-FIVEM"
            return hashlib.sha256(fallback.encode("utf-8")).hexdigest()

        def get_key_storage_path():
            cwd = os.path.abspath(os.getcwd())
            app_name = "FiveM-Farming-Beta" if "Beta" in cwd or "beta" in cwd else "FiveM-Farming"
            app_d = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), app_name)
            os.makedirs(app_d, exist_ok=True)
            return os.path.join(app_d, ".license_key")

        def load_saved_key():
            p = get_key_storage_path()
            return open(p, "r", encoding="utf-8").read().strip() if os.path.isfile(p) else ""

        def save_key(k):
            try:
                open(get_key_storage_path(), "w", encoding="utf-8").write(str(k).strip())
            except Exception:
                pass

        class KeyAuthClient:
            def __init__(self):
                self.name = "Chatchai09122546's Application"
                self.ownerid = "B3zvHP2liv"
                self.version = "1.0"
                self.session_id = None

            def init(self):
                try:
                    data = urllib.parse.urlencode({"type": "init", "ver": self.version, "name": self.name, "ownerid": self.ownerid}).encode("utf-8")
                    req = urllib.request.Request("https://keyauth.win/api/1.2/", data=data, headers={"User-Agent": "KeyAuth"})
                    res = json.loads(urllib.request.urlopen(req, timeout=12, context=ctx).read().decode("utf-8"))
                    if res.get("success"):
                        self.session_id = res.get("sessionid")
                        return True, ""
                    return False, res.get("message", "Init failed")
                except Exception as e:
                    return False, str(e)

            def verify_license(self, key):
                if not key: return False, "กรุณากรอก License Key", {}
                ok, msg = self.init()
                if not ok: return False, msg, {}
                try:
                    data = urllib.parse.urlencode({"type": "license", "key": key, "hwid": get_hwid(), "sessionid": self.session_id, "name": self.name, "ownerid": self.ownerid}).encode("utf-8")
                    req = urllib.request.Request("https://keyauth.win/api/1.2/", data=data, headers={"User-Agent": "KeyAuth"})
                    res = json.loads(urllib.request.urlopen(req, timeout=15, context=ctx).read().decode("utf-8"))
                    if res.get("success"):
                        subs = res.get("info", {}).get("subscriptions", [])
                        exp = "ถาวร (Lifetime)"
                        if subs and isinstance(subs, list):
                            ts = subs[0].get("expiry")
                            if ts:
                                try:
                                    import datetime
                                    exp = datetime.datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
                                except Exception:
                                    exp = str(ts)
                        return True, "ยืนยันคีย์สำเร็จ!", {"key": key, "expiry": exp}
                    return False, res.get("message", "คีย์ไม่ถูกต้อง หรือหมดอายุ"), {}
                except Exception as e:
                    return False, f"ข้อผิดพลาด: {e}", {}

    saved_key = load_saved_key()
    client = KeyAuthClient()
    if saved_key:
        ok, msg, info = client.verify_license(saved_key)
        if ok:
            return True, info.get("expiry", "")

    from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout
    dialog = QDialog()
    dialog.setWindowTitle("FiveM Farming - ยืนยันสิทธิ์การใช้งาน (KeyAuth)")
    dialog.setFixedSize(460, 240)
    dialog.setStyleSheet(
        "QDialog { background: #f8fafc; font-family: 'Segoe UI', Tahoma, sans-serif; }"
        "QLabel { color: #0f172a; }"
        "QLineEdit { padding: 8px 12px; border: 1.5px solid #cbd5e1; border-radius: 6px; background: white; font-size: 13px; color: #1e293b; }"
        "QLineEdit:focus { border-color: #0ea5e9; }"
        "QPushButton { padding: 8px 16px; border-radius: 6px; font-weight: bold; background: #0ea5e9; color: white; border: none; font-size: 13px; }"
        "QPushButton:hover { background: #0284c7; }"
        "QPushButton#btn_copy { background: #e2e8f0; color: #334155; font-size: 11px; padding: 2px 8px; }"
        "QPushButton#btn_copy:hover { background: #cbd5e1; }"
    )
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(24, 20, 24, 20)
    layout.setSpacing(12)

    title = QLabel("🔑 กรุณากรอก License Key เพื่อเริ่มใช้งาน")
    title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0f172a;")
    layout.addWidget(title)

    hwid_row = QHBoxLayout()
    hwid_val = get_hwid()
    hwid_lbl = QLabel(f"รหัสเครื่อง (HWID): <b style='color:#0ea5e9;'>{hwid_val[:18]}...</b>")
    hwid_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
    btn_copy = QPushButton("คัดลอก HWID")
    btn_copy.setObjectName("btn_copy")
    btn_copy.setFixedHeight(24)
    btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(hwid_val))
    hwid_row.addWidget(hwid_lbl)
    hwid_row.addStretch()
    hwid_row.addWidget(btn_copy)
    layout.addLayout(hwid_row)

    key_input = QLineEdit()
    key_input.setPlaceholderText("กรอก License Key ของคุณ...")
    if saved_key:
        key_input.setText(saved_key)
    layout.addWidget(key_input)

    status_lbl = QLabel("")
    status_lbl.setStyleSheet("font-size: 11px; color: #ef4444;")
    layout.addWidget(status_lbl)

    btn = QPushButton("ยืนยัน Key (Activate)")
    layout.addWidget(btn)

    verified_expiry = [""]

    def on_activate():
        k = key_input.text().strip()
        if not k:
            status_lbl.setText("กรุณากรอก License Key")
            return
        btn.setEnabled(False)
        btn.setText("กำลังตรวจสอบ...")
        QApplication.processEvents()
        ok, msg, info = client.verify_license(k)
        btn.setEnabled(True)
        btn.setText("ยืนยัน Key (Activate)")
        if ok:
            save_key(k)
            verified_expiry[0] = info.get("expiry", "")
            dialog.accept()
        else:
            status_lbl.setText(f"❌ {msg}")

    btn.clicked.connect(on_activate)
    if dialog.exec() == QDialog.Accepted:
        return True, verified_expiry[0]
    return False, ""


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_fixed_light_theme(app)
    
    ok, expiry = check_license_or_prompt()
    if not ok:
        sys.exit(0)

    window = MainWindow()
    if expiry:
        window.setWindowTitle(f"FiveM Farming - Macro (หมดอายุ: {expiry})")
    window.show()
    force_light_title_bar(window)
    sys.exit(app.exec())
