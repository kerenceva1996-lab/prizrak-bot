import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from supabase import create_client, Client

# ================== НАСТРОЙКИ ==================
TOKEN = "8692048583:AAHflIk4eDZZNYFSnjV3-r-lAPCyUnAncHM"
SUPABASE_URL = "https://upnrccovjyxbmhnupndx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVwbnJjY292anl4Ym1obnVwbmR4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQwMTA1MTEsImV4cCI6MjA4OTU4NjUxMX0.idfe6tXuc6jD1CuNQzQNHyrIk1v_HfiU_ajkw0XA9Ik"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

used_cards = []
user_data = {}

# ================== КОМАНДА /start ==================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎴 Взять улику", callback_data="take_card")]
        ]
    )
    await message.answer(
        "🕯️ **ПИСЬМА ПРИЗРАКА**\n\n"
        "Нажми кнопку, чтобы взять улику и начать игру.",
        reply_markup=keyboard
    )

# ================== ВЗЯТЬ УЛИКУ ==================
@dp.callback_query(F.data == "take_card")
async def take_card(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Получаем все карты
    all_cards = supabase.table("cards").select("*").execute()
    available = [c for c in all_cards.data if c['id'] not in used_cards]
    
    if not available:
        await callback.message.answer("❌ Все улики уже использованы! Игра окончена.")
        return
    
    # Выбираем случайную карту
    card = random.choice(available)
    used_cards.append(card['id'])
    
    # Сохраняем карту для пользователя
    user_data[user_id] = {'card_id': card['id'], 'card_url': card['image_url']}
    
    # Отправляем картинку в чат
    await callback.message.answer_photo(
        photo=card['image_url'],
        caption=f"🃏 **Улика получена!**\n\nВыбери категорию:"
    )
    
    # Кнопки выбора категории
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗡️ МОТИВ", callback_data="cat_МОТИВ"),
                InlineKeyboardButton(text="📍 МЕСТО", callback_data="cat_МЕСТО"),
                InlineKeyboardButton(text="⚰️ СПОСОБ", callback_data="cat_СПОСОБ")
            ]
        ]
    )
    await callback.message.answer("Куда положим эту улику?", reply_markup=keyboard)
    await callback.answer()

# ================== ВЫБОР КАТЕГОРИИ ==================
@dp.callback_query(F.data.startswith("cat_"))
async def select_category(callback: types.CallbackQuery):
    category = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    if user_id not in user_data:
        await callback.message.answer("❌ Сначала возьми улику (нажми «Взять улику»).")
        return
    
    user_data[user_id]['category'] = category
    
    await callback.message.answer(f"✅ Категория выбрана: **{category}**\n\n✍️ Напиши историю для этой улики (одним сообщением):")
    await callback.answer()

# ================== ПОЛУЧЕНИЕ ИСТОРИИ ==================
@dp.message()
async def get_story(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in user_data or 'category' not in user_data[user_id]:
        return
    
    story = message.text
    card_id = user_data[user_id]['card_id']
    category = user_data[user_id]['category']
    card_url = user_data[user_id]['card_url']
    
    # Сохраняем в Supabase
    supabase.table("moves").insert({
        "player_id": user_id,
        "card_id": card_id,
        "category": category,
        "story": story
    }).execute()
    
    # Публикуем результат в чат
    await message.answer(
        f"📜 **История сохранена!**\n\n"
        f"🃏 Улика: [посмотреть]({card_url})\n"
        f"📂 Категория: {category}\n"
        f"📝 История: {story}\n\n"
        f"👻 Следующий игрок, нажми «Взять улику»."
    )
    
    # Очищаем данные пользователя
    del user_data[user_id]

# ================== ЗАПУСК ==================
async def main():
    print("✅ Бот Письма Призрака запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
