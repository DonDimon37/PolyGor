import os
import asyncio
import logging
import pandas as pd
import asyncpg
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from dotenv import load_dotenv
from web3 import Web3

# --- 1. НАСТРОЙКИ ---
load_dotenv()
TG_TOKEN = os.getenv("TG_TOKEN")
DB_DSN = os.getenv("DB_DSN")
ADMIN_ID = int(os.getenv("ADMIN_ID") or 0)
RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

USDC_E_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
ERC20_ABI = '[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"uint8","type":"uint8"}],"type":"function"}]'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TG_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
w3 = Web3(Web3.HTTPProvider(RPC_URL))

class BetStates(StatesGroup):
    waiting_for_amount = State()

# --- 2. МЕНЮ И МАРКЕТЫ ---

def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="₿ BTC"), KeyboardButton(text="Ξ ETH"))
    builder.row(KeyboardButton(text="📊 Все рынки"))
    builder.row(KeyboardButton(text="🔒 Баланс пула"), KeyboardButton(text="📈 Отчет"))
    return builder.as_markup(resize_keyboard=True)

async def get_markets_from_db(category=None):
    conn = await asyncpg.connect(DB_DSN)
    try:
        if category:
            return await conn.fetch("SELECT id, question FROM markets WHERE category = $1 AND status = 'ACTIVE' ORDER BY id DESC LIMIT 5", category)
        return await conn.fetch("SELECT id, question FROM markets WHERE status = 'ACTIVE' ORDER BY id DESC LIMIT 10")
    finally: await conn.close()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🚀 **PolyGate VIP Terminal**\n\nСистема активна.", reply_markup=get_main_menu(), parse_mode="Markdown")

@dp.message(F.text.in_({"₿ BTC", "Ξ ETH", "📊 Все рынки"}))
async def show_markets(message: types.Message):
    cat_map = {"₿ BTC": "BTC", "Ξ ETH": "ETH"}
    markets = await get_markets_from_db(cat_map.get(message.text))
    if not markets:
        await message.answer("⚠️ Актуальных рынков нет.")
        return
    for m in markets:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="👍 ДА", callback_data=f"y_{m['id']}"),
            InlineKeyboardButton(text="👎 НЕТ", callback_data=f"n_{m['id']}")
        ]])
        await message.answer(f"🔹 *{m['question']}*", reply_markup=kb, parse_mode="Markdown")

# --- 3. ЛОГИКА СТАВКИ ---

@dp.callback_query(F.data.startswith("y_") | F.data.startswith("n_"))
async def process_bet_click(callback: types.CallbackQuery, state: FSMContext):
    side, m_id = ("YES" if callback.data.startswith("y_") else "NO"), int(callback.data.split("_")[1])
    await state.update_data(market_db_id=m_id, side=side)
    await state.set_state(BetStates.waiting_for_amount)
    await callback.answer()
    await callback.message.answer(f"✅ Выбрано: *{side}*\nВведите сумму в **USDC**:", parse_mode="Markdown")

@dp.message(BetStates.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    clean_text = message.text.replace(',', '.', 1)
    if not clean_text.replace('.', '', 1).isdigit():
        await message.answer("⚠️ Введите число.")
        return
    amount = float(clean_text)
    user_data = await state.get_data()
    conn = await asyncpg.connect(DB_DSN)
    try:
        market = await conn.fetchrow("SELECT condition_id, question FROM markets WHERE id = $1", user_data['market_db_id'])
        bet_id = await conn.fetchval("INSERT INTO bets (user_id, condition_id, side, amount_usdc, status) VALUES ($1, $2, $3, $4, 'PENDING') RETURNING id", message.from_user.id, market['condition_id'], user_data['side'], amount)
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ ОК", callback_data=f"adm_ok_{bet_id}"), InlineKeyboardButton(text="❌ НЕТ", callback_data=f"adm_no_{bet_id}")]])
        await bot.send_message(ADMIN_ID, f"🔔 **СТАВКА #{bet_id}**\n👤: {message.from_user.full_name}\n❓: {market['question']}\n🎯: {user_data['side']}\n💵: {amount} USDC", reply_markup=admin_kb, parse_mode="Markdown")
        await message.answer(f"📥 Ставка #{bet_id} отправлена на проверку.", parse_mode="Markdown")
    finally:
        await conn.close()
        await state.clear()

@dp.callback_query(F.data.startswith("adm_"))
async def admin_action(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    _, action, bet_id = callback.data.split("_")
    conn = await asyncpg.connect(DB_DSN)
    try:
        bet = await conn.fetchrow("SELECT user_id, amount_usdc FROM bets WHERE id = $1", int(bet_id))
        status = "APPROVED" if action == "ok" else "REJECTED"
        await conn.execute("UPDATE bets SET status = $1 WHERE id = $2", status, int(bet_id))
        await bot.send_message(bet['user_id'], f"{'🟢' if action=='ok' else '🔴'} Ставка #{bet_id} {'подтверждена' if action=='ok' else 'отклонена'}.", parse_mode="Markdown")
        await callback.message.edit_text(f"{callback.message.text}\n\n🎬 **Итог:** {status}")
    finally: await conn.close()

# --- 4. РАСШИРЕННЫЙ ОТЧЕТ И БАЛАНС ---

@dp.message(F.text == "🔒 Баланс пула")
async def view_vault(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        account = w3.eth.account.from_key(PRIVATE_KEY)
        pol = w3.from_wei(w3.eth.get_balance(account.address), 'ether')
        usdc_c = w3.eth.contract(address=w3.to_checksum_address(USDC_E_ADDRESS), abi=ERC20_ABI)
        usdc = usdc_c.functions.balanceOf(account.address).call() / (10**6)
        await message.answer(f"🔒 **Пул**\n⛽ POL: `{pol:.4f}`\n💵 USDC: `{usdc:.2f}`", parse_mode="Markdown")
    except Exception as e: await message.answer(f"❌ Ошибка Web3: {e}")

@dp.message(F.text == "📈 Отчет")
async def btn_report(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    conn = await asyncpg.connect(DB_DSN)
    try:
        bets = await conn.fetch("SELECT * FROM bets ORDER BY created_at DESC")
        if not bets:
            await message.answer("⚠️ Ставок нет.")
            return

        df = pd.DataFrame([dict(r) for r in bets])
        
        # Считаем статистику
        total_vol = df['amount_usdc'].sum()
        won_vol = df[df['status'] == 'WON']['amount_usdc'].sum()
        lost_vol = df[df['status'] == 'LOST']['amount_usdc'].sum()
        pending_count = len(df[df['status'].isin(['PENDING', 'APPROVED'])])

        summary_text = (
            f"📊 **Аналитика пула**\n\n"
            f"💰 Общий оборот: `{total_vol:.2f} USDC`\n"
            f"✅ Выиграно: `{won_vol:.2f} USDC`\n"
            f"❌ Проиграно: `{lost_vol:.2f} USDC`\n"
            f"⏳ В игре: `{pending_count}` ставок\n"
        )

        path = "PolyGate_Advanced_Report.xlsx"
        df.to_excel(path, index=False)
        await message.answer_document(FSInputFile(path), caption=summary_text, parse_mode="Markdown")
        os.remove(path)
    finally: await conn.close()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
