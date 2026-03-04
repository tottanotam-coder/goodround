import os
import subprocess
import logging
import tempfile
import asyncio
import stat
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Устанавливаем необходимые утилиты
subprocess.run(["apt-get", "update"], check=False)
subprocess.run(["apt-get", "install", "-y", "wget", "xz-utils"], check=False)

# Скачиваем ffmpeg, если его нет
if not os.path.exists("./ffmpeg"):
    subprocess.run(["wget", "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"], check=True)
    subprocess.run(["tar", "-xf", "ffmpeg-release-amd64-static.tar.xz"], check=True)
    subprocess.run("cp ffmpeg-*-amd64-static/ffmpeg ./ffmpeg", shell=True, check=True)
    subprocess.run(["chmod", "+x", "./ffmpeg"], check=True)
    subprocess.run("rm -rf ffmpeg-release-amd64-static.tar.xz ffmpeg-*-amd64-static", shell=True, check=True)
    print("✅ ffmpeg установлен")
else:
    print("✅ ffmpeg уже есть")

# Настройки логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получение токена (закрытый способ)
TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    await update.message.reply_text(
        "Привет 👋\n"
        "🎥 Просто отправь мне любое video или анимацию, "
        "и я превращу его в кружок\n\n"
        "📌 Команды:\n"
        "/start – запустить\n\n"
        "👥 Автор: @TommiFox"
    )

async def author(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /author"""
    await update.message.reply_text("👤 Автор бота: @TommiFox")

async def videotonote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка видео"""
    if not update.message.video:
        await update.message.reply_text("🎥 Отправь видео")
        return

    logger.info("Received a video from the user: %s", update.effective_user.username)
    status_message = await update.message.reply_text("⏰ Терпение...")
    status_message_2 = await update.message.reply_text("P.S. Если видео не пришло, подожди немного, бот может быть занят")

    try:
        video = update.message.video
        file = await video.get_file()

        with tempfile.TemporaryDirectory() as tmpdirname:
            inputpath = os.path.join(tmpdirname, "inputvideo.mp4")
            outputpath = os.path.join(tmpdirname, "videonote.mp4")

            # Скачивание видео
            await file.download_to_drive(custom_path=inputpath)
            logger.info("Video saved: %s", inputpath)

            # Твоя оригинальная команда ffmpeg
            ffmpegcmd = ["./ffmpeg", "-y", "-i", inputpath, "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=240:240", "-c:a", "copy", outputpath]

            process = subprocess.run(ffmpegcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if process.returncode != 0:
                logger.error("ffmpeg error: %s", process.stderr)
                await update.message.reply_text("Ошибка при обработке видео")
                return

            logger.info("Video successfully converted: %s", outputpath)
            
            # Удаление временных сообщений
            await context.bot.deleteMessage(chat_id=update.effective_chat.id, message_id=status_message_2.message_id)
            await context.bot.deleteMessage(chat_id=update.effective_chat.id, message_id=status_message.message_id)
            
            await asyncio.sleep(2)
            await update.message.reply_text("Видео готово!")

            # Отправка кружка
            with open(outputpath, "rb") as videofile:
                await context.bot.sendVideoNote(
                    chat_id=update.effective_chat.id,
                    video_note=videofile,
                    duration=video.duration
                )
    except Exception as e:
        logger.exception("Error in video processing")
        await update.message.reply_text(f"An error has occurred: {e}")

def main() -> None:
    """Запуск бота"""
    if not TOKEN:
        logger.error("BOT_TOKEN is not set!")
        return
        
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("author", author))
    app.add_handler(MessageHandler(filters.VIDEO, videotonote))

    logger.info("The bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
