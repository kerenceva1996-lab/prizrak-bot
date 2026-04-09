import asyncio
import random
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from supabase import create_client, Client

TOKEN = "8692048583:AAHflIk4eDZZNYFSnjV3-r-lAPCyUnAncHM"
SUPABASE_URL = "https://upnrccovjyxbmhnupndx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVwbnJjY292anl4Ym1obnVwbmR4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQwMTA1MTEsImV4cCI6MjA4OTU4NjUxMX0.idfe6tXuc6jD1CuNQzQNHyrIk1v_HfiU_ajkw0XA9Ik"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

used_cards = []

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💼 Сесть за стол", callback_data="to_table")]
        ]
    )
    await message.answer("🕯️ Нажми кнопку, чтобы сесть за стол.", reply_markup=keyboard)

@dp.callback_query(F.data == "to_table")
async def to_table(callback: types.CallbackQuery):
    url = "https://kerenceva1996-lab.github.io/ghost-table/"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Открыть стол", web_app=WebAppInfo(url=url))]
        ]
    )
    await bot.send_message(
        chat_id=callback.from_user.id,
        text="🕯️ Нажми кнопку, чтобы открыть стол:",
        reply_markup=keyboard
    )
    await callback.answer("✅ Стол открыт!")

@dp.message(F.content_type == 'web_app_data')
async def handle_web_app_data(message: types.Message):
    global used_cards
    data = json.loads(message.web_app_data.data)
    if data.get('action') == 'get_card':
        all_cards = supabase.table("cards").select("*").execute()
        available = [c for c in all_cards.data if c['id'] not in used_cards]
        if not available:
            await message.answer(json.dumps({"action": "error", "message": "Нет карт"}))
            return
        card = random.choice(available)
        used_cards.append(card['id'])
        await message.answer(json.dumps({"action": "card_received", "card_id": card['id'], "url": card['image_url']}))

async def main():
    print("✅ Бот запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
