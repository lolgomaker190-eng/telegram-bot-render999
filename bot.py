import os
import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import json

# === КОНФИГУРАЦИЯ ===
# ПРИОРИТЕТ 1: Пытаемся взять ключи из переменных окружения (как на Render).
# ПРИОРИТЕТ 2: Если их там нет, используем ключи, заданные ниже (для локального запуска).
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', "8538666427:AAGdVXvxAMWtmjNtSJEC4W0oAvm3JFplfXE")  # Ваш ключ
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', "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")  # Ваш ключ
MODEL_NAME = "nex-agi/deepseek-v3.1-nex-n1:free"

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === ОБРАБОТЧИКИ КОМАНД ТЕЛЕГРАМ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Я бот с нейросетью. Задай мне вопрос!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    await update.message.reply_chat_action(action="typing")

    try:
        answer = await get_ai_response(user_message)
        if len(answer) > 4096:
            answer = answer[:4090] + "\n[...]"
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка. Попробуй еще раз.")

# === ЗАПРОС К OPENROUTER API ===
async def get_ai_response(user_message: str) -> str:
    """Отправляет запрос к нейросети и возвращает ответ."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://render.com",
        "X-Title": "Telegram AI Bot"
    }
    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Ты полезный ассистент. Отвечай на русском."},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 1000
    }

    response = requests.post(url, headers=headers, json=data, timeout=60)
    response.raise_for_status()
    result = response.json()
    return result['choices'][0]['message']['content']

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот жив и работает!")

# === ОСНОВНАЯ ФУНКЦИЯ ===
def main():
    """Определяет режим запуска: вебхук на Render или polling локально."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("health", health))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Режим для Render (через вебхук)
    if os.getenv('RENDER'):
        from telegram.ext import Updater
        import asyncio
        
        async def set_webhook_on_start():
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            # Имя сервиса берем из переменной окружения Render
            service_name = os.getenv('RENDER_SERVICE_NAME', 'your-service-name')
            webhook_url = f"https://{service_name}.onrender.com/{TELEGRAM_BOT_TOKEN}"
            await bot.set_webhook(url=webhook_url)
            logger.info(f"Webhook установлен: {webhook_url}")

        async def main_async():
            await set_webhook_on_start()
            port = int(os.getenv('PORT', 8443))
            service_name = os.getenv('RENDER_SERVICE_NAME', 'your-service-name')
            webhook_url = f"https://{service_name}.onrender.com/{TELEGRAM_BOT_TOKEN}"
            
            await application.run_webhook(
                listen="0.0.0.0",
                port=port,
                url_path=TELEGRAM_BOT_TOKEN,
                webhook_url=webhook_url
            )

        asyncio.run(main_async())
    else:
        # Режим для локальной отладки (polling)
        logger.info("Запуск в режиме polling (локальная отладка)...")
        application.run_polling()

if __name__ == '__main__':
    main()
