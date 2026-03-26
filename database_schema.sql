CREATE TABLE users (
    telegram_id BIGINT PRIMARY KEY,
    casino_user_id VARCHAR(255) UNIQUE NOT NULL, 
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE markets (
    condition_id VARCHAR(255) PRIMARY KEY, 
    question TEXT NOT NULL,
    category VARCHAR(50), 
    status VARCHAR(20) DEFAULT 'ACTIVE', 
    winning_outcome VARCHAR(10), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE bets (
    bet_id SERIAL PRIMARY KEY,
    telegram_id BIGINT REFERENCES users(telegram_id),
    condition_id VARCHAR(255) REFERENCES markets(condition_id),
    outcome VARCHAR(10) NOT NULL, 
    amount_uah DECIMAL(12, 2) NOT NULL, 
    amount_usdc DECIMAL(12, 4) NOT NULL, 
    buy_price_usdc DECIMAL(5, 4) NOT NULL, 
    shares_bought DECIMAL(12, 4) NOT NULL, 
    status VARCHAR(20) DEFAULT 'PENDING', 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transactions (
    tx_id SERIAL PRIMARY KEY,
    telegram_id BIGINT REFERENCES users(telegram_id),
    bet_id INT REFERENCES bets(bet_id),
    tx_type VARCHAR(20) NOT NULL, 
    amount_uah DECIMAL(12, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bets_status ON bets(status);
CREATE INDEX idx_markets_status ON markets(status);
