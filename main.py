import requests
import os

# ──────────────── НАСТРОЙКИ ────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
MESSAGE_THREAD_ID = os.getenv("MESSAGE_THREAD_ID")

COIN_ID = "not-pixel"          # ← это ID на CoinGecko

# Пороги для резких скачков (за 24 часа)
PUMP_THRESHOLD = 30.0     # +30% за сутки → памп
DUMP_THRESHOLD = -20.0    # -20% за сутки → дамп
# ────────────────────────────────────────────

def get_price():
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": COIN_ID,
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        coin = data.get(COIN_ID, {})
        price = coin.get("usd")
        change_24h = coin.get("usd_24h_change")
        return price, change_24h
    except Exception as e:
        print("Ошибка CoinGecko:", str(e))
        return None, None

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
        payload["text"] = f"🚨 <b>{text}</b> 🚨"
    
    r = requests.post(url, data=payload, timeout=10)
    if r.status_code == 200:
        print("Отправлено:", text)
    else:
        print("Ошибка отправки:", r.text)

# ──────────────── ЗАПУСК ────────────────
print("Запуск бота (CoinGecko)...")
price, change_24h = get_price()

if price is None:
    print("Не удалось получить цену")
    exit()

# Формат цены (убираем лишние нули)
price_str = f"{price:,.5f}".rstrip('0').rstrip('.') if '.' in f"{price:,.5f}" else f"{price:,.0f}"
price_display = f"${price_str}"

change_str = f"{change_24h:+.2f}%" if change_24h is not None else "?"

regular_text = f"{price_display}  <b>[{change_str}]</b>"

# Проверка резкого скачка
if change_24h is not None:
    if change_24h >= PUMP_THRESHOLD:
        alert_text = f"РЕЗКИЙ ПАМП +{change_24h:.1f}% за сутки\n{regular_text}"
        send_message(alert_text, urgent=True)
    elif change_24h <= DUMP_THRESHOLD:
        alert_text = f"РЕЗКИЙ ДАМП {change_24h:.1f}% за сутки\n{regular_text}"
        send_message(alert_text, urgent=True)
    else:
        send_message(regular_text)
else:
    send_message(regular_text)

print("Готово!")
