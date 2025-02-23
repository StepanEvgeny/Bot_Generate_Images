import json
import time
import os
import base64
import requests
from PIL import Image
from io import BytesIO
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackContext
from telegram.ext import Application, CommandHandler, MessageHandler, filters


class Text2ImageAPI:

    def __init__(self, url, api_key, secret_key):
        self.URL = url
        self.AUTH_HEADERS = {
            'X-Key': f'Key {api_key}',
            'X-Secret': f'Secret {secret_key}',
        }

    def get_model(self):
        """ Получает ID модели для генерации изображений """
        try:
            response = requests.get(self.URL + 'key/api/v1/models', headers=self.AUTH_HEADERS)
            response.raise_for_status()
            data = response.json()
            return data[0]['id'] if data else None
        except (requests.RequestException, KeyError, IndexError) as e:
            print(f"Ошибка при получении модели: {e}")
            return None

    def generate(self, prompt, model, images=1, width=1024, height=1024):
        """ Отправляет запрос на генерацию изображения """
        params = {
            "type": "GENERATE",
            "numImages": images,
            "width": width,
            "height": height,
            "generateParams": {
                "query": prompt
            }
        }

        data = {
            'model_id': (None, model),
            'params': (None, json.dumps(params), 'application/json')
        }

        try:
            response = requests.post(self.URL + 'key/api/v1/text2image/run', headers=self.AUTH_HEADERS, files=data)
            response.raise_for_status()
            data = response.json()
            return data.get('uuid')
        except requests.RequestException as e:
            print(f"Ошибка при генерации изображения: {e}")
            return None

    def check_generation(self, request_id, attempts=10, delay=10):
        """ Проверяет статус генерации изображения """
        while attempts > 0:
            try:
                response = requests.get(self.URL + f'key/api/v1/text2image/status/{request_id}', headers=self.AUTH_HEADERS)
                response.raise_for_status()
                data = response.json()
                
                if data.get('status') == 'DONE':
                    return data.get('images', [])
            except requests.RequestException as e:
                print(f"Ошибка при проверке статуса: {e}")
            
            attempts -= 1
            time.sleep(delay)
        return None

    def decode_and_save_image(self, base64_string, filename="generated_image.jpg"):
        """ Декодирует изображение из Base64 и сохраняет его на диск """
        try:
            decoded_data = base64.b64decode(base64_string)
            image = Image.open(BytesIO(decoded_data))
            image.save(filename)
            return filename
        except (base64.binascii.Error, IOError) as e:
            print(f"Ошибка при декодировании или сохранении изображения: {e}")
            return None

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Привет! Отправьте мне текст, и я сгенерирую изображение по вашему описанию.")

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Этот бот использует нейросеть FusionBrain для генерации изображений по текстовым описаниям. "
        "Просто отправьте мне текст, и я превращу его в картинку! 🎨\n\n"
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Получить справку"
    )

async def handle_message(update: Update, context: CallbackContext):
    user_text = update.message.text
    waiting_message = await update.message.reply_text("Генерирую изображение, подождите...")  # Сохраняем сообщение
    
    api = Text2ImageAPI(API_URL, API_KEY, SECRET_KEY)
    model_id = api.get_model()
    
    if model_id:
        uuid = api.generate(user_text, model_id)
        if uuid:
            images = api.check_generation(uuid)
            if images:
                image_path = api.decode_and_save_image(images[0])
                if image_path:
                    await context.bot.delete_message(chat_id=update.message.chat_id, message_id=waiting_message.message_id)  # Удаляем сообщение
                    await context.bot.send_photo(chat_id=update.message.chat_id, photo=open(image_path, 'rb'))
                    return
                
    # Если произошла ошибка — не удаляем сообщение, а просто уведомляем
    await waiting_message.edit_text("Произошла ошибка при генерации изображения. Попробуйте снова.")

if __name__ == '__main__':
    API_URL = 'https://api-key.fusionbrain.ai/'
    API_KEY = os.getenv('FUSIONBRAIN_API_KEY', 'your_api_key_here')
    SECRET_KEY = os.getenv('FUSIONBRAIN_SECRET_KEY', 'your_secret_key_here')
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'your_telegram_token_here')

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()
