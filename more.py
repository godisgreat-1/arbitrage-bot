import ccxt
import time
import requests

# ================== CONFIG ==================
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1470940001150832776/qkCw4pWux_JqKFRCK3MqtwtgHgKUyvAJt-dt-UAfJwsoBK0tdymDlV541hBHjyOEG4XE"
CAPITAL_USD = 100
MIN_PROFIT_USD = 1.0   # alert only if profit >= $1
SCAN_DELAY = 20        # seconds

TRADING_FEE = 0.001    # 0.1% typical spot fee

# rough withdrawal fee estimates (USDT-based)
WITHDRAW_FEES = {
    "binance": 1.0,
    "bybit": 1.0,
    "gateio": 1.5,
    "mexc": 1.0
}

# ================== EXCHANGES ==================
exchanges = {
    "binance": ccxt.binance(),
    "bybit": ccxt.bybit(),
    "gateio": ccxt.gateio(),
    "mexc": ccxt.mexc()
}

for ex in exchanges.values():
    ex.load_markets()

# ================== HELPERS ==================
def send_discord(msg):
    requests.post(DISCORD_WEBHOOK, json={"content": msg})

def get_best_prices(exchange, symbol):
    try:
        ob = exchange.fetch_order_book(symbol, limit=5)
        ask = ob["asks"][0][0] if ob["asks"] else None
        bid = ob["bids"][0][0] if ob["bids"] else None
        return ask, bid
    except:
        return None, None

def simulate_profit(buy_price, sell_price, buy_ex, sell_ex):
    amount = CAPITAL_USD / buy_price
    buy_cost = CAPITAL_USD * (1 + TRADING_FEE)
    sell_value = amount * sell_price * (1 - TRADING_FEE)
    withdraw_fee = WITHDRAW_FEES[buy_ex]
    return sell_value - buy_cost - withdraw_fee

# ================== MAIN LOOP ==================
print("🚀 Arbitrage Scanner Started (NO API KEYS)")
send_discord("🚀 Arbitrage Scanner Started\nCapital: $100")

while True:
    try:
        symbols = set(
            s for s in exchanges["binance"].symbols
            if s.endswith("/USDT")
        )

        for symbol in symbols:
            prices = {}

            for name, ex in exchanges.items():
                ask, bid = get_best_prices(ex, symbol)
                if ask and bid:
                    prices[name] = {"ask": ask, "bid": bid}

            for buy_ex in prices:
                for sell_ex in prices:
                    if buy_ex == sell_ex:
                        continue

                    buy_price = prices[buy_ex]["ask"]
                    sell_price = prices[sell_ex]["bid"]

                    if sell_price <= buy_price:
                        continue

                    profit = simulate_profit(
                        buy_price, sell_price, buy_ex, sell_ex
                    )

                    if profit >= MIN_PROFIT_USD:
                        msg = (
                            f"🔥 ARBITRAGE FOUND\n"
                            f"Coin: {symbol}\n"
                            f"Buy: {buy_ex} @ {buy_price}\n"
                            f"Sell: {sell_ex} @ {sell_price}\n"
                            f"Capital: $100\n"
                            f"Estimated Profit: ${profit:.2f}"
                        )
                        print(msg)
                        send_discord(msg)

        time.sleep(SCAN_DELAY)

    except Exception as e:
        print("Error:", e)
        time.sleep(10)
