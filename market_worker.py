import os
import asyncio
import aiohttp
import asyncpg
from dotenv import load_dotenv
from payout_logic import resolve_market_and_payout

load_dotenv()
DB_DSN = os.getenv("DB_DSN")
GAMMA_API_URL = "https://gamma-api.polymarket.com/markets/{}"
POLL_INTERVAL_SECONDS = 300 

async def fetch_market_status(session: aiohttp.ClientSession, condition_id: str):
    try:
        async with session.get(GAMMA_API_URL.format(condition_id), timeout=10) as response:
            if response.status == 200: return await response.json()
    except: pass
    return None

async def market_worker():
    print("🔄 Полинг рынков (Worker) запущен...")
    current_usdc_uah_rate = 41.50 

    while True:
        try:
            conn = await asyncpg.connect(DB_DSN)
            active_markets = await conn.fetch("SELECT condition_id FROM markets WHERE status = 'ACTIVE'")
            
            if active_markets:
                async with aiohttp.ClientSession() as session:
                    for market in active_markets:
                        cond_id = market['condition_id']
                        data = await fetch_market_status(session, cond_id)
                        
                        if data and data.get('closed') is True:
                            tokens = data.get('tokens', [])
                            winning_outcome = next(('YES' if i == 0 else 'NO' for i, t in enumerate(tokens) if t.get('winner')), None)
                            
                            if winning_outcome:
                                print(f"✅ Рынок {cond_id} завершен! Победитель: {winning_outcome}")
                                await resolve_market_and_payout(cond_id, winning_outcome, current_usdc_uah_rate)
            await conn.close()
        except Exception as e:
            print(f"⚠️ Ошибка воркера: {e}")
        
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    asyncio.run(market_worker())
