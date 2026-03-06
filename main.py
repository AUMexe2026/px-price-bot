import requests
import os
import time

# ──────────────── НАСТРОЙКИ ────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
MESSAGE_THREAD_ID = os.getenv("MESSAGE_THREAD_ID")
CMC_API_KEY = os.getenv("CMC_API_KEY")
COIN_SYMBOL = 'PX'

# Пороги для резких скачков (за 1 час)
PUMP_THRESHOLD = 30.0     # +30% за час → памп
DUMP_THRESHOLD = -20.0    # -20% за час → дамп
# ────────────────────────────────────────────

def get_price():
    try:
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        params = {"symbol": COIN_SYMBOL, "convert": "USD"}
        headers = {"Accepts": "application/json", "X-CMC_PRO_API_KEY": CMC_API_KEY}
        
        response = requests.get(url, headers=headers, params=params, timeout=12)
        response.raise_for_status()
        data = response.json()

        if data.get("status", {}).get("error_code", 0) != 0:
            print("Ошибка CMC:", data["status"].get("error_message"))
            return None, None, None

        coin = data["data"][COIN_SYMBOL]["quote"]["USD"]
        price = coin["price"]
        change_1h = coin.get("percent_change_1h")
        change_24h = coin.get("percent_change_24h")
        return price, change_1h, change_24h
    except Exception as e:
        print("Ошибка:", str(e))
        return None, None, None

def send_message(text, urgent=False):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    if MESSAGE_THREAD_ID:
        payload["message_thread_id"] = int(MESSAGE_THREAD_ID)
    
    if urgent:
        payload["text"] = f"🚨 **{text}** 🚨"
    
    r = requests.post(url, data=payload, timeout=10)
    if r.status_code == 200:
        print("Отправлено:", text)
    else:
        print("Ошибка отправки:", r.text)

# ──────────────── ЗАПУСК ────────────────
print("Запуск...")
price, change_1h, change_24h = get_price()

if price is None:
    print("Не удалось получить цену")
    exit()

# Формат цены: убираем лишние нули после точки
price_str = f"{price:,.5f}".rstrip('0').rstrip('.') if '.' in f"{price:,.5f}" else f"{price:,.0f}"
price_display = f"${price_str}"

# Процент за 24ч (основной)
change_24h_str = f"{change_24h:+.2f}%" if change_24h is not None else "?"

regular_text = f"{price_display}   <b>[{change_24h_str}]</b>"

# Проверяем резкий скачок по 1h (для памп/дамп)
if change_1h is not None:
    if change_1h >= PUMP_THRESHOLD:
        alert_text = f"РЕЗКИЙ ПАМП +{change_1h:.1f}% за час\n{price_display} <b>[{change_24h_str}]</b>"
        send_message(alert_text, urgent=True)
    elif change_1h <= DUMP_THRESHOLD:
        alert_text = f"РЕЗКИЙ ДАМП {change_1h:.1f}% за час\n{regular_text}"
        send_message(alert_text, urgent=True)
    else:
        send_message(regular_text)
else:
    # Если 1h нет — просто обычное
    send_message(regular_text)

print("Готово!")
