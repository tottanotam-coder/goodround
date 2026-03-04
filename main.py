import os
import tempfile
import subprocess
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ТВОЙ ЗАКРЫТЫЙ ТОКЕН (как и было в твоем оригинальном коде)
TOKEN = os.getenv("TOKEN") 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Берем имя пользователя, чтобы бот его запомнил
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Привет, {user_name}! 👋\n\n"
        "🎥 Просто отправь мне видео, и я сделаю из него кружок.\n"
        "⏱ Видео длиннее 60 секунд я обрежу автоматически!"
    )

async def videotonote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Обращаемся по имени при начале обработки
    user_name = update.effective_user.first_name
    status_message = await update.message.reply_text(f"Секунду, {user_name}, я превращаю видео в кружок... ⏳")

    try:
        video = update.message.video
        file = await video.get_file()

        with tempfile.TemporaryDirectory() as tmpdirname:
            inputpath = os.path.join(tmpdirname, "inputvideo.mp4")
            outputpath = os.path.join(tmpdirname, "videonote.mp4")

            await file.download_to_drive(custom_path=inputpath)

            # Команда ffmpeg: обрезка до 60 секунд и создание квадрата для кружка
            ffmpegcmd = [
                "./ffmpeg", "-y", "-i", inputpath,
                "-t", "60",
                "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=240:240",
                "-c:a", "aac", "-strict", "experimental", outputpath
            ]

            process = subprocess.run(ffmpegcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if process.returncode != 0:
                logger.error(f"Ошибка ffmpeg: {process.stderr}")
                await update.message.reply_text("❌ Ошибка при конвертации.")
                return

            with open(outputpath, "rb") as videofile:
                # Определяем длительность (не более 60 секунд)
                dur = min(video.duration, 60) if video.duration else 60
                await context.bot.sendVideoNote(
                    chat_id=update.effective_chat.id,
                    video_note=videofile,
                    duration=dur
                )
            
            await status_message.delete()

    except Exception as e:
        logger.exception("Ошибка!")
        error_text = str(e)
        if "File is too big" in error_text:
            msg = "❌ Видео слишком тяжелое для загрузки (лимит 20Мб)."
        else:
            msg = f"⚠️ Произошла ошибка: {error_text}"
        await update.message.reply_text(msg)

def main() -> None:
    if not TOKEN:
        logger.error("Токен не найден в переменных окружения!")
        return
        
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, videotonote))
    
    logger.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
