import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from supabase import create_client, Client

TOKEN = "8692048583:AAHflIk4eDZZNYFSnjV3-r-lAPCyUnAncHM"
SUPABASE_URL = "https://upnrccovjyxbmhnupndx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVwbnJjY292anl4Ym1obnVwbmR4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQwMTA1MTEsImV4cCI6MjA4OTU4NjUxMX0.idfe6tXuc6jD1CuNQzQNHyrIk1v_HfiU_ajkw0XA9Ik"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

games = {}

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
    await message.answer(f"🎮 Игра создана!\n📌 Код: `{game_code}`\n👥 `/join {game_code}`\n▶️ `/start_game`", parse_mode="Markdown")

@dp.message(Command("join"))
async def join_game(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ `/join КОД`")
        return
    game_code = args[1]
    game = games.get(game_code)
    if not game or game['status'] != 'waiting':
        await message.answer("❌ Игра не найдена или уже началась")
        return
    if message.from_user.id in game['players']:
        await message.answer("❌ Вы уже в игре")
        return
    if len(game['players']) >= 6:
        await message.answer("❌ Игра заполнена")
        return
    game['players'].append(message.from_user.id)
    game['player_names'][message.from_user.id] = message.from_user.first_name
    await message.answer(f"✅ {message.from_user.first_name} присоединился!")

@dp.message(Command("start_game"))
async def start_game(message: types.Message):
    game_code = None
    game = None
    for code, g in games.items():
        if g['creator_id'] == message.from_user.id:
            game_code = code
            game = g
            break
    if not game:
        await message.answer("❌ Вы не создали игру")
        return
    if len(game['players']) < 2:
        await message.answer("❌ Нужно минимум 2 игрока")
        return
    game['status'] = 'playing'
    await message.answer(f"✅ Игра началась! Игроков: {len(game['players'])}")
    await send_game_board(game_code, message.chat.id)

async def send_game_board(game_code: str, chat_id: int):
    game = games.get(game_code)
    if not game:
        return
    current_player = game['player_names'][game['players'][game['current_turn']]]
    text = f"🕯️ СТОЛ УЛИК\n\n👻 Ход: {current_player}\n\n"
    for cat in ['МОТИВ', 'МЕСТО', 'СПОСОБ']:
        text += f"**{cat}**\n"
        cards = game['board'][cat]
        if cards:
            for i, c in enumerate(cards):
                text += f"{i+1}. {c['story']} — {c['player']}\n"
        else:
            text += "(пусто)\n"
        text += "\n"
    text += "🎴 Взять улику — в личке с ботом /start"
    keyboard = []
    for cat in ['МОТИВ', 'МЕСТО', 'СПОСОБ']:
        for i in range(len(game['board'][cat])):
            keyboard.append([InlineKeyboardButton(text=f"🔍 {cat} {i+1}", callback_data=f"view_{game_code}_{cat}_{i}")])
    if game.get('pinned_msg_id'):
        try:
            await bot.edit_message_text(text, chat_id=chat_id, message_id=game['pinned_msg_id'])
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=game['pinned_msg_id'], reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        except:
            msg = await bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
            game['pinned_msg_id'] = msg.message_id
            await bot.pin_chat_message(chat_id, game['pinned_msg_id'])
    else:
        msg = await bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        game['pinned_msg_id'] = msg.message_id
        await bot.pin_chat_message(chat_id, game['pinned_msg_id'])

@dp.callback_query(F.data.startswith("view_"))
async def view_card(callback: types.CallbackQuery):
    _, game_code, category, idx = callback.data.split("_")
    idx = int(idx)
    game = games.get(game_code)
    if not game or idx >= len(game['board'][category]):
        await callback.answer("❌ Улика не найдена")
        return
    card = game['board'][category][idx]
    await callback.message.answer_photo(photo=card['url'], caption=f"🃏 {category}\n📝 {card['story']}\n👤 {card['player']}")
    await callback.answer()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    active = None
    for code, g in games.items():
        if message.from_user.id in g['players'] and g['status'] == 'playing':
            active = code
            break
    if not active:
        await message.answer("👻 Нет активной игры. Создайте или присоединитесь в группе.")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎴 ВЗЯТЬ УЛИКУ", callback_data=f"take_{active}")]])
    await message.answer("🃏 Нажми кнопку:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("take_"))
async def take_card(callback: types.CallbackQuery):
    game_code = callback.data.split("_")[1]
    game = games.get(game_code)
    if not game or game['status'] != 'playing':
        await callback.answer("❌ Игра не активна")
        return
    current = game['players'][game['current_turn']]
    if callback.from_user.id != current:
        await callback.answer("❌ Сейчас не ваш ход")
        return
    all_cards = supabase.table("cards").select("*").execute()
    available = [c for c in all_cards.data if c['id'] not in game['used_cards']]
    if not available:
        await callback.message.answer("❌ Все улики использованы")
        return
    card = random.choice(available)
    game['used_cards'].append(card['id'])
    game['temp_card'] = {'card_id': card['id'], 'card_url': card['image_url'], 'player_id': callback.from_user.id}
    await callback.message.answer_photo(photo=card['image_url'], caption="🃏 Улика получена! Выбери категорию:")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🗡️ МОТИВ", callback_data=f"cat_{game_code}_МОТИВ"),
        InlineKeyboardButton(text="📍 МЕСТО", callback_data=f"cat_{game_code}_МЕСТО"),
        InlineKeyboardButton(text="⚰️ СПОСОБ", callback_data=f"cat_{game_code}_СПОСОБ")
    ]])
    await callback.message.answer("Куда положим?", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("cat_"))
async def select_category(callback: types.CallbackQuery):
    _, game_code, category = callback.data.split("_")
    game = games.get(game_code)
    if not game or 'temp_card' not in game:
        await callback.message.answer("❌ Сначала возьми улику")
        return
    if len(game['board'][category]) >= 4:
        await callback.message.answer(f"❌ В {category} уже 4 улики!")
        return
    game['temp_card']['category'] = category
    await callback.message.answer(f"✅ Категория: {category}\n\n✍️ Напиши историю:")
    await callback.answer()

@dp.message()
async def get_story(message: types.Message):
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
    supabase.table("moves").insert({"player_id": message.from_user.id, "card_id": card_id, "category": category, "story": story}).execute()
    game['board'][category].append({'card_id': card_id, 'url': card_url, 'story': story, 'player': player_name})
    game['current_turn'] = (game['current_turn'] + 1) % len(game['players'])
    del game['temp_card']
    await send_game_board(game_code, game['chat_id'])
    total = len(game['board']['МОТИВ']) + len(game['board']['МЕСТО']) + len(game['board']['СПОСОБ'])
    if total >= 12:
        await message.answer("🎉 СТОЛ ЗАПОЛНЕН! Напишите /final_table в группе.")
    else:
        await message.answer("📜 История сохранена! Следующий игрок, нажми «Взять улику».")

@dp.message(Command("final_table"))
async def final_table(message: types.Message):
    game_code = None
    game = None
    for code, g in games.items():
        if g['chat_id'] == message.chat.id:
            game_code = code
            game = g
            break
    if not game:
        await message.answer("❌ Нет активной игры")
        return
    total = len(game['board']['МОТИВ']) + len(game['board']['МЕСТО']) + len(game['board']['СПОСОБ'])
    if total < 12:
        await message.answer(f"❌ Собрано {total}/12 улик")
        return
    text = "🏆 ФИНАЛЬНЫЙ СТОЛ\n\n"
    for cat in ['МОТИВ', 'МЕСТО', 'СПОСОБ']:
        text += f"{cat}\n"
        for i, c in enumerate(game['board'][cat]):
            text += f"{i+1}. {c['story']} — {c['player']}\n"
        text += "\n"
    await message.answer(text)
    for cat in ['МОТИВ', 'МЕСТО', 'СПОСОБ']:
        for c in game['board'][cat]:
            await message.answer_photo(photo=c['url'], caption=f"{cat}\n{c['story']}\n{c['player']}")
    del games[game_code]
    await message.answer("🎮 Игра завершена! /new_game")

async def main():
    print("✅ Бот запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
