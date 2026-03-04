import os
import subprocess
import logging
import tempfile
import asyncio

# Устанавливаем wget и xz-utils
subprocess.run(["apt-get", "update"], check=False)
subprocess.run(["apt-get", "install", "-y", "wget", "xz-utils"], check=False)

# Скачиваем ffmpeg, если его нет
if not os.path.exists("./ffmpeg"):
    subprocess.run(["apt-get", "update"], check=False)
    subprocess.run(["apt-get", "install", "-y", "wget", "xz-utils"], check=False)
    subprocess.run(["wget", "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"], check=True)
    subprocess.run(["tar", "-xf", "ffmpeg-release-amd64-static.tar.xz"], check=True)
    subprocess.run("cp ffmpeg-*-amd64-static/ffmpeg ./ffmpeg", shell=True, check=True)
    subprocess.run(["chmod", "+x", "./ffmpeg"], check=True)
    subprocess.run("rm -rf ffmpeg-release-amd64-static.tar.xz ffmpeg-*-amd64-static", shell=True, check=True)
    print("✅ ffmpeg установлен")
else:
    print("✅ ffmpeg уже есть")

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Logging Settings
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """The handler of the command /start"""
    await update.message.reply_text(
        "👋 Привет! Я умею превращать видео в кружки\n\n"
        "📹 Отправь мне видео или анимацию (до 20 МБ) и я сделаю из них видеосообщение (кружок)\n\n"
        "⚠️ Видео длиннее 1 минуты будет **автоматически обрезано** до 60 секунд\n\n"
        "👤 Автор: @TommiFox"
    )

async def videotonote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for video and animation"""
    
    # Проверяем, что прислали (видео или анимацию)
    if update.message.video:
        media = update.message.video
        is_animation = False
    elif update.message.animation:
        media = update.message.animation
        is_animation = True
    else:
        await update.message.reply_text("🎥 Отправь видео или анимацию")
        return

        # Проверка размера (лимит Telegram 20 МБ)
    if media.file_size > 20 * 1024 * 1024:
        await update.message.reply_text("❌ Файл слишком большой. Максимум 20 МБ")
        return

    logger.info("Received from user: %s", update.effective_user.username)
    status_message = await update.message.reply_text("⏰ Бот старается... 🍒")

    try:
        # Получаем файл
        file = await media.get_file()
        
        # Для анимации длительность = 0
        duration = media.duration if not is_animation else 0

        with tempfile.TemporaryDirectory() as tmpdirname:
            inputpath = os.path.join(tmpdirname, "input.mp4")
            outputpath = os.path.join(tmpdirname, "output.mp4")

            await file.download_to_drive(custom_path=inputpath)
            logger.info("File saved: %s", inputpath)

            # Команда ffmpeg (для анимации звука нет, но это не важно)
            if duration > 60:
                ffmpegcmd = ["./ffmpeg", "-y", "-i", inputpath, 
                           "-t", "60",
                           "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=240:240", 
                           "-c:a", "copy", outputpath]
                await status_message.edit_text("⏰ Видео длиннее минуты, обрезаю...")
            else:
                ffmpegcmd = ["./ffmpeg", "-y", "-i", inputpath, 
                           "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=240:240", 
                           "-c:a", "copy", outputpath]

            process = subprocess.run(ffmpegcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if process.returncode != 0:
                logger.error("FFMPEG ERROR: %s", process.stderr)
                await status_message.edit_text("❌ Ошибка при обработке")
                return

            logger.info("Conversion successful")
            await status_message.delete()
            await asyncio.sleep(2)
            await update.message.reply_text("Готово!")

            with open(outputpath, "rb") as videofile:
                await context.bot.sendVideoNote(
                    chat_id=update.effective_chat.id,
                    video_note=videofile,
                    duration=min(duration, 60) if duration > 0 else 0
                )
    except Exception as e:
        logger.exception("Error")
        await status_message.edit_text("❌ Ошибка")

def main() -> None:
    """The main function for launching a bot"""
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    # Обрабатываем и видео, и анимации
    app.add_handler(MessageHandler(filters.VIDEO | filters.ANIMATION, videotonote))

    logger.info("The bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
