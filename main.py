import requests
import os
import logging

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

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_price():
    """Получает цену и изменения с CoinMarketCap"""
    try:
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        params = {"symbol": COIN_SYMBOL, "convert": "USD"}
        headers = {
            "Accepts": "application/json",
            "X-CMC_PRO_API_KEY": CMC_API_KEY,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=12)
        response.raise_for_status()
        data = response.json()

        # Проверка на ошибки API
        error_code = data.get("status", {}).get("error_code", 0)
        if error_code != 0:
            error_msg = data["status"].get("error_message", "Неизвестная ошибка")
            logging.error(f"Ошибка CMC ({error_code}): {error_msg}")
            return None, None, None

        coin = data["data"][COIN_SYMBOL]["quote"]["USD"]
        price = coin["price"]
        change_1h = coin.get("percent_change_1h")
        change_24h = coin.get("percent_change_24h")
        return price, change_1h, change_24h
        
    except requests.exceptions.Timeout:
        logging.error("Таймаут запроса к CMC")
        return None, None, None
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка сети: {e}")
        return None, None, None
    except Exception as e:
        logging.error(f"Неожиданная ошибка: {type(e).__name__}: {e}")
        return None, None, None

def send_message(text, urgent=False):
    """Отправляет сообщение в Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Формируем текст с учётом срочности (используем HTML-теги)
    if urgent:
        formatted_text = f"🚨 <b>{text}</b> 🚨"
    else:
        formatted_text = text
    
    payload = {
        "chat_id": CHAT_ID,
        "text": formatted_text,
        "parse_mode": "HTML"
    }
    
    # Добавляем ID топика, если указан и не пустой
    if MESSAGE_THREAD_ID and MESSAGE_THREAD_ID.strip():
        try:
            payload["message_thread_id"] = int(MESSAGE_THREAD_ID.strip())
        except ValueError:
            logging.warning("MESSAGE_THREAD_ID не является числом, пропускаем")
    
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            logging.info(f"Сообщение отправлено: {text[:50]}...")
            return True
        else:
            logging.error(f"Ошибка Telegram API {r.status_code}: {r.text}")
            return False
    except Exception as e:
        logging.error(f"Ошибка отправки в Telegram: {e}")
        return False

# ──────────────── ЗАПУСК ────────────────
def main():
    logging.info(f"Запуск бота для монеты: {COIN_SYMBOL}")
    
    # Проверяем наличие всех необходимых переменных
    required_vars = ["BOT_TOKEN", "CHAT_ID", "CMC_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logging.error(f"Отсутствуют переменные окружения: {missing}")
        return
    
    price, change_1h, change_24h = get_price()

    if price is None:
        logging.error("Не удалось получить цену, завершаю работу")
        return

    # Формат цены: убираем лишние нули после точки
    price_formatted = f"{price:,.5f}".rstrip('0').rstrip('.')
    price_display = f"${price_formatted}"

    # Форматируем проценты
    change_24h_str = f"{change_24h:+.2f}%" if change_24h is not None else "N/A"
    change_1h_str = f"{change_1h:+.2f}%" if change_1h is not None else None

    # Базовое сообщение
    regular_text = f"{price_display}   <b>[{change_24h_str}]</b>"

    # Проверяем резкие скачки по 1h
    if change_1h is not None:
        if change_1h >= PUMP_THRESHOLD:
            alert_text = f"🚀 РЕЗКИЙ ПАМП +{change_1h:.1f}% за час!\n{price_display} <b>[{change_24h_str}]</b>"
            send_message(alert_text, urgent=True)
        elif change_1h <= DUMP_THRESHOLD:
            alert_text = f"📉 РЕЗКИЙ ДАМП {change_1h:.1f}% за час!\n{price_display} <b>[{change_24h_str}]</b>"
            send_message(alert_text, urgent=True)
        else:
            send_message(regular_text)
    else:
        # Если данных за 1 час нет — отправляем обычное сообщение
        send_message(regular_text)

    logging.info("✅ Готово!")

if __name__ == "__main__":
    main()
