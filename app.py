from flask import Flask
import os
import threading
import asyncio
from bot import dp, bot # Импортируем твоего бота

app = Flask(__name__)

@app.route('/')
def health():
    return "Bot is running"

def run_bot():
    asyncio.run(dp.start_polling(bot))

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    threading.Thread(target=run_bot, daemon=True).start()
    # Запускаем Flask, чтобы Render видел порт
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)