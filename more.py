import requests
import time
import hashlib

# ==========================
# CONFIG
# ==========================

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1470940001150832776/qkCw4pWux_JqKFRCK3MqtwtgHgKUyvAJt-dt-UAfJwsoBK0tdymDlV541hBHjyOEG4XE"

CAPITAL = 100
TRADING_FEE = 0.001
WITHDRAWAL_FEE_PERCENT = 0.002
MAX_PROFIT_ALERT = 15
CHECK_INTERVAL = 20

sent_opportunities = set()

# ==========================
# DISCORD ALERT
# ==========================

def send_discord(message):
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": message})
    except:
        pass

# ==========================
# GET SYMBOLS
# ==========================

def get_mexc_symbols():
    url = "https://api.mexc.com/api/v3/exchangeInfo"
    data = requests.get(url).json()
    return set(
        s["symbol"] for s in data["symbols"]
        if s["quoteAsset"] == "USDT" and s["status"] == "1"
    )

def get_gate_symbols():
    url = "https://api.gateio.ws/api/v4/spot/currency_pairs"
    data = requests.get(url).json()
    return set(
        s["id"].replace("_", "") for s in data
        if s["quote"] == "USDT"
    )

# ==========================
# ORDER BOOK
# ==========================

def get_mexc_orderbook(symbol):
    url = f"https://api.mexc.com/api/v3/depth?symbol={symbol}&limit=5"
    data = requests.get(url).json()
    best_ask = float(data["asks"][0][0])
    best_bid = float(data["bids"][0][0])
    return best_ask, best_bid

def get_gate_orderbook(symbol):
    pair = symbol[:-4] + "_USDT"
    url = f"https://api.gateio.ws/api/v4/spot/order_book?currency_pair={pair}&limit=5"
    data = requests.get(url).json()
    best_ask = float(data["asks"][0][0])
    best_bid = float(data["bids"][0][0])
    return best_ask, best_bid

# ==========================
# PROFIT CALCULATOR
# ==========================

def calculate_profit(buy_price, sell_price):
    amount = CAPITAL / buy_price
    amount_after_buy_fee = amount * (1 - TRADING_FEE)
    amount_after_withdraw = amount_after_buy_fee * (1 - WITHDRAWAL_FEE_PERCENT)
    final_usdt = amount_after_withdraw * sell_price
    final_usdt_after_sell_fee = final_usdt * (1 - TRADING_FEE)
    profit = final_usdt_after_sell_fee - CAPITAL
    return round(profit, 2)

def calculate_spread(buy_price, sell_price):
    spread = ((sell_price - buy_price) / buy_price) * 100
    return round(spread, 2)

# ==========================
# MAIN LOOP
# ==========================

def run():
    print("🚀 Arbitrage Scanner Started")

    mexc_symbols = get_mexc_symbols()
    gate_symbols = get_gate_symbols()

    common_pairs = list(mexc_symbols.intersection(gate_symbols))
    print(f"🔎 Found {len(common_pairs)} common pairs")

    while True:
        for symbol in common_pairs:
            try:
                mexc_ask, mexc_bid = get_mexc_orderbook(symbol)
                gate_ask, gate_bid = get_gate_orderbook(symbol)

                # Scenario 1
                profit1 = calculate_profit(mexc_ask, gate_bid)

                # Scenario 2
                profit2 = calculate_profit(gate_ask, mexc_bid)

                if profit1 > profit2:
                    best_profit = profit1
                    buy_exchange = "MEXC"
                    sell_exchange = "Gate.io"
                    buy_price = mexc_ask
                    sell_price = gate_bid
                else:
                    best_profit = profit2
                    buy_exchange = "Gate.io"
                    sell_exchange = "MEXC"
                    buy_price = gate_ask
                    sell_price = mexc_bid

                spread_percent = calculate_spread(buy_price, sell_price)

                if 0 < best_profit <= MAX_PROFIT_ALERT:
                    unique_id = hashlib.md5(
                        f"{symbol}{buy_exchange}{sell_exchange}{best_profit}".encode()
                    ).hexdigest()

                    if unique_id not in sent_opportunities:
                        sent_opportunities.add(unique_id)

                        message = (
                            f"🔥 ARBITRAGE FOUND\n\n"
                            f"Coin: {symbol}\n"
                            f"Buy: {buy_exchange} @ {buy_price}\n"
                            f"Sell: {sell_exchange} @ {sell_price}\n"
                            f"Spread: {spread_percent}%\n"
                            f"Capital: ${CAPITAL}\n"
                            f"Estimated Profit: ${best_profit}"
                        )

                        print(message)
                        send_discord(message)

            except:
                continue

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run()
