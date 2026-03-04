import os
import subprocess
import logging
import tempfile
import asyncio
import urllib.request
import tarfile
import glob
import shutil
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Скачиваем ffmpeg, если его нет
if not os.path.exists("./ffmpeg"):
    print("📥 Скачиваю ffmpeg...")
    url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
    urllib.request.urlretrieve(url, "ffmpeg-release-amd64-static.tar.xz")
    
    with tarfile.open("ffmpeg-release-amd64-static.tar.xz") as tar:
        tar.extractall()
    
    ffmpeg_dir = glob.glob("ffmpeg-*-amd64-static")[0]
    shutil.move(os.path.join(ffmpeg_dir, "ffmpeg"), "./ffmpeg")
    os.chmod("./ffmpeg", 0o755)
    
    shutil.rmtree(ffmpeg_dir)
    os.remove("ffmpeg-release-amd64-static.tar.xz")
    print("✅ ffmpeg установлен")
else:
    print("✅ ffmpeg уже есть")

# Настройки логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота
TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет 👋\n"
        "🎥 Отправь мне видео или анимацию, и я сделаю кружок\n\n"
        "👤 Автор: @TommiFox"
    )

async def author(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("👤 Автор бота: @TommiFox")

async def videotonote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Проверяем, есть ли видео или анимация
    if not (update.message.video or update.message.animation):
        await update.message.reply_text("🎥 Отправь видео или анимацию")
        return

    msg = await update.message.reply_text("⏳ Обрабатываю...")

    try:
        # Получаем файл (видео или анимацию)
        if update.message.video:
            file = await update.message.video.get_file()
            duration = update.message.video.duration
        else:  # анимация
            file = await update.message.animation.get_file()
            duration = 0  # для анимации длительность не обязательна

        with tempfile.TemporaryDirectory() as tmpdirname:
            inputpath = os.path.join(tmpdirname, "input.mp4")
            outputpath = os.path.join(tmpdirname, "output.mp4")

            await file.download_to_drive(custom_path=inputpath)

            # Конвертируем в кружок
            cmd = ["./ffmpeg", "-y", "-i", inputpath, 
                   "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=240:240", 
                   "-c:a", "copy", outputpath]

            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if process.returncode != 0:
                await msg.edit_text("❌ Ошибка при обработке")
                return

            await msg.delete()
            
            with open(outputpath, "rb") as f:
                await context.bot.sendVideoNote(
                    chat_id=update.effective_chat.id,
                    video_note=f,
                    duration=duration
                )
    except Exception as e:
        logger.exception("Error")
        await msg.edit_text(f"❌ Ошибка")

def main():
    if not TOKEN:
        logger.error("Нет токена!")
        return
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("author", author))
    app.add_handler(MessageHandler(filters.VIDEO | filters.ANIMATION, videotonote))
    app.run_polling()

if __name__ == "__main__":
    main()
