# PolyGate (PolyGor) 🌐

**PolyGate** — это Web3-шлюз корпоративного уровня для B2B2C сегмента. Система позволяет бесшовно интегрировать традиционные фиатные платформы (iGaming) с глобальными рынками предсказаний (Polymarket) через блокчейн Polygon.

## 🏗 Обзор архитектуры

Система спроектирована как микросервисная архитектура, полностью изолирующая фиатные расчеты от крипто-ликвидности:

1. **Смарт-контракт Vault (Solidity):** Безопасно взаимодействует с Gnosis Conditional Tokens Framework (CTF). Выполняет функции `splitPosition` и `mergePositions` для управления корпоративным пулом USDC.
2. **Telegram Gateway (Python/aiogram):** Интерфейс для VIP-пользователей. Обрабатывает ордеры на ставки, проверяет балансы и генерирует финансовые отчеты в Excel в реальном времени.
3. **Market Resolution Worker (Python):** Фоновый процесс (воркер), который опрашивает Gamma API на предмет закрытых рынков и автоматически запускает логику выплат.
4. **Клиринговый модуль (PostgreSQL):** Строгая реляционная схема данных для отслеживания пользователей, активных рынков, ожидающих ставок и истории транзакций, что гарантирует отсутствие потерь данных при сбоях сети.

## 🚀 Технологический стек

* **Backend:** Python 3.10+, `aiogram`, `asyncpg`, `aiohttp`, `pandas`
* **Web3 интеграция:** `web3.py`, `py-clob-client` (Polymarket API)
* **Смарт-контракты:** Solidity, Conditional Tokens Framework (CTF)
* **База данных:** PostgreSQL 14+
* **Инфраструктура:** Ubuntu VPS, `systemd` (демонизация сервисов)

## ⚙️ Развертывание и настройка

### 1. Переменные окружения
Создайте файл `.env` в корневой директории:
```env
TG_TOKEN=ваш_токен_бота
ADMIN_ID=ваш_telegram_id
PRIVATE_KEY=приватный_ключ_кошелька_polygon
RPC_URL=[https://polygon-rpc.com](https://polygon-rpc.com)
DB_DSN=postgresql://polygate_user:password@localhost:5432/polygate
