import os
import asyncio
import logging
import pandas as pd
import asyncpg
from aiogram.types import FSInputFile
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from py_clob_client.client import ClobClient
from web3 import Web3

# Загрузка переменных окружения
load_dotenv()
TG_TOKEN = os.getenv("TG_TOKEN")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URL = os.getenv("RPC_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

USDC_E_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
ERC20_ABI = '[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"uint8","type":"uint8"}],"type":"function"}]'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TG_TOKEN)
dp = Dispatcher()
w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = w3.eth.account.from_key(PRIVATE_KEY)

# Подключение к стакану Polymarket
clob_client = ClobClient("https://clob.polymarket.com", chain_id=137, key=PRIVATE_KEY)
clob_client.create_or_derive_api_creds()

def get_vault_balance():
    pol_balance = w3.from_wei(w3.eth.get_balance(account.address), 'ether')
    usdc_contract = w3.eth.contract(address=w3.to_checksum_address(USDC_E_ADDRESS), abi=ERC20_ABI)
    decimals = usdc_contract.functions.decimals().call()
    raw_usdc = usdc_contract.functions.balanceOf(account.address).call()
    return pol_balance, raw_usdc / (10 ** decimals)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🚀 *PolyGate VIP Terminal*\n\nДобро пожаловать. Система активна.", parse_mode="Markdown")

@dp.message(Command("vault"))
async def cmd_vault(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        pol, usdc = get_vault_balance()
        await message.answer(f"🔒 *Корпоративный пул (Polygon):*\n\n⛽ POL: `{pol:.4f}`\n💵 USDC.e: `{usdc:.2f} $`\n📍 `{account.address}`", parse_mode="Markdown")

@dp.message(Command("report"))
async def cmd_report(message: types.Message):
    # Защита: команду может вызывать только владелец пула
    if message.from_user.id != ADMIN_ID:
        return

    msg = await message.answer("📊 Собираю аналитику из базы данных. Формирую Excel...")
    
    # Подключаемся к базе
    conn = await asyncpg.connect(os.getenv("DB_DSN"))
    try:
        # Достаем все ставки
        bets = await conn.fetch("SELECT * FROM bets ORDER BY created_at DESC")
        
        if not bets:
            await msg.edit_text("⚠️ База ставок пока пуста. Нет данных для отчета.")
            return

        # Конвертируем данные в таблицу
        data = [dict(record) for record in bets]
        df = pd.DataFrame(data)
        
        # Убираем таймзоны для совместимости с Excel
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_localize(None)

        # Сохраняем во временный файл
        file_path = "PolyGate_Financial_Report.xlsx"
        df.to_excel(file_path, index=False)
        
        # Отправляем файл в Telegram
        report_file = FSInputFile(file_path)
        await message.answer_document(report_file, caption="📈 Финансовый отчет по пулу (PolyGate)")
        
        # Удаляем файл с сервера после отправки
        os.remove(file_path)
    except Exception as e:
        await message.answer(f"❌ Ошибка выгрузки: {e}")
    finally:
        await conn.close()
async def main():
    logging.info("PolyGate Gateway запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
