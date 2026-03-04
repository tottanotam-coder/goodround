import os
import tempfile
import subprocess
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ТВОЙ ЗАКРЫТЫЙ ТОКЕН
TOKEN = os.getenv("TOKEN") 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name
    await update.message.reply_text(f"Привет, {user_name}! 👋\nОтправь мне видео, и я сделаю кружок.")

async def videotonote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name
    status_message = await update.message.reply_text(f"Делаю кружок для {user_name}... ⏳")

    try:
        video = update.message.video
        file = await video.get_file()

        with tempfile.TemporaryDirectory() as tmpdirname:
            inputpath = os.path.join(tmpdirname, "in.mp4")
            outputpath = os.path.join(tmpdirname, "out.mp4")

            await file.download_to_drive(custom_path=inputpath)

            # Максимально простая команда без сложных кавычек
            # -t 60 обрезает до минуты
            ffmpegcmd = [
                "./ffmpeg", "-y", "-i", inputpath,
                "-t", "60",
                "-vf", "crop=min(iw\,ih):min(iw\,ih),scale=240:240",
                "-c:a", "aac", "-strict", "experimental", 
                outputpath
            ]

            process = subprocess.run(ffmpegcmd, capture_output=True, text=True)
            
            if process.returncode != 0:
                logger.error(f"FFMPEG ERROR: {process.stderr}")
                await update.message.reply_text("❌ Ошибка обработки. Попробуй другое видео.")
                return

            with open(outputpath, "rb") as videofile:
                dur = min(video.duration, 60) if video.duration else 60
                await context.bot.sendVideoNote(
                    chat_id=update.effective_chat.id,
                    video_note=videofile,
                    duration=dur
                )
            
            await status_message.delete()

    except Exception as e:
        logger.exception("Ошибка!")
        await update.message.reply_text(f"⚠️ Ошибка: {e}")

def main() -> None:
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, videotonote))
    app.run_polling()

if __name__ == "__main__":
    main()
