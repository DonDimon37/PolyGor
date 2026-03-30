import os
import aiohttp
import asyncpg
import asyncio
from dotenv import load_dotenv

load_dotenv()
DB_DSN = os.getenv("DB_DSN")

# Используем эндпоинт Markets с фильтром по объему (Volume 24h)
GAMMA_API = "https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=50&order=volume24hr&ascending=false"

async def fetch_and_update():
    conn = await asyncpg.connect(DB_DSN)
    # Очищаем старые неактуальные данные перед обновлением
    await conn.execute("DELETE FROM markets;")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(GAMMA_API) as resp:
            markets_data = await resp.json()
            
            for m in markets_data:
                condition_id = m.get('conditionId')
                question = m.get('question')
                # Пытаемся определить категорию из тегов или названия
                raw_cat = m.get('category', 'General')
                
                # Умная категоризация для твоих кнопок
                title_upper = question.upper()
                if "BTC" in title_upper or "BITCOIN" in title_upper:
                    category = "BTC"
                elif "ETH" in title_upper or "ETHEREUM" in title_upper:
                    category = "ETH"
                else:
                    category = raw_cat

                if condition_id and question:
                    await conn.execute("""
                        INSERT INTO markets (condition_id, question, category, status)
                        VALUES ($1, $2, $3, 'ACTIVE')
                        ON CONFLICT (condition_id) DO UPDATE 
                        SET question = EXCLUDED.question, category = EXCLUDED.category
                    """, condition_id, question, category)
    
    await conn.close()
    print("✅ База данных обновлена: загружены ТОП-50 актуальных рынков по объему.")

if __name__ == "__main__":
    asyncio.run(fetch_and_update())
