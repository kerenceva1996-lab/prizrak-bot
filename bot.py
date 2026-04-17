import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from supabase import create_client, Client

# ================== ТВОИ НАСТРОЙКИ ==================
TOKEN = "8692048583:AAHflIk4eDZZNYFSnjV3-r-lAPCyUnAncHM"
SUPABASE_URL = "https://upnrccovjyxbmhnupndx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVwbnJjY292anl4Ym1obnVwbmR4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQwMTA1MTEsImV4cCI6MjA4OTU4NjUxMX0.idfe6tXuc6jD1CuNQzQNHyrIk1v_HfiU_ajkw0XA9Ik"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================== ХРАНИЛИЩЕ ИГР ==================
games = {}  # game_code -> данные игры

# ================== СОЗДАНИЕ ИГРЫ ==================
@dp.message(Command("new_game"))
async def new_game(message: types.Message):
    game_code = str(message.from_user.id)[:6]
    games[game_code] = {
        'creator_id': message.from_user.id,
        'players': [message.from_user.id],
        'player_names': {message.from_user.id: message.from_user.first_name},
        'status': 'waiting',
        'current_turn': 0,
        'used_cards': [],
        'board': {'МОТИВ': [], 'МЕСТО': [], 'СПОСОБ': []},
        'chat_id': message.chat.id,
        'pinned_msg_id': None
    }
    
    await message.answer(
        f"🎮 **Игра создана!**\n\n"
        f"📌 Код игры: `{game_code}`\n"
        f"👥 Отправьте код друзьям: `/join {game_code}`\n\n"
        f"Когда соберётесь, нажмите `/start_game`",
        parse_mode="Markdown"
    )

# ================== ПРИСОЕДИНЕНИЕ ==================
@dp.message(Command("join"))
async def join_game(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Укажите код: `/join КОД`", parse_mode="Markdown")
        return
    
    game_code = args[1]
    game = games.get(game_code)
    
    if not game:
        await message.answer("❌ Игра не найдена!")
        return
    
    if message.from_user.id in game['players']:
        await message.answer("❌ Вы уже в игре!")
        return
    
    game['players'].append(message.from_user.id)
    game['player_names'][message.from_user.id] = message.from_user.first_name
    
    await message.answer(f"✅ {message.from_user.first_name} присоединился к игре!")

# ================== СТАРТ ИГРЫ ==================
@dp.message(Command("start_game"))
async def start_game(message: types.Message):
    # Находим игру, где пользователь — создатель
    game_code = None
    game = None
    for code, g in games.items():
        if g['creator_id'] == message.from_user.id:
            game_code = code
            game = g
            break
    
    if not game:
        await message.answer("❌ Вы не создали игру! Сначала напишите /new_game")
        return
    
    if len(game['players']) < 2:
        await message.answer("❌ Нужно минимум 2 игрока! Пригласите друзей через /join")
        return
    
    game['status'] = 'playing'
    game['current_turn'] = 0
    
    await message.answer(f"✅ Игра началась! Всего игроков: {len(game['players'])}")
    
    # Отправляем игровой стол
    await send_game_board(game_code, message.chat.id)

# ================== ОТПРАВКА СТОЛА ==================
async def send_game_board(game_code: str, chat_id: int):
    game = games.get(game_code)
    if not game:
        return
    
    current_player_id = game['players'][game['current_turn']]
    current_player_name = game['player_names'].get(current_player_id, "Игрок")
    
    text = f"🕯️ **СТОЛ УЛИК** 🕯️\n\n"
    text += f"👻 Ход: **{current_player_name}**\n\n"
    
    for category in ['МОТИВ', 'МЕСТО', 'СПОСОБ']:
        text += f"**{category}**\n"
        cards = game['board'][category]
        if cards:
            for i, card in enumerate(cards):
                text += f"{i+1}. {card['story']} — {card['player']}\n"
        else:
            text += "(пусто)\n"
        text += "\n"
    
    text += "🔍 Нажмите **«Взять улику»** в личном сообщении с ботом!"
    
    # Отправляем или обновляем закреплённое сообщение
    if game.get('pinned_msg_id'):
        try:
            await bot.edit_message_text(text, chat_id=chat_id, message_id=game['pinned_msg_id'])
        except:
            msg = await bot.send_message(chat_id, text)
            game['pinned_msg_id'] = msg.message_id
            await bot.pin_chat_message(chat_id, game['pinned_msg_id'])
    else:
        msg = await bot.send_message(chat_id, text)
        game['pinned_msg_id'] = msg.message_id
        await bot.pin_chat_message(chat_id, game['pinned_msg_id'])

# ================== СТАРТ В ЛИЧКЕ ==================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Проверяем, есть ли активная игра у пользователя
    active_game = None
    for code, game in games.items():
        if message.from_user.id in game['players'] and game['status'] == 'playing':
            active_game = code
            break
    
    if not active_game:
        await message.answer(
            "👻 **ПИСЬМА ПРИЗРАКА**\n\n"
            "Создайте или присоединитесь к игре в группе:\n"
            "/new_game — создать игру\n"
            "/join КОД — присоединиться"
        )
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎴 ВЗЯТЬ УЛИКУ", callback_data=f"take_{active_game}")]
        ]
    )
    await message.answer("🃏 Нажми кнопку, чтобы взять улику:", reply_markup=keyboard)

# ================== ВЗЯТЬ УЛИКУ ==================
@dp.callback_query(F.data.startswith("take_"))
async def take_card(callback: types.CallbackQuery):
    game_code = callback.data.split("_")[1]
    game = games.get(game_code)
    
    if not game or game['status'] != 'playing':
        await callback.answer("❌ Игра не активна", show_alert=True)
        return
    
    # Проверяем, чей ход
    current_player_id = game['players'][game['current_turn']]
    if callback.from_user.id != current_player_id:
        await callback.answer("❌ Сейчас не ваш ход!", show_alert=True)
        return
    
    # Получаем случайную карту из Supabase
    all_cards = supabase.table("cards").select("*").execute()
    available = [c for c in all_cards.data if c['id'] not in game['used_cards']]
    
    if not available:
        await callback.message.answer("❌ Все улики использованы!")
        return
    
    card = random.choice(available)
    game['used_cards'].append(card['id'])
    
    # Временное хранилище для выбора игрока
    game['temp_card'] = {
        'card_id': card['id'],
        'card_url': card['image_url'],
        'player_id': callback.from_user.id
    }
    
    await callback.message.answer_photo(
        photo=card['image_url'],
        caption="🃏 **Улика получена!**\n\nВыбери категорию:"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗡️ МОТИВ", callback_data=f"cat_{game_code}_МОТИВ"),
                InlineKeyboardButton(text="📍 МЕСТО", callback_data=f"cat_{game_code}_МЕСТО"),
                InlineKeyboardButton(text="⚰️ СПОСОБ", callback_data=f"cat_{game_code}_СПОСОБ")
            ]
        ]
    )
    await callback.message.answer("Куда положим улику?", reply_markup=keyboard)
    await callback.answer()

# ================== ВЫБОР КАТЕГОРИИ ==================
@dp.callback_query(F.data.startswith("cat_"))
async def select_category(callback: types.CallbackQuery):
    _, game_code, category = callback.data.split("_")
    game = games.get(game_code)
    
    if not game or 'temp_card' not in game:
        await callback.message.answer("❌ Сначала возьми улику!")
        return
    
    game['temp_card']['category'] = category
    await callback.message.answer(f"✅ Категория: {category}\n\n✍️ Напиши историю для этой улики:")
    await callback.answer()

# ================== ПОЛУЧЕНИЕ ИСТОРИИ ==================
@dp.message()
async def get_story(message: types.Message):
    # Находим игру, где у игрока есть temp_card
    game_code = None
    game = None
    for code, g in games.items():
        if g.get('temp_card') and g['temp_card'].get('player_id') == message.from_user.id:
            game_code = code
            game = g
            break
    
    if not game or 'category' not in game['temp_card']:
        return
    
    story = message.text
    card_id = game['temp_card']['card_id']
    category = game['temp_card']['category']
    card_url = game['temp_card']['card_url']
    player_name = message.from_user.first_name
    
    # Сохраняем в базу данных
    supabase.table("moves").insert({
        "player_id": message.from_user.id,
        "card_id": card_id,
        "category": category,
        "story": story
    }).execute()
    
    # Добавляем в игровую доску
    game['board'][category].append({
        'card_id': card_id,
        'url': card_url,
        'story': story,
        'player': player_name
    })
    
    # Переход хода
    game['current_turn'] = (game['current_turn'] + 1) % len(game['players'])
    
    # Очищаем временные данные
    del game['temp_card']
    
    # Обновляем закреплённое сообщение
    await send_game_board(game_code, game['chat_id'])
    
    await message.answer(
        f"📜 **История сохранена!**\n\n"
        f"👻 Следующий игрок, нажми «Взять улику» в личном сообщении с ботом."
    )

# ================== ЗАПУСК ==================
async def main():
    print("✅ Бот Письма Призрака запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
