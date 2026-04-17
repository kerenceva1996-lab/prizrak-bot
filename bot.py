import asyncio
import random
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from supabase import create_client, Client

# ================== НАСТРОЙКИ ==================
TOKEN = "8692048583:AAHflIk4eDZZNYFSnjV3-r-lAPCyUnAncHM"
SUPABASE_URL = "https://upnrccovjyxbmhnupndx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVwbnJjY292anl4Ym1obnVwbmR4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQwMTA1MTEsImV4cCI6MjA4OTU4NjUxMX0.idfe6tXuc6jD1CuNQzQNHyrIk1v_HfiU_ajkw0XA9Ik"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

used_cards = []
user_stories = {}

# ================== КОМАНДА /start ==================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💼 Сесть за стол", callback_data="to_table")]
        ]
    )
    await message.answer("🕯️ Нажми кнопку, чтобы начать игру.", reply_markup=keyboard)

# ================== КНОПКА "СЕСТЬ ЗА СТОЛ" ==================
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
        text="🕯️ Нажми кнопку, чтобы взять улику:",
        reply_markup=keyboard
    )
    await callback.answer("✅ Игра началась!")

# ================== ПОЛУЧЕНИЕ ЗАПРОСА С САЙТА ==================
@dp.message(F.content_type == 'web_app_data')
async def handle_web_app_data(message: types.Message):
    global used_cards
    data = json.loads(message.web_app_data.data)
    print(f"📨 Получено: {data}")

    if data.get('action') == 'get_card':
        all_cards = supabase.table("cards").select("*").execute()
        available = [c for c in all_cards.data if c['id'] not in used_cards]
        if not available:
            await message.answer("❌ Все улики уже использованы!")
            return
        
        card = random.choice(available)
        used_cards.append(card['id'])
        
        user_stories[message.from_user.id] = {'card_id': card['id'], 'card_url': card['image_url']}
        
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=card['image_url'],
            caption=f"🃏 Улика #{card['id']}\n\nВыбери категорию:"
        )
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🗡️ МОТИВ", callback_data=f"cat_motiv_{card['id']}"),
                    InlineKeyboardButton(text="📍 МЕСТО", callback_data=f"cat_mesto_{card['id']}"),
                    InlineKeyboardButton(text="⚰️ СПОСОБ", callback_data=f"cat_sposob_{card['id']}")
                ]
            ]
        )
        await bot.send_message(
            chat_id=message.chat.id,
            text="Куда положим эту улику?",
            reply_markup=keyboard
        )

# ================== ВЫБОР КАТЕГОРИИ ==================
@dp.callback_query(F.data.startswith("cat_"))
async def category_selected(callback: types.CallbackQuery):
    data = callback.data.split("_")
    cat_key = data[1]  # motiv, mesto, sposob
    
    category_map = {
        'motiv': 'МОТИВ',
        'mesto': 'МЕСТО',
        'sposob': 'СПОСОБ'
    }
    category = category_map.get(cat_key, cat_key.upper())
    
    user_stories[callback.from_user.id]['category'] = category
    
    await callback.message.answer(f"✅ Категория выбрана: {category}\n\nНапиши историю для этой улики (текст):")
    await callback.answer()

# ================== ПОЛУЧЕНИЕ ИСТОРИИ ==================
@dp.message()
async def get_story(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_stories or 'category' not in user_stories[user_id]:
        return
    
    story = message.text
    card_id = user_stories[user_id]['card_id']
    category = user_stories[user_id]['category']
    card_url = user_stories[user_id]['card_url']
    
    supabase.table("moves").insert({
        "player_id": user_id,
        "card_id": card_id,
        "category": category,
        "story": story
    }).execute()
    
    await message.answer(
        f"📜 **История сохранена!**\n\n"
        f"🃏 Улика: [картинка]({card_url})\n"
        f"📂 Категория: {category}\n"
        f"📝 История: {story}\n\n"
        f"👻 Теперь ход другого игрока. Нажмите «Взять улику»."
    )
    
    del user_stories[user_id]

# ================== ЗАПУСК ==================
async def main():
    print("✅ Бот запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
