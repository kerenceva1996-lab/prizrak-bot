import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

TOKEN = "8692048583:AAHflIk4eDZZNYFSnjV3-r-lAPCyUnAncHM"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

games = {}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👻 **ПИСЬМА ПРИЗРАКА**\n\n"
        "Команды:\n"
        "/new_game — создать игру\n"
        "/join — присоединиться\n"
        "/start_game — начать игру (только создатель)"
    )

@dp.message(Command("new_game"))
async def new_game(message: types.Message):
    game_code = str(message.from_user.id)[:6]
    games[game_code] = {
        'creator': message.from_user.id,
        'players': [message.from_user.id],
        'names': {message.from_user.id: message.from_user.first_name},
        'status': 'waiting',
        'roles': {}
    }
    await message.answer(
        f"🎮 **Игра создана!**\n\n"
        f"📌 Код: `{game_code}`\n"
        f"👥 Пригласи друзей: `/join {game_code}`\n\n"
        f"Когда соберётесь (от 4 игроков), напиши `/start_game`"
    )

@dp.message(Command("join"))
async def join_game(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Напиши: `/join КОД`")
        return

    game_code = args[1]
    game = games.get(game_code)

    if not game:
        await message.answer("❌ Игра не найдена")
        return

    if game['status'] != 'waiting':
        await message.answer("❌ Игра уже началась")
        return

    if message.from_user.id in game['players']:
        await message.answer("❌ Ты уже в игре")
        return

    game['players'].append(message.from_user.id)
    game['names'][message.from_user.id] = message.from_user.first_name

    await message.answer(f"✅ {message.from_user.first_name} присоединился! ({len(game['players'])} игроков)")

@dp.message(Command("start_game"))
async def start_game(message: types.Message):
    game_code = None
    game = None
    for code, g in games.items():
        if g['creator'] == message.from_user.id:
            game_code = code
            game = g
            break

    if not game:
        await message.answer("❌ Ты не создатель игры")
        return

    if len(game['players']) < 4:
        await message.answer(f"❌ Нужно минимум 4 игрока. Сейчас: {len(game['players'])}")
        return

    game['status'] = 'playing'
    players = game['players']
    random.shuffle(players)

    # Раздаём роли
    roles = ['👻 Призрак', '🗡️ Убийца']
    
    # Остальные — детективы
    for i in range(2, len(players)):
        roles.append('🔍 Детектив')

    random.shuffle(roles)
    game['roles'] = {player: roles[i] for i, player in enumerate(players)}

    # Находим, кто есть кто
    ghost = None
    killer = None
    for player, role in game['roles'].items():
        if role == '👻 Призрак':
            ghost = player
        elif role == '🗡️ Убийца':
            killer = player

    # Отправляем роли в личку
    for player, role in game['roles'].items():
        text = f"🕯️ **Твоя роль в игре «Письма Призрака»**\n\nТы — **{role}**"

        # Если это Призрак — говорим, кто Убийца
        if role == '👻 Призрак' and killer:
            killer_name = game['names'].get(killer, str(killer))
            text += f"\n\n🔍 Ты знаешь, что Убийца — **{killer_name}**"

        # Если это Убийца — говорим, кто Призрак
        elif role == '🗡️ Убийца' and ghost:
            ghost_name = game['names'].get(ghost, str(ghost))
            text += f"\n\n👻 Ты знаешь, что Призрак — **{ghost_name}**"

        text += "\n\n👻 Игра началась! Обсуждайте в общем чате."
        await bot.send_message(player, text)

    # Выводим в группу
    await message.answer(
        f"🎭 **Игра началась!**\n\n"
        f"👥 Игроков: {len(game['players'])}\n"
        f"📩 Роли разданы в личные сообщения.\n\n"
        f"🗣️ Обсуждайте и ищите убийцу!"
    )

@dp.message(Command("roles"))
async def show_roles(message: types.Message):
    game_code = None
    game = None
    for code, g in games.items():
        if g['creator'] == message.from_user.id:
            game_code = code
            game = g
            break

    if not game:
        await message.answer("❌ Ты не создатель игры")
        return

    text = "📋 **Роли игроков:**\n\n"
    for player, role in game['roles'].items():
        name = game['names'].get(player, str(player))
        text += f"• {name} — {role}\n"

    await message.answer(text)

async def main():
    print("✅ Бот Письма Призрака запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
