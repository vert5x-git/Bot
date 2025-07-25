from .. import loader, utils
import asyncio
from telethon.tl.types import Message

@loader.tds
class GMinesBonusFarmer(loader.Module):
    """Авто-получение бонуса в @gminesbot каждый час"""
    strings = {"name": "GMinesBonusFarmer"}

    def __init__(self):
        self._running = False
        self._task = None

    async def gfarmer_cmd(self, message: Message):
        """Включает или выключает фармер"""
        self._running = not self._running
        if self._running:
            self._task = asyncio.create_task(self._farmer_loop())
            await utils.answer(message, "✅ Фармер запущен: будет получать бонус каждый час.")
        else:
            if self._task:
                self._task.cancel()
            await utils.answer(message, "⛔ Фармер остановлен.")

    async def _farmer_loop(self):
        while self._running:
            try:
                await self._client.send_message("@gminesbot", "/bonus")
                await asyncio.sleep(3600)  # ждать 1 час
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[GMinesBonusFarmer] Ошибка: {e}")
                await asyncio.sleep(60)

    async def watcher(self, message: Message):
        if not self._running:
            return
        if message.chat and message.chat.username == "gminesbot":
            if "🎁 Получить бонус" in message.raw_text:
                try:
                    await message.click(text="🎁 Получить бонус")
                except Exception as e:
                    print(f"[GMinesBonusFarmer] Ошибка клика: {e}")