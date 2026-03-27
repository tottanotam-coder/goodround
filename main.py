import os
import subprocess
import tempfile
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# ========== УСТАНОВКА FFMPEG (как в вашем работающем боте) ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Устанавливаем wget и xz-utils
subprocess.run(["apt-get", "update"], check=False, capture_output=True)
subprocess.run(["apt-get", "install", "-y", "wget", "xz-utils"], check=False, capture_output=True)

# Скачиваем ffmpeg, если его нет
if not os.path.exists("./ffmpeg"):
    logger.info("Скачиваю ffmpeg...")
    subprocess.run(["wget", "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"], check=True)
    subprocess.run(["tar", "-xf", "ffmpeg-release-amd64-static.tar.xz"], check=True)
    subprocess.run("cp ffmpeg-*-amd64-static/ffmpeg ./ffmpeg", shell=True, check=True)
    subprocess.run(["chmod", "+x", "./ffmpeg"], check=True)
    subprocess.run("rm -rf ffmpeg-release-amd64-static.tar.xz ffmpeg-*-amd64-static", shell=True, check=True)
    logger.info("✅ ffmpeg установлен")
else:
    logger.info("✅ ffmpeg уже есть")

FFMPEG_PATH = "./ffmpeg"
# ===========================================================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(content_types=['audio', 'voice', 'document'])
async def convert_to_voice(message: types.Message):
    try:
        await message.reply("⏳ Конвертирую...")

        if message.audio:
            file = message.audio
        elif message.voice:
            file = message.voice
        elif message.document:
            file = message.document
        else:
            return

        file_info = await bot.get_file(file.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)

        with tempfile.TemporaryDirectory() as tmpdirname:
            input_path = os.path.join(tmpdirname, "input.ogg")
            output_path = os.path.join(tmpdirname, "output.ogg")

            with open(input_path, "wb") as f:
                f.write(downloaded_file.getvalue())

            ffmpeg_cmd = [
                FFMPEG_PATH, "-i", input_path,
                "-c:a", "libopus",
                "-ar", "48000",
                "-b:a", "64k",
                "-ac", "1",
                "-f", "ogg",
                output_path
            ]
            
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                await message.reply(f"Ошибка конвертации: {result.stderr[:200]}")
                return

            with open(output_path, "rb") as f:
                await message.reply_voice(f)

    except Exception as e:
        await message.reply(f"Ошибка: {e}")

if __name__ == "__main__":
    logger.info("Бот запущен")
    executor.start_polling(dp, skip_updates=True)
