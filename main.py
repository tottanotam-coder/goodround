import os
import subprocess
import logging
import tempfile
import asyncio
import stat

# Устанавливаем wget и xz-utils
subprocess.run(["apt-get", "update"], check=False)
subprocess.run(["apt-get", "install", "-y", "wget", "xz-utils"], check=False)

# Скачиваем ffmpeg, если его нет
if not os.path.exists("./ffmpeg"):
    import subprocess
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

import os
TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """The handler of the command /start"""
    await update.message.reply_text(
        "Привет 👋\n"
        "🎥 Просто отправь мне любое видео или анимацию, "
        "и я превращу его в кружок\n\n"
        "✨ **Важно:** По правилам Telegram кружок может длиться только **60 секунд**. "
        "Если ты пришлешь более длинное видео, я автоматически обрежу его до первой минуты!"
        "📌 Команды:\n"
        "/start – запустить\n\n"
        "👥 Автор: @TommiFox"
    )

async def author(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /author"""
    await update.message.reply_text("👤 Автор бота: @TommiFox")

async def videotonote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Video Handler: downloads, converts and send video message"""
    # Checking, that a video exists in the message
    if not update.message.video:
        await update.message.reply_text("🎥 Отправь видео")
        return

    logger.info("Received a video from the user: %s", update.effective_user.username)
    status_message = await update.message.reply_text("⏰ Терпение...")
    status_message_2 = await update.message.reply_text("P.S. Бот всё еще обрбатывает видео ✨")

    try:
        video = update.message.video
        file = await video.get_file()

        # Creating a temporary directory for storing files
        with tempfile.TemporaryDirectory() as tmpdirname:
            inputpath = os.path.join(tmpdirname, "inputvideo.mp4")
            outputpath = os.path.join(tmpdirname, "videonote.mp4")

            # Downloading original video
            await file.download_to_drive(custom_path=inputpath)
            logger.info("Video saved: %s", inputpath)

            # Forming the ffmpeg command:
            # 1. Crop the video to a square with a size equal to the minimum side. (min(iw,ih)).
            # 2. Scaling the result to 240x240 pixels (required size for video note).
            # 3. The -y option allows you to overwrite the output file without prompting..
            ffmpegcmd = "./ffmpeg", "-y", "-t", "60", "-i", inputpath, "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=240:240", "-c:a", "aac", "-strict", "experimental", outputpath
            

            process = subprocess.run(ffmpegcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if process.returncode != 0:
                logger.error("ffmpeg error: %s", process.stderr)
                await update.message.reply_text("Ошибка при обработке видео")
                return

            logger.info("Видео успешно конвертировано: %s", outputpath)
            # Deleting the temporary message
            await context.bot.deleteMessage(chat_id=update.effective_chat.id, message_id=status_message_2.message_id)
            await context.bot.deleteMessage(chat_id=update.effective_chat.id, message_id=status_message.message_id)
            await asyncio.sleep(2)
            await update.message.reply_text("Видео готово!")

            # We are sending the converted video as a video message. (video note)
            with open(outputpath, "rb") as videofile:
                await context.bot.sendVideoNote(
                    chat_id=update.effective_chat.id,
                    video_note=videofile,
                    duration=min(video.duration, 60) if video.duration else 60  # We specify the duration of the original video
                )
    except Exception as e:
        logger.exception("Ошибка при обработке видео")
        
        # Переводим текст ошибки для пользователя
        error_text = str(e)
        
        if "File is too big" in error_text:
            msg = "❌ Ошибка: Файл слишком большой. Попробуй отправить видео поменьше (до 20-50 МБ)."
        elif "Wrong file identifier" in error_text:
            msg = "❌ Ошибка: Не удалось скачать файл. Попробуй еще раз."
        else:
            # Если ошибка неизвестна, пишем её как есть, но по-русски
            msg = f"⚠️ Произошла ошибка: {error_text}"
            
        await update.message.reply_text(msg)

def main() -> None:
    """The main function for launching a bot"""
    app = Application.builder().token(TOKEN).build()

    # Registering command and message handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("author", author))
    app.add_handler(MessageHandler(filters.VIDEO, videotonote))

    logger.info("The bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
