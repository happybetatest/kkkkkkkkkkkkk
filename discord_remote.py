"""Standalone Discord Remote Control module for FiveM Farming Macro.

Pure Python implementation: zero external package dependencies (no discord.py needed).
Connects to Discord Gateway v10 via WebSocket (aiohttp or built-in socket/SSL)
and uses standard HTTPS REST for sending messages and screenshots.
"""

import asyncio
import json
import mimetypes
import os
import ssl
import sys
import threading
import time
import urllib.request
import urllib.parse
from uuid import uuid4

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except Exception:
    SSL_CONTEXT = ssl.create_default_context()
    SSL_CONTEXT.check_hostname = False
    SSL_CONTEXT.verify_mode = ssl.CERT_NONE

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from PySide6.QtCore import QObject, Signal, Slot


DISCORD_AVAILABLE = True  # Always True since we don't rely on external discord.py!


def send_discord_rest_message(bot_token, channel_id, content="", file_path=None, reply_to_message_id=None):
    """Send text message and/or file attachment via Discord REST API v10."""
    try:
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        headers = {
            "Authorization": f"Bot {bot_token}",
            "User-Agent": "FiveMFarmingRemote/1.3.2",
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

        with urllib.request.urlopen(req, timeout=12, context=SSL_CONTEXT) as resp:
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
            "User-Agent": "FiveMFarmingRemote/1.3.2",
        }
        req = urllib.request.Request(url, headers=headers, method="DELETE")
        with urllib.request.urlopen(req, timeout=8, context=SSL_CONTEXT):
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
        self.is_enabled = False
        self.is_running = False
        self.loop = None
        self.thread = None

    def configure(self, token, admin_id, enabled):
        self.bot_token = str(token).strip()
        self.admin_user_id = str(admin_id).strip()
        self.is_enabled = bool(enabled)

    def start_bot(self):
        if not self.bot_token:
            self.status_signal.emit(False, "ยังไม่ได้ใส่ Bot Token")
            return

        if self.is_running:
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
        except Exception as e:
            if self.is_running:
                self.status_signal.emit(False, f"ข้อผิดพลาด: {e}")
                self.log_signal.emit(f"[Discord Remote] การเชื่อมต่อขัดข้อง: {e}")
        finally:
            self.is_running = False
            self.status_signal.emit(False, "ออฟไลน์")

    async def _gateway_loop(self):
        gateway_url = "wss://gateway.discord.gg/?v=10&encoding=json"
        
        while self.is_running:
            try:
                if not AIOHTTP_AVAILABLE:
                    self.status_signal.emit(False, "จำเป็นต้องมี aiohttp")
                    return

                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(gateway_url, ssl=SSL_CONTEXT) as ws:
                        heartbeat_task = None
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
                                    heartbeat_task = asyncio.create_task(self._heartbeat(ws, interval_ms / 1000.0, seq))
                                    
                                    # Send Identify (Op 2)
                                    # Intents: 33280 = GUILD_MESSAGES (512) + DIRECT_MESSAGES (4096) + MESSAGE_CONTENT (32768) + GUILDS (1) = 37377
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
                                        self.status_signal.emit(True, f"ออนไลน์: {username}")
                                        self.log_signal.emit(f"[Discord Remote] เชื่อมต่อบอทสำเร็จ: {username}")

                                    elif t == "MESSAGE_CREATE":
                                        # Process incoming command
                                        asyncio.create_task(self._handle_message(d))

                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break

                        if heartbeat_task:
                            heartbeat_task.cancel()

            except Exception as conn_err:
                if self.is_running:
                    self.status_signal.emit(False, f"กำลังต่อใหม่ ({conn_err})")
                    self.log_signal.emit(f"[Discord Remote] หลุดการเชื่อมต่อ กำลังเชื่อมต่อใหม่ใน 5 วินาที: {conn_err}")
                    await asyncio.sleep(5.0)

    async def _heartbeat(self, ws, interval_seconds, current_seq):
        try:
            while self.is_running:
                await asyncio.sleep(interval_seconds)
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
        channel_id = str(d.get("channel_id", "")).strip()
        msg_id = str(d.get("id", "")).strip()
        content = str(d.get("content", "")).strip()

        if not content:
            return

        # Security Whitelist check: only accept commands from Admin User ID
        if self.admin_user_id and sender_id != self.admin_user_id:
            return

        cmd = content.lower()
        if cmd.startswith("!") or cmd.startswith("/"):
            cmd = cmd[1:].strip()

        # 1. HELP COMMAND
        if cmd in ("help", "คำสั่ง", "เมนู", "menu"):
            help_text = (
                "🎮 **FiveM Farming Macro — เมนูคำสั่งควบคุมระยะไกล**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "📦 `!check` หรือ `!bag` : **เปิดกระเป๋า ตรวจเช็คทอง/เพชร และถ่ายรูปส่งกลับมา**\n"
                "🗑️ `!discard` หรือ `!ทิ้งทอง` : **สั่งทิ้งทอง กดยืนยัน และกลับไปเริ่มฟาร์มต่อให้อัตโนมัติ**\n"
                "📸 `!screen` : ถ่ายภาพหน้าจอ FiveM สดๆ\n"
                "📊 `!status` : ตรวจสอบสถานะการทำงานปัจจุบัน\n"
                "🟢 `!start` : เริ่มการทำงานของบอท (F9)\n"
                "🔴 `!stop` : หยุดพักบอทชั่วคราว (F9)\n"
                "🍗 `!feed` : สั่งให้ตัวละครกินน้ำ (ช่อง 6) และอาหาร (ช่อง 7)\n"
                "💎 `!store` : สั่งให้เริ่มกระบวนการเก็บเพชรลงรถ\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "*คำสั่งทั้งหมดล็อกสิทธิ์ให้เจ้าของใช้งานได้เท่านั้น 🔒*"
            )
            send_discord_rest_message(self.bot_token, channel_id, help_text, reply_to_message_id=msg_id)
            return

        # 2. CHECK BAG & SEND SCREENSHOT
        if cmd in ("check", "bag", "กระเป๋า", "ทอง", "gold"):
            wait_id = send_discord_rest_message(
                self.bot_token, channel_id,
                "⏳ กำลังสลับไป FiveM และเปิดกระเป๋าเพื่อถ่ายรูป กรุณารอสักครู่...",
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
                    f"📦 **[ผลการตรวจสอบกระเป๋า FiveM]**\n"
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
                    "⚠️ คำสั่งหมดเวลา: ไม่สามารถเปิดกระเป๋าได้ทันเวลา กรุณาเช็คว่าเปิด FiveM อยู่หรือไม่",
                    reply_to_message_id=msg_id
                )
            return

        # 3. DISCARD GOLD & RESUME FARMING
        if cmd in ("discard", "dump", "drop", "ทิ้งทอง", "ทิ้ง"):
            wait_id = send_discord_rest_message(
                self.bot_token, channel_id,
                "🗑️ กำลังเปิดกระเป๋าเพื่อกดทิ้งทอง และเริ่มฟาร์มต่อให้อัตโนมัติ...",
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

                reply_text = f"✅ **{msg_text}**" if success else f"⚠️ **{msg_text}**"
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
                    "⚠️ คำสั่งหมดเวลา: การทิ้งทองใช้เวลานานเกินกำหนด",
                    reply_to_message_id=msg_id
                )
            return

        # 4. CAPTURE SCREEN
        if cmd in ("screen", "screenshot", "จอ", "ภาพ"):
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
                        content=f"📸 **ภาพหน้าจอ FiveM สดๆ** (<t:{int(time.time())}:T>)",
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
                        "⚠️ ไม่สามารถจับภาพหน้าจอ FiveM ได้ (หน้าต่างอาจถูกย่อ)",
                        reply_to_message_id=msg_id
                    )
            except asyncio.TimeoutError:
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    "⚠️ การถ่ายภาพหน้าจอหมดเวลา",
                    reply_to_message_id=msg_id
                )
            return

        # 5. START MACRO
        if cmd in ("start", "เริ่ม", "on"):
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("start_macro", callback)
            res = await future
            send_discord_rest_message(
                self.bot_token, channel_id,
                f"🟢 **{res.get('message', 'เริ่มการทำงานของบอทแล้ว')}**",
                reply_to_message_id=msg_id
            )
            return

        # 6. STOP MACRO
        if cmd in ("stop", "หยุด", "off", "pause"):
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("stop_macro", callback)
            res = await future
            send_discord_rest_message(
                self.bot_token, channel_id,
                f"🔴 **{res.get('message', 'หยุดพักบอทชั่วคราวแล้ว')}**",
                reply_to_message_id=msg_id
            )
            return

        # 7. FEED ACTION
        if cmd in ("feed", "กินข้าว", "กินน้ำ", "อาหาร", "กิน"):
            wait_id = send_discord_rest_message(
                self.bot_token, channel_id,
                "🍗 กำลังเริ่มกระบวนการกินน้ำ (ช่อง 6) และอาหาร (ช่อง 7)...",
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
                    f"🍗 **{res.get('message', 'ป้อนอาหารและน้ำเรียบร้อยแล้ว')}**",
                    reply_to_message_id=msg_id
                )
                if wait_id:
                    delete_discord_rest_message(self.bot_token, channel_id, wait_id)
            except asyncio.TimeoutError:
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    "⚠️ กระบวนการกินอาหารหมดเวลา",
                    reply_to_message_id=msg_id
                )
            return

        # 8. STORE DIAMONDS
        if cmd in ("store", "เก็บเพชร", "เก็บของ", "รถ"):
            wait_id = send_discord_rest_message(
                self.bot_token, channel_id,
                "💎 กำลังเริ่มกระบวนการเก็บเพชรลงท้ายรถ...",
                reply_to_message_id=msg_id
            )
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("store_diamonds", callback)

            try:
                res = await asyncio.wait_for(future, timeout=30.0)
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    f"💎 **{res.get('message', 'กระบวนการเก็บเพชรเสร็จสิ้น')}**",
                    reply_to_message_id=msg_id
                )
                if wait_id:
                    delete_discord_rest_message(self.bot_token, channel_id, wait_id)
            except asyncio.TimeoutError:
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    "⚠️ กระบวนการเก็บเพชรหมดเวลา",
                    reply_to_message_id=msg_id
                )
            return

        # 9. STATUS
        if cmd in ("status", "สถานะ", "info"):
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("get_status", callback)
            res = await future
            status_text = (
                "📊 **สถานะระบบ FiveM Farming Macro**\n"
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

        # 10. QUIT / KILL GAME (quit / exit / killgame / closegame / ออกเกม / ปิดเกม / คิลเกม / ดับเกม)
        if cmd in ("quit", "exit", "killgame", "closegame", "ออกเกม", "ปิดเกม", "คิลเกม", "ดับเกม", "kill", "forceclose"):
            wait_id = send_discord_rest_message(
                self.bot_token, channel_id,
                "🛑 กำลังสั่ง Force Quit / ปิดเกม FiveM และ GTA...",
                reply_to_message_id=msg_id
            )
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("kill_game", callback)

            try:
                res = await asyncio.wait_for(future, timeout=10.0)
                msg_text = res.get("message", "สั่งปิดเกม FiveM เรียบร้อยแล้ว")
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    content=f"🛑 **{msg_text}**",
                    reply_to_message_id=msg_id
                )
                if wait_id:
                    delete_discord_rest_message(self.bot_token, channel_id, wait_id)
            except asyncio.TimeoutError:
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    "⚠️ การสั่งปิดเกมหมดเวลา",
                    reply_to_message_id=msg_id
                )
            return

        # 11. REFRESH CONNECTION (refresh / reconnect / รีเฟรช / ต่อใหม่ / รีเฟรชเกม / รี)
        if cmd in ("refresh", "reconnect", "รีเฟรช", "ต่อใหม่", "รีเฟรชเกม", "รี"):
            wait_id = send_discord_rest_message(
                self.bot_token, channel_id,
                "🔄 กำลังรีเฟรชการเชื่อมต่อหน้าต่าง FiveM...",
                reply_to_message_id=msg_id
            )
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("refresh_game", callback)

            try:
                res = await asyncio.wait_for(future, timeout=10.0)
                msg_text = res.get("message", "รีเฟรชการเชื่อมต่อสำเร็จ")
                img_path = res.get("image_path")
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    content=f"🔄 **{msg_text}** (<t:{int(time.time())}:T>)",
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
                    "⚠️ การรีเฟรชการเชื่อมต่อหมดเวลา",
                    reply_to_message_id=msg_id
                )
            return

        # 12. RESTART GAME (restartgame / รีเกม / เข้าใหม่)
        if cmd.startswith("restartgame") or cmd.startswith("รีเกม") or cmd.startswith("เข้าใหม่"):
            parts = cmd.split(maxsplit=1)
            target_server = parts[1].strip() if len(parts) > 1 else ""
            wait_id = send_discord_rest_message(
                self.bot_token, channel_id,
                "🔄 กำลังสั่งปิดเกมเดิม และเปิด FiveM ใหม่ด้วยโหมด pure_2...",
                reply_to_message_id=msg_id
            )
            future = asyncio.Future()

            def callback(result):
                if self.loop and not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("restart_game", {"server": target_server, "callback": callback})

            try:
                res = await asyncio.wait_for(future, timeout=20.0)
                msg_text = res.get("message", "สั่งรีเกมและเชื่อมต่อใหม่เรียบร้อยแล้ว")
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    content=f"🚀 **{msg_text}**",
                    reply_to_message_id=msg_id
                )
                if wait_id:
                    delete_discord_rest_message(self.bot_token, channel_id, wait_id)
            except asyncio.TimeoutError:
                send_discord_rest_message(
                    self.bot_token, channel_id,
                    "⚠️ การสั่งรีเกมหมดเวลา",
                    reply_to_message_id=msg_id
                )
            return
