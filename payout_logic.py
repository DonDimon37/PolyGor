import os
import asyncpg
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
DB_DSN = os.getenv("DB_DSN")

async def resolve_market_and_payout(condition_id: str, winning_outcome: str, usdc_uah_rate: float):
    conn = await asyncpg.connect(DB_DSN)
    try:
        async with conn.transaction():
            await conn.execute('''
                UPDATE markets SET status = 'RESOLVED', winning_outcome = $1, updated_at = $2
                WHERE condition_id = $3
            ''', winning_outcome, datetime.now(), condition_id)

            bets = await conn.fetch('''
                SELECT bet_id, telegram_id, outcome, shares_bought 
                FROM bets WHERE condition_id = $1 AND status = 'PENDING'
            ''', condition_id)

            for bet in bets:
                if bet['outcome'] == winning_outcome:
                    payout_uah = float(bet['shares_bought']) * usdc_uah_rate
                    await conn.execute("UPDATE bets SET status = 'WON' WHERE bet_id = $1", bet['bet_id'])
                    await conn.execute('''
                        INSERT INTO transactions (telegram_id, bet_id, tx_type, amount_uah)
                        VALUES ($1, $2, 'WIN_PAYOUT', $3)
                    ''', bet['telegram_id'], bet['bet_id'], payout_uah)
                else:
                    await conn.execute("UPDATE bets SET status = 'LOST' WHERE bet_id = $1", bet['bet_id'])
    except Exception as e:
        print(f"Критическая ошибка БД при расчете рынка {condition_id}: {e}")
        raise 
    finally:
        await conn.close()
