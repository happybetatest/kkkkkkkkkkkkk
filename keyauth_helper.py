import os
import sys
import json
import ssl
import hashlib
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime

try:
    import certifi
    HTTPS_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:
    HTTPS_CONTEXT = ssl.create_default_context()

APP_NAME = "Chatchai09122546's Application"
OWNER_ID = "B3zvHP2liv"
APP_VERSION = "1.0"
API_URL = "https://keyauth.win/api/1.2/"


def get_hwid():
    """Consistent, standardized HWID for Windows."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        )
        guid, _ = winreg.QueryValueEx(key, "MachineGuid")
        if guid:
            return hashlib.sha256(str(guid).strip().encode("utf-8")).hexdigest()
    except Exception:
        pass

    try:
        cmd = subprocess.Popen("wmic csproduct get uuid", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
        out, _ = cmd.communicate()
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        if len(lines) >= 2 and lines[1]:
            return hashlib.sha256(lines[1].encode("utf-8")).hexdigest()
    except Exception:
        pass

    fallback = f"{os.environ.get('COMPUTERNAME', 'PC')}-{os.environ.get('USERNAME', 'USER')}-FIVEM"
    return hashlib.sha256(fallback.encode("utf-8")).hexdigest()


class KeyAuthClient:
    def __init__(self, name=APP_NAME, ownerid=OWNER_ID, version=APP_VERSION):
        self.name = name
        self.ownerid = ownerid
        self.version = version
        self.session_id = None
        self.initialized = False
        self.last_error = ""

    def init(self):
        try:
            post_data = urllib.parse.urlencode({
                "type": "init",
                "ver": self.version,
                "name": self.name,
                "ownerid": self.ownerid
            }).encode("utf-8")

            req = urllib.request.Request(
                API_URL,
                data=post_data,
                headers={"User-Agent": "KeyAuth"}
            )
            with urllib.request.urlopen(req, timeout=12, context=HTTPS_CONTEXT) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            if result.get("success"):
                self.session_id = result.get("sessionid")
                self.initialized = True
                return True, "เชื่อมต่อเซิร์ฟเวอร์สำเร็จ"
            else:
                msg = result.get("message", "Init failed")
                self.last_error = msg
                return False, msg
        except Exception as e:
            self.last_error = str(e)
            return False, f"ไม่สามารถเชื่อมต่อ KeyAuth: {e}"

    def verify_license(self, key):
        if not key or not str(key).strip():
            return False, "กรุณากรอก License Key", {}

        key = str(key).strip()

        if not self.initialized or not self.session_id:
            ok, msg = self.init()
            if not ok:
                return False, msg, {}

        hwid = get_hwid()
        try:
            post_data = urllib.parse.urlencode({
                "type": "license",
                "key": key,
                "hwid": hwid,
                "sessionid": self.session_id,
                "name": self.name,
                "ownerid": self.ownerid
            }).encode("utf-8")

            req = urllib.request.Request(
                API_URL,
                data=post_data,
                headers={"User-Agent": "KeyAuth"}
            )
            with urllib.request.urlopen(req, timeout=15, context=HTTPS_CONTEXT) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            if result.get("success"):
                info = result.get("info", {})
                subscriptions = info.get("subscriptions", [])
                expiry_str = "ถาวร (Lifetime)"
                if subscriptions and isinstance(subscriptions, list):
                    expiry_timestamp = subscriptions[0].get("expiry")
                    if expiry_timestamp:
                        try:
                            exp_dt = datetime.fromtimestamp(int(expiry_timestamp))
                            expiry_str = exp_dt.strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            expiry_str = str(expiry_timestamp)

                return True, "ยืนยันคีย์สำเร็จ!", {
                    "key": key,
                    "expiry": expiry_str,
                    "info": info
                }
            else:
                msg = result.get("message", "คีย์ไม่ถูกต้อง หรือหมดอายุ")
                return False, msg, {}
        except Exception as e:
            return False, f"ข้อผิดพลาดในการตรวจสอบคีย์: {e}", {}


def get_key_storage_path():
    app_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "FiveM-Farming")
    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, ".license_key")


def load_saved_key():
    try:
        path = get_key_storage_path()
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""


def save_key(key):
    try:
        path = get_key_storage_path()
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(key).strip())
        return True
    except Exception:
        return False


def clear_saved_key():
    try:
        path = get_key_storage_path()
        if os.path.isfile(path):
            os.remove(path)
    except Exception:
        pass
