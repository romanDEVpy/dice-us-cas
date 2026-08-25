import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN_HERE")

bot = Bot(TOKEN)
dp = Dispatcher()

# Небольшое временное состояние.
# Для такого простого бота БД не нужна.
users = {}

GAMES = {
    "dice": {
        "name": "Кубик",
        "emoji": "🎲",
        "values": 6,
    },
    "darts": {
        "name": "Дартс",
        "emoji": "🎯",
        "values": 6,
    },
    "basketball": {
        "name": "Баскетбол",
        "emoji": "🏀",
        "values": 5,
    },
    "football": {
        "name": "Футбол",
        "emoji": "⚽",
        "values": 5,
    },
    "bowling": {
        "name": "Боулинг",
        "emoji": "🎳",
        "values": 6,
    }
}


def games_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f'{game["emoji"]} {game["name"]}',
                    callback_data=f"game:{key}",
                )
            ]
            for key, game in GAMES.items()
        ]
    )


def outcomes_keyboard(game_key: str):
    game = GAMES[game_key]
    max_value = game["values"]

    buttons = []

    # Для обычных игр показываем все значения.
    if max_value <= 6:
        row = []

        for value in range(1, max_value + 1):
            row.append(
                InlineKeyboardButton(
                    text=str(value),
                    callback_data=f"bet:{game_key}:{value}",
                )
            )

            if len(row) == 3:
                buttons.append(row)
                row = []

        if row:
            buttons.append(row)

    # В слотах 64 возможных внутренних результата,
    # поэтому делаем сетку.
    else:
        row = []

        for value in range(1, 65):
            row.append(
                InlineKeyboardButton(
                    text=str(value),
                    callback_data=f"bet:{game_key}:{value}",
                )
            )

            if len(row) == 8:
                buttons.append(row)
                row = []

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="back_games",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def play_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎮 Бросить",
                    callback_data="play",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Изменить ставку",
                    callback_data="change_bet",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎲 Другая игра",
                    callback_data="back_games",
                )
            ],
        ]
    )


@dp.message(CommandStart())
async def start(message: Message):
    users.pop(message.from_user.id, None)

    await message.answer(
        "🎮 <b>Выбери игру:</b>",
        parse_mode="HTML",
        reply_markup=games_keyboard(),
    )


@dp.callback_query(F.data == "back_games")
async def back_games(callback: CallbackQuery):
    users.pop(callback.from_user.id, None)

    await callback.message.edit_text(
        "🎮 <b>Выбери игру:</b>",
        parse_mode="HTML",
        reply_markup=games_keyboard(),
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("game:"))
async def select_game(callback: CallbackQuery):
    game_key = callback.data.split(":")[1]
    game = GAMES.get(game_key)

    if not game:
        await callback.answer("Неизвестная игра")
        return

    users[callback.from_user.id] = {
        "game": game_key,
        "bet": None,
    }

    await callback.message.edit_text(
        f'{game["emoji"]} <b>{game["name"]}</b>\n\n'
        f"Выбери исход:",
        parse_mode="HTML",
        reply_markup=outcomes_keyboard(game_key),
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("bet:"))
async def select_bet(callback: CallbackQuery):
    _, game_key, value = callback.data.split(":")
    value = int(value)

    game = GAMES.get(game_key)

    if not game:
        await callback.answer("Ошибка")
        return

    users[callback.from_user.id] = {
        "game": game_key,
        "bet": value,
    }

    await callback.message.edit_text(
        f'{game["emoji"]} <b>{game["name"]}</b>\n\n'
        f"Твой исход: <b>{value}</b>\n\n"
        f"Нажми кнопку, чтобы запустить игру.",
        parse_mode="HTML",
        reply_markup=play_keyboard(),
    )

    await callback.answer()


@dp.callback_query(F.data == "change_bet")
async def change_bet(callback: CallbackQuery):
    data = users.get(callback.from_user.id)

    if not data:
        await callback.answer("Сначала выбери игру")
        return

    game_key = data["game"]
    game = GAMES[game_key]

    await callback.message.edit_text(
        f'{game["emoji"]} <b>{game["name"]}</b>\n\n'
        f"Выбери новый исход:",
        parse_mode="HTML",
        reply_markup=outcomes_keyboard(game_key),
    )

    await callback.answer()


@dp.callback_query(F.data == "play")
async def play(callback: CallbackQuery):
    data = users.get(callback.from_user.id)

    if not data or data.get("bet") is None:
        await callback.answer("Сначала выбери ставку")
        return

    game_key = data["game"]
    bet = data["bet"]

    game = GAMES[game_key]

    await callback.answer()

    # Именно Telegram генерирует результат Dice,
    # бот никак не выбирает выпавшее значение.
    dice_message = await callback.message.answer_dice(
        emoji=game["emoji"]
    )

    result = dice_message.dice.value

    if result == bet:
        text = (
            "✅ <b>ПОБЕДА!</b>\n\n"
            f"Твой выбор: <b>{bet}</b>\n"
            f"Выпало: <b>{result}</b>"
        )
    else:
        text = (
            "❌ <b>Не угадал</b>\n\n"
            f"Твой выбор: <b>{bet}</b>\n"
            f"Выпало: <b>{result}</b>"
        )

    await asyncio.sleep(3)

    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=play_keyboard(),
    )


async def main():
    print("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())