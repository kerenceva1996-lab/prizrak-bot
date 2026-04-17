import os
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# ========== КОНФИГ ==========
TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ========== КАРТЫ ИГРЫ ==========
CARDS = {
    'place': ['Заброшенная школа', 'Старый театр', 'Подземелье', 'Библиотека', 'Кладбище'],
    'method': ['Старое зеркало', 'Свеча желаний', 'Призрачный ключ', 'Маятник', 'Фотография'],
    'motive': ['Месть', 'Неоконченное дело', 'Защита тайны', 'Предупреждение', 'Любовь']
}

# ВАШИ УЛИКИ С КАРТИНКАМИ (укажите пути к файлам)
EVIDENCE = {
    'e1': {'name': '📜 Старое письмо', 'desc': 'Пожелтевшее письмо', 'image': 'images/evidence1.jpg'},
    'e2': {'name': '🔑 Ржавый ключ', 'desc': 'Старый ржавый ключ', 'image': 'images/evidence2.jpg'},
    'e3': {'name': '📸 Фотография', 'desc': 'Размытая фигура', 'image': 'images/evidence3.jpg'},
    'e4': {'name': '💍 Кольцо', 'desc': 'Обручальное кольцо', 'image': 'images/evidence4.jpg'}
}

# ========== РАБОТА С БАЗОЙ ДАННЫХ ==========
def create_game(creator_id: int, game_code: str):
    data = {
        'game_code': game_code,
        'creator_id': creator_id,
        'players': [creator_id],
        'player_names': {},
        'status': 'waiting',
        'current_turn': 0,
        'used_cards': {'place': [], 'method': [], 'motive': []},
        'used_evidence': [],
        'results': {},
        'pinned_msg_id': None,
        'chat_id': None
    }
    supabase.table('games').insert(data).execute()
    return data

def get_game(game_code: str):
    result = supabase.table('games').select('*').eq('game_code', game_code).execute()
    return result.data[0] if result.data else None

def update_game(game_code: str, updates: dict):
    supabase.table('games').update(updates).eq('game_code', game_code).execute()

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard(game_code: str):
    game = get_game(game_code)
    if not game:
        return None
    
    # Три главные кнопки
    keyboard = [
        [
            InlineKeyboardButton(text="🏚 МЕСТО", callback_data=f"cat_{game_code}_place"),
            InlineKeyboardButton(text="🗡 СПОСОБ", callback_data=f"cat_{game_code}_method"),
            InlineKeyboardButton(text="👻 МОТИВ", callback_data=f"cat_{game_code}_motive")
        ]
    ]
    
    # Кнопки улик (только неиспользованные)
    evidence_row = []
    for ev_id, ev_data in EVIDENCE.items():
        if ev_id not in game.get('used_evidence', []):
            evidence_row.append(
                InlineKeyboardButton(text=ev_data['name'], callback_data=f"ev_{game_code}_{ev_id}")
            )
    if evidence_row:
        keyboard.append(evidence_row)
    
    keyboard.append([InlineKeyboardButton(text="✅ ЗАКОНЧИТЬ ХОД", callback_data=f"end_{game_code}")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_card_keyboard(game_code: str, card_type: str):
    game = get_game(game_code)
    if not game:
        return None
    
    available = [c for c in CARDS[card_type] if c not in game.get('used_cards', {}).get(card_type, [])]
    
    keyboard = []
    for i in range(0, len(available), 2):
        row = []
        for card in available[i:i+2]:
            row.append(InlineKeyboardButton(text=card, callback_data=f"select_{game_code}_{card_type}_{card}"))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(text="◀ НАЗАД", callback_data=f"back_{game_code}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ========== ОТПРАВКА ИГРОВОГО ПОЛЯ ==========
async def send_game_board(game_code: str, chat_id: int, player_id: int = None):
    """Отправляет игровое поле с картинкой-фоном"""
    game = get_game(game_code)
    if not game:
        return
    
    # Определяем, чей ход
    current_player = game['players'][game['current_turn']]
    player_name = game.get('player_names', {}).get(str(current_player), f"Игрок {current_player}")
    
    caption = (
        f"👻 **ПИСЬМА ПРИЗРАКА**\n\n"
        f"🎲 Ход: **{player_name}**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🏚 **МЕСТО** | 🗡 **СПОСОБ** | 👻 **МОТИВ**\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"⬇️ **Выберите категорию или улику:**"
    )
    
    # Отправляем картинку-заставку (опционально)
    try:
        with open('images/game_bg.jpg', 'rb') as bg:
            msg = await bot.send_photo(chat_id, bg, caption=caption, parse_mode="Markdown")
    except:
        msg = await bot.send_message(chat_id, caption, parse_mode="Markdown")
    
    # Отправляем кнопки отдельным сообщением
    await bot.send_message(chat_id, "🔮 **Ваш выбор:**", reply_markup=get_main_keyboard(game_code))
    
    # Закрепляем сообщение с кнопками
    if game.get('pinned_msg_id'):
        try:
            await bot.unpin_chat_message(chat_id, game['pinned_msg_id'])
        except:
            pass
    
    pinned = await bot.send_message(chat_id, "📌 **Игровое меню (закреплено)**", reply_markup=get_main_keyboard(game_code))
    await bot.pin_chat_message(chat_id, pinned.message_id)
    
    update_game(game_code, {'pinned_msg_id': pinned.message_id, 'chat_id': chat_id})

# ========== ОБРАБОТЧИКИ КОМАНД ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👻 **Добро пожаловать в игру 'Письма призрака'!**\n\n"
        "🔮 Мистическая детективная игра\n\n"
        "**Команды:**\n"
        "/new_game — создать новую игру\n"
        "/join КОД — присоединиться к игре\n"
        "/start_game — начать игру (только создатель)"
    )

@dp.message(Command("new_game"))
async def cmd_new_game(message: types.Message):
    game_code = str(message.from_user.id)[:6]
    create_game(message.from_user.id, game_code)
    
    await message.answer(
        f"🎮 **Игра создана!**\n\n"
        f"📌 Код игры: `{game_code}`\n"
        f"👥 Отправьте код друзьям: `/join {game_code}`\n\n"
        f"Когда соберётесь (2-6 игроков), введите:\n"
        f"`/start_game`",
        parse_mode="Markdown"
    )

@dp.message(Command("join"))
async def cmd_join(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Укажите код: `/join КОД`", parse_mode="Markdown")
        return
    
    game_code = args[1]
    game = get_game(game_code)
    
    if not game:
        await message.answer("❌ Игра не найдена!")
        return
    
    if game['status'] != 'waiting':
        await message.answer("❌ Игра уже началась!")
        return
    
    if message.from_user.id in game['players']:
        await message.answer("❌ Вы уже в игре!")
        return
    
    if len(game['players']) >= 6:
        await message.answer("❌ Игра заполнена (максимум 6 игроков)!")
        return
    
    # Добавляем игрока
    players = game['players']
    players.append(message.from_user.id)
    update_game(game_code, {'players': players})
    
    await message.answer(f"✅ {message.from_user.first_name} присоединился к игре!")
    
    # Уведомляем создателя
    await bot.send_message(
        game['creator_id'],
        f"👤 {message.from_user.first_name} присоединился!\n👥 Всего игроков: {len(players)}"
    )

@dp.message(Command("start_game"))
async def cmd_start_game(message: types.Message):
    # Ищем игру, где пользователь — создатель
    game_code = None
    game_data = None
    
    # В реальном проекте лучше сделать запрос в БД
    # Сейчас упрощённо: проверяем все активные игры (для демо)
    
    await message.answer("✅ Игра началась! Отправляю игровое поле...")
    # Здесь нужна логика поиска игры по creator_id
    # Для простоты пока так:
    await message.answer("🔧 Функция дорабатывается. Напишите /setup_game {код} для ручной настройки")

# ========== CALLBACK ОБРАБОТЧИКИ ==========
@dp.callback_query(F.data.startswith("cat_"))
async def handle_category(callback: types.CallbackQuery):
    _, game_code, card_type = callback.data.split("_")
    await callback.message.edit_reply_markup(reply_markup=get_card_keyboard(game_code, card_type))
    await callback.answer()

@dp.callback_query(F.data.startswith("select_"))
async def handle_card_select(callback: types.CallbackQuery):
    _, game_code, card_type, card_value = callback.data.split("_", 3)
    
    game = get_game(game_code)
    if not game:
        await callback.answer("Ошибка игры!", show_alert=True)
        return
    
    # Сохраняем выбор
    player_id = callback.from_user.id
    if str(player_id) not in game.get('results', {}):
        results = game.get('results', {})
        results[str(player_id)] = {}
        update_game(game_code, {'results': results})
        game = get_game(game_code)
    
    results = game['results']
    results[str(player_id)][card_type] = card_value
    update_game(game_code, {'results': results})
    
    # Обновляем использованные карты
    used = game.get('used_cards', {})
    used[card_type].append(card_value)
    update_game(game_code, {'used_cards': used})
    
    await callback.answer(f"✅ Выбрано: {card_value}!", show_alert=True)
    
    # Возвращаем главное меню
    await callback.message.edit_reply_markup(reply_markup=get_main_keyboard(game_code))

@dp.callback_query(F.data.startswith("ev_"))
async def handle_evidence(callback: types.CallbackQuery):
    _, game_code, ev_id = callback.data.split("_")
    
    game = get_game(game_code)
    if not game:
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    # Отправляем КАРТИНКУ улики
    evidence = EVIDENCE.get(ev_id)
    if evidence and evidence.get('image'):
        try:
            photo = FSInputFile(evidence['image'])
            await bot.send_photo(
                callback.from_user.id,
                photo,
                caption=f"🔍 **{evidence['name']}**\n\n{evidence['desc']}",
                parse_mode="Markdown"
            )
        except Exception as e:
            await callback.answer(f"Ошибка загрузки картинки: {e}", show_alert=True)
    else:
        await callback.answer(f"🔍 {evidence['name']}: {evidence['desc']}", show_alert=True)
    
    # Отмечаем улику как использованную
    used = game.get('used_evidence', [])
    if ev_id not in used:
        used.append(ev_id)
        update_game(game_code, {'used_evidence': used})
    
    await callback.answer("Улика получена!")

@dp.callback_query(F.data.startswith("end_"))
async def end_turn(callback: types.CallbackQuery):
    _, game_code = callback.data.split("_")
    
    game = get_game(game_code)
    if not game:
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    # Переход хода
    current_turn = game['current_turn']
    next_turn = (current_turn + 1) % len(game['players'])
    update_game(game_code, {'current_turn': next_turn})
    
    await callback.answer("✅ Ход завершён!")
    
    # Обновляем игровое поле
    await send_game_board(game_code, callback.message.chat.id)

@dp.callback_query(F.data.startswith("back_"))
async def back_to_main(callback: types.CallbackQuery):
    _, game_code = callback.data.split("_")
    await callback.message.edit_reply_markup(reply_markup=get_main_keyboard(game_code))
    await callback.answer()

# ========== ЗАПУСК ==========
async def main():
    print("👻 Бот 'Письма призрака' запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
