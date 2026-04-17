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

# ================== ХРАНИЛИЩЕ ==================
game_board = {
    'МОТИВ': [],
    'МЕСТО': [],
    'СПОСОБ': []
}
pinned_message_id = None
group_chat_id = None
used_cards = []
user_data = {}
current_turn = None
players_list = []

# ================== ДОБАВЛЕНИЕ ИГРОКА ==================
def add_player(user_id, name):
    try:
        existing = supabase.table("players").select("*").eq("user_id", user_id).execute()
        if not existing.data:
            supabase.table("players").insert({"user_id": user_id, "name": name}).execute()
    except:
        pass

# ================== ОБНОВЛЕНИЕ СТОЛА ==================
async def update_table():
    if not group_chat_id or not pinned_message_id:
        return
    
    text = "🕯️ **СТОЛ УЛИК** 🕯️\n\n"
    
    # Мотив
    text += "🗡️ **МОТИВ**\n"
    buttons_motiv = []
    for i in range(4):
        if i < len(game_board['МОТИВ']):
            card = game_board['МОТИВ'][i]
            buttons_motiv.append(InlineKeyboardButton(text=f"🔍 {i+1}", callback_data=f"view_motiv_{i}"))
        else:
            buttons_motiv.append(InlineKeyboardButton(text=f"⬜ {i+1}", callback_data=f"empty"))
    text += " ".join(["   "] * 4) + "\n\n"
    
    # Место
    text += "📍 **МЕСТО**\n"
    buttons_mesto = []
    for i in range(4):
        if i < len(game_board['МЕСТО']):
            buttons_mesto.append(InlineKeyboardButton(text=f"🔍 {i+1}", callback_data=f"view_mesto_{i}"))
        else:
            buttons_mesto.append(InlineKeyboardButton(text=f"⬜ {i+1}", callback_data=f"empty"))
    text += " ".join(["   "] * 4) + "\n\n"
    
    # Способ
    text += "⚰️ **СПОСОБ**\n"
    buttons_sposob = []
    for i in range(4):
        if i < len(game_board['СПОСОБ']):
            buttons_sposob.append(InlineKeyboardButton(text=f"🔍 {i+1}", callback_data=f"view_sposob_{i}"))
        else:
            buttons_sposob.append(InlineKeyboardButton(text=f"⬜ {i+1}", callback_data=f"empty"))
    text += " ".join(["   "] * 4) + "\n\n"
    
    if current_turn:
        text += f"👻 Ход: {current_turn}"
    else:
        text += "👻 Нажми «Взять улику»"
    
    # Создаём клавиатуру из кнопок
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            buttons_motiv,
            buttons_mesto,
            buttons_sposob
        ]
    )
    
    try:
        await bot.edit_message_text(text, chat_id=group_chat_id, message_id=pinned_message_id, reply_markup=keyboard)
    except:
        msg = await bot.send_message(group_chat_id, text, reply_markup=keyboard)
        pinned_message_id = msg.message_id
        await bot.pin_chat_message(group_chat_id, pinned_message_id)

# ================== НОВАЯ ИГРА ==================
@dp.message(Command("new_game"))
async def new_game(message: types.Message):
    global group_chat_id, pinned_message_id, game_board, used_cards, user_data, current_turn, players_list
    group_chat_id = message.chat.id
    game_board = {'МОТИВ': [], 'МЕСТО': [], 'СПОСОБ': []}
    used_cards = []
    user_data = {}
    players_list = []
    current_turn = None
    
    await update_table()
    await message.answer("🎴 Игра создана! Нажмите «Взять улику», чтобы начать.")

# ================== СТАРТ (личка) ==================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    add_player(user_id, name)
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎴 Взять улику", callback_data="take_card")]
        ]
    )
    await message.answer(
        f"🕯️ **ПИСЬМА ПРИЗРАКА**\n\nПривет, {name}! Нажми кнопку, чтобы взять улику.",
        reply_markup=keyboard
    )

# ================== ВЗЯТЬ УЛИКУ ==================
@dp.callback_query(F.data == "take_card")
async def take_card(callback: types.CallbackQuery):
    global current_turn
    user_id = callback.from_user.id
    name = callback.from_user.first_name
    add_player(user_id, name)
    
    if not group_chat_id:
        await callback.message.answer("❌ Сначала создай игру в группе: /new_game")
        return
    
    if current_turn is None:
        current_turn = name
    
    all_cards = supabase.table("cards").select("*").execute()
    available = [c for c in all_cards.data if c['id'] not in used_cards]
    
    if not available:
        await callback.message.answer("❌ Все улики использованы!")
        return
    
    card = random.choice(available)
    used_cards.append(card['id'])
    user_data[user_id] = {'card_id': card['id'], 'card_url': card['image_url']}
    
    await callback.message.answer_photo(
        photo=card['image_url'],
        caption="🃏 **Улика получена!**\n\nВыбери категорию:"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗡️ МОТИВ", callback_data="cat_МОТИВ"),
                InlineKeyboardButton(text="📍 МЕСТО", callback_data="cat_МЕСТО"),
                InlineKeyboardButton(text="⚰️ СПОСОБ", callback_data="cat_СПОСОБ")
            ]
        ]
    )
    await callback.message.answer("Куда положим улику?", reply_markup=keyboard)
    await callback.answer()

# ================== ВЫБОР КАТЕГОРИИ ==================
@dp.callback_query(F.data.startswith("cat_"))
async def select_category(callback: types.CallbackQuery):
    category = callback.data.split("_")[1]
    user_id = callback.from_user.id
    name = callback.from_user.first_name
    
    if user_id not in user_data:
        await callback.message.answer("❌ Сначала возьми улику.")
        return
    
    if len(game_board[category]) >= 4:
        await callback.message.answer(f"❌ В категории {category} уже 4 улики!")
        return
    
    user_data[user_id]['category'] = category
    user_data[user_id]['player_name'] = name
    await callback.message.answer(f"✅ Категория: {category}\n\n✍️ Напиши историю:")
    await callback.answer()

# ================== ПОЛУЧЕНИЕ ИСТОРИИ ==================
@dp.message()
async def get_story(message: types.Message):
    global current_turn
    user_id = message.from_user.id
    
    if user_id not in user_data or 'category' not in user_data[user_id]:
        return
    
    story = message.text
    card_id = user_data[user_id]['card_id']
    category = user_data[user_id]['category']
    card_url = user_data[user_id]['card_url']
    player_name = user_data[user_id]['player_name']
    
    # Сохраняем в БД
    supabase.table("moves").insert({
        "player_id": user_id,
        "card_id": card_id,
        "category": category,
        "story": story
    }).execute()
    
    # Добавляем в игровой стол
    game_board[category].append({
        'url': card_url,
        'story': story,
        'player': player_name,
        'card_id': card_id
    })
    
    # Обновляем стол
    await update_table()
    
    await message.answer(
        f"📜 **История сохранена!**\n\n"
        f"👻 Следующий игрок, нажми «Взять улику»."
    )
    
    # Смена хода
    current_turn = None
    del user_data[user_id]
    
    # Проверяем, заполнен ли стол
    total_cards = len(game_board['МОТИВ']) + len(game_board['МЕСТО']) + len(game_board['СПОСОБ'])
    if total_cards >= 12:
        await message.answer(
            "🎉 **СТОЛ ЗАПОЛНЕН!** 🎉\n\n"
            "Все 12 улик на месте. Напишите /final_table, чтобы увидеть финальный стол."
        )

# ================== ПРОСМОТР УЛИКИ ==================
@dp.callback_query(F.data.startswith("view_"))
async def view_card(callback: types.CallbackQuery):
    data = callback.data.split("_")
    category = data[1]  # motiv, mesto, sposob
    index = int(data[2])
    
    if category == 'motiv':
        cat_name = 'МОТИВ'
    elif category == 'mesto':
        cat_name = 'МЕСТО'
    else:
        cat_name = 'СПОСОБ'
    
    if index >= len(game_board[cat_name]):
        await callback.answer("❌ Здесь пока нет улики")
        return
    
    card = game_board[cat_name][index]
    
    await callback.message.answer_photo(
        photo=card['url'],
        caption=f"🃏 **Улика #{card['card_id']}**\n\n"
                f"📂 Категория: {cat_name}\n"
                f"📝 История: {card['story']}\n"
                f"👤 Игрок: {card['player']}"
    )
    await callback.answer()

# ================== ФИНАЛЬНЫЙ СТОЛ ==================
@dp.message(Command("final_table"))
async def final_table(message: types.Message):
    total_cards = len(game_board['МОТИВ']) + len(game_board['МЕСТО']) + len(game_board['СПОСОБ'])
    if total_cards < 12:
        await message.answer(f"❌ Стол ещё не заполнен! Собрано {total_cards}/12 улик.")
        return
    
    text = "🏆 **ФИНАЛЬНЫЙ СТОЛ** 🏆\n\n"
    
    for category in ['МОТИВ', 'МЕСТО', 'СПОСОБ']:
        text += f"**{category}**\n"
        for i, card in enumerate(game_board[category]):
            text += f"{i+1}. {card['story']} — {card['player']}\n"
        text += "\n"
    
    await message.answer(text)
    
    # Отправляем все картинки
    for category in ['МОТИВ', 'МЕСТО', 'СПОСОБ']:
        for card in game_board[category]:
            await message.answer_photo(
                photo=card['url'],
                caption=f"📂 {category}\n📝 {card['story']}\n👤 {card['player']}"
            )

# ================== ЗАПУСК ==================
async def main():
    print("✅ Бот Письма Призрака запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
