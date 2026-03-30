import os
import asyncio
import logging
import aiohttp
import asyncpg
from dotenv import load_dotenv
from aiogram import Bot

# 1. НАСТРОЙКИ
load_dotenv()
DB_DSN = os.getenv("DB_DSN")
TG_TOKEN = os.getenv("TG_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID") or 0)

# Используем базовый эндпоинт для поиска
GAMMA_SEARCH_API = "https://gamma-api.polymarket.com/markets?condition_id="

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TG_TOKEN)

async def check_payouts():
    conn = await asyncpg.connect(DB_DSN)
    
    # Берем подтвержденные ставки
    active_bets = await conn.fetch("SELECT * FROM bets WHERE status = 'APPROVED'")
    
    if not active_bets:
        logging.info("Нет активных ставок для проверки.")
        await conn.close()
        await bot.session.close()
        return

    async with aiohttp.ClientSession() as session:
        for bet in active_bets:
            bet_id = bet['id']
            user_id = bet['user_id']
            cond_id = bet['condition_id']
            user_side = bet['side']
            
            logging.info(f"🔎 Проверка ставки #{bet_id} (Hash: {cond_id[:10]}...)")

            try:
                # Ищем маркет по condition_id
                async with session.get(f"{GAMMA_SEARCH_API}{cond_id}") as resp:
                    if resp.status != 200:
                        logging.warning(f"⚠️ Ошибка API ({resp.status}) для ставки #{bet_id}")
                        continue
                    
                    data = await resp.json()
                    
                    # API возвращает список, берем первый элемент
                    if not data or len(data) == 0:
                        logging.warning(f"❓ Рынок не найден в API Polymarket")
                        continue
                    
                    market_data = data[0]
                    
                    # Проверяем статус закрытия
                    is_closed = market_data.get('closed', False)
                    has_res = market_data.get('hasResolution', False)
                    
                    if is_closed and has_res:
                        res_index = market_data.get('winningOutcomeIndex')
                        
                        if res_index is None:
                            logging.info(f"⏳ Рынок закрыт, но индекс результата еще не определен.")
                            continue

                        # Определяем победителя (0 = YES, 1 = NO)
                        actual_outcome = "YES" if str(res_index) == "0" else "NO"
                        
                        if user_side == actual_outcome:
                            new_status = "WON"
                            msg = f"💰 **СТАВКА #{bet_id} ВЫИГРАЛА!**\n\nРезультат: *{actual_outcome}*\nОжидайте выплату профита."
                        else:
                            new_status = "LOST"
                            msg = f"📉 **СТАВКА #{bet_id} ПРОИГРАЛА**\n\nРезультат: *{actual_outcome}*"

                        # Обновляем базу
                        await conn.execute("UPDATE bets SET status = $1 WHERE id = $2", new_status, bet_id)
                        
                        # Уведомляем
                        await bot.send_message(user_id, msg, parse_mode="Markdown")
                        await bot.send_message(ADMIN_ID, f"📑 Ставка #{bet_id} рассчитана: {new_status}")
                        logging.info(f"✅ Ставка #{bet_id} обновлена: {new_status}")
                    else:
                        logging.info(f"⌛ Ставка #{bet_id}: Рынок еще активен.")

            except Exception as e:
                logging.error(f"❌ Ошибка ставки {bet_id}: {e}")

    await conn.close()
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(check_payouts())
