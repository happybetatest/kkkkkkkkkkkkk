"""Discord Remote Control module for FiveM Farming Macro.

Allows users to control and monitor their FiveM farming macro from Discord via a Bot.
"""

import asyncio
import os
import threading
import time
import cv2
import numpy as np

try:
    import discord
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False

from PySide6.QtCore import QObject, Signal, Slot


class DiscordRemoteWorker(QObject):
    """Background worker managing the Discord Bot client."""

    status_signal = Signal(bool, str)          # (is_connected, bot_username_or_error)
    log_signal = Signal(str)                   # log message
    action_requested = Signal(str, object)     # (action_name, reply_callback_or_dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bot_token = ""
        self.admin_user_id = ""
        self.is_enabled = False
        self.is_running = False
        self.client = None
        self.loop = None
        self.thread = None

    def configure(self, token, admin_id, enabled):
        self.bot_token = str(token).strip()
        self.admin_user_id = str(admin_id).strip()
        self.is_enabled = bool(enabled)

    def start_bot(self):
        if not DISCORD_AVAILABLE:
            self.status_signal.emit(False, "ไม่พบไลบรารี discord.py")
            self.log_signal.emit("[Discord Remote] ผิดพลาด: ไม่พบ discord.py ในระบบ")
            return

        if not self.bot_token:
            self.status_signal.emit(False, "ยังไม่ได้ใส่ Bot Token")
            return

        if self.is_running:
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()

    def stop_bot(self):
        self.is_running = False
        if self.loop and self.client:
            try:
                asyncio.run_coroutine_threadsafe(self.client.close(), self.loop)
            except Exception:
                pass
        self.status_signal.emit(False, "ออฟไลน์")

    def _run_event_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        intents = discord.Intents.default()
        intents.message_content = True

        self.client = discord.Client(intents=intents, loop=self.loop)

        @self.client.event
        async def on_ready():
            username = f"{self.client.user.name}"
            self.status_signal.emit(True, f"ออนไลน์: {username}")
            self.log_signal.emit(f"[Discord Remote] เชื่อมต่อบอทสำเร็จ: {username}")

        @self.client.event
        async def on_message(message):
            if message.author.bot:
                return

            # Whitelist check: only accept commands from configured Admin User ID
            sender_id = str(message.author.id)
            if self.admin_user_id and sender_id != self.admin_user_id:
                # Silently ignore unauthorized users for maximum privacy & security
                return

            raw_text = message.content.strip()
            if not raw_text:
                return

            # Normalize command (strip prefix '!' or '/' or direct command)
            cmd = raw_text.lower()
            if cmd.startswith("!") or cmd.startswith("/"):
                cmd = cmd[1:].strip()

            await self._handle_command(message, cmd)

        try:
            self.loop.run_until_complete(self.client.start(self.bot_token))
        except Exception as e:
            if self.is_running:
                self.status_signal.emit(False, f"ข้อผิดพลาด: {e}")
                self.log_signal.emit(f"[Discord Remote] การเชื่อมต่อขัดข้อง: {e}")
        finally:
            self.is_running = False

    async def _handle_command(self, message, cmd):
        # 1. HELP COMMAND
        if cmd in ("help", "คำสั่ง", "เมนู", "menu"):
            help_text = (
                "🎮 **FiveM Farming Macro — เมนูคำสั่งควบคุมระยะไกล**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "📦 `!check` หรือ `!bag` : **เปิดกระเป๋า ตรวจเช็คทอง/เพชร และถ่ายรูปส่งกลับมา**\n"
                "🗑️ `!discard` หรือ `!ทิ้งทอง` : **สั่งทิ้งทอง กดยืนยัน และกลับไปเริ่มฟาร์มต่อ**\n"
                "📸 `!screen` : ถ่ายภาพหน้าจอ FiveM สดๆ\n"
                "📊 `!status` : ตรวจสอบสถานะการทำงานปัจจุบัน\n"
                "🟢 `!start` : เริ่มการทำงานของบอท\n"
                "🔴 `!stop` : หยุดพักบอทชั่วคราว\n"
                "🍗 `!feed` : สั่งให้ตัวละครกินน้ำ (ช่อง 6) และอาหาร (ช่อง 7)\n"
                "💎 `!store` : สั่งให้เริ่มกระบวนการเก็บเพชรลงรถ\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "*คำสั่งทั้งหมดทำงานเฉพาะกับเจ้าของบอทเท่านั้น*"
            )
            await message.reply(help_text)
            return

        # 2. CHECK BAG & SEND SCREENSHOT
        if cmd in ("check", "bag", "กระเป๋า", "ทอง", "gold"):
            wait_msg = await message.reply("⏳ กำลังสลับไป FiveM และเปิดกระเป๋าเพื่อถ่ายรูป กรุณารอสักครู่...")
            future = asyncio.Future()

            def callback(result):
                if not self.loop.is_closed():
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

                if img_path and os.path.isfile(img_path):
                    with open(img_path, "rb") as f:
                        picture = discord.File(f, filename="inventory.png")
                        await message.reply(content=caption, file=picture)
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass
                else:
                    await message.reply(content=f"{caption}\n*(ไม่สามารถบันทึกภาพกระเป๋าได้)*")
                await wait_msg.delete()
            except asyncio.TimeoutError:
                await wait_msg.edit(content="⚠️ คำสั่งหมดเวลา: มาโครไม่ตอบสนอง กรุณาตรวจสอบว่าเปิด FiveM อยู่หรือไม่")
            return

        # 3. DISCARD GOLD & RESUME FARMING
        if cmd in ("discard", "dump", "drop", "ทิ้งทอง", "ทิ้ง"):
            wait_msg = await message.reply("🗑️ กำลังเปิดกระเป๋าเพื่อกดทิ้งทอง และเริ่มฟาร์มต่อให้อัตโนมัติ...")
            future = asyncio.Future()

            def callback(result):
                if not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("discard_gold", callback)

            try:
                res = await asyncio.wait_for(future, timeout=25.0)
                success = res.get("success", False)
                msg_text = res.get("message", "ดำเนินการเสร็จสิ้น")
                img_path = res.get("image_path")

                reply_text = f"✅ **{msg_text}**" if success else f"⚠️ **{msg_text}**"
                if img_path and os.path.isfile(img_path):
                    with open(img_path, "rb") as f:
                        picture = discord.File(f, filename="discard_result.png")
                        await message.reply(content=reply_text, file=picture)
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass
                else:
                    await message.reply(content=reply_text)
                await wait_msg.delete()
            except asyncio.TimeoutError:
                await wait_msg.edit(content="⚠️ คำสั่งหมดเวลา: ไม่สามารถทำรายการทิ้งทองได้ทันในเวลาที่กำหนด")
            return

        # 4. CAPTURE SCREEN
        if cmd in ("screen", "screenshot", "จอ", "ภาพ"):
            wait_msg = await message.reply("📸 กำลังถ่ายภาพหน้าจอ FiveM...")
            future = asyncio.Future()

            def callback(result):
                if not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("screenshot", callback)

            try:
                res = await asyncio.wait_for(future, timeout=10.0)
                img_path = res.get("image_path")
                if img_path and os.path.isfile(img_path):
                    with open(img_path, "rb") as f:
                        picture = discord.File(f, filename="fivem_screen.png")
                        await message.reply(content=f"📸 **ภาพหน้าจอ FiveM สดๆ** (<t:{int(time.time())}:T>)", file=picture)
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass
                    await wait_msg.delete()
                else:
                    await wait_msg.edit(content="⚠️ ไม่สามารถจับภาพหน้าจอ FiveM ได้ (หน้าต่างเกมอาจถูกย่อ)")
            except asyncio.TimeoutError:
                await wait_msg.edit(content="⚠️ การถ่ายภาพหน้าจอหมดเวลา")
            return

        # 5. START MACRO
        if cmd in ("start", "เริ่ม", "on"):
            future = asyncio.Future()

            def callback(result):
                if not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("start_macro", callback)
            res = await future
            await message.reply(f"🟢 **{res.get('message', 'เริ่มการทำงานของบอทแล้ว')}**")
            return

        # 6. STOP MACRO
        if cmd in ("stop", "หยุด", "off", "pause"):
            future = asyncio.Future()

            def callback(result):
                if not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("stop_macro", callback)
            res = await future
            await message.reply(f"🔴 **{res.get('message', 'หยุดพักบอทชั่วคราวแล้ว')}**")
            return

        # 7. FEED ACTION
        if cmd in ("feed", "กินข้าว", "กินน้ำ", "อาหาร", "กิน"):
            wait_msg = await message.reply("🍗 กำลังเริ่มกระบวนการกินน้ำ (ช่อง 6) และอาหาร (ช่อง 7)...")
            future = asyncio.Future()

            def callback(result):
                if not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("feed", callback)

            try:
                res = await asyncio.wait_for(future, timeout=30.0)
                await wait_msg.edit(content=f"🍗 **{res.get('message', 'ป้อนอาหารและน้ำเรียบร้อยแล้ว')}**")
            except asyncio.TimeoutError:
                await wait_msg.edit(content="⚠️ กระบวนการกินอาหารหมดเวลา")
            return

        # 8. STORE DIAMONDS
        if cmd in ("store", "เก็บเพชร", "เก็บของ", "รถ"):
            wait_msg = await message.reply("💎 กำลังเริ่มกระบวนการเก็บเพชรลงท้ายรถ...")
            future = asyncio.Future()

            def callback(result):
                if not self.loop.is_closed():
                    self.loop.call_soon_threadsafe(future.set_result, result)

            self.action_requested.emit("store_diamonds", callback)

            try:
                res = await asyncio.wait_for(future, timeout=30.0)
                await wait_msg.edit(content=f"💎 **{res.get('message', 'กระบวนการเก็บเพชรเสร็จสิ้น')}**")
            except asyncio.TimeoutError:
                await wait_msg.edit(content="⚠️ กระบวนการเก็บเพชรหมดเวลา")
            return

        # 9. STATUS
        if cmd in ("status", "สถานะ", "info"):
            future = asyncio.Future()

            def callback(result):
                if not self.loop.is_closed():
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
            await message.reply(status_text)
            return
