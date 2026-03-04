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
        "👋 Привет! Я умею превращать видео в кружки.\n\n"
        "📹 Отправь мне видео, и я сделаю из него видеосообщение (кружок).\n\n"
        "⚠️ Видео длиннее 60 секунд будет **автоматически обрезано** до 60 секунд.\n\n"
        "👤 Автор: @TommiFox"
    )

async def videotonote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Video Handler: downloads, converts and send video message"""
    if not update.message.video:
        await update.message.reply_text("🎥 Отправь видео")
        return

    logger.info("Received a video from the user: %s", update.effective_user.username)
    status_message = await update.message.reply_text("⏰ Бот старается... 🍒")

    try:
        video = update.message.video
        file = await video.get_file()

        if video.duration > 60:
            await status_message.edit_text("⏰ Видео длиннее 60 секунд, обрезаю...")

        with tempfile.TemporaryDirectory() as tmpdirname:
            inputpath = os.path.join(tmpdirname, "inputvideo.mp4")
            outputpath = os.path.join(tmpdirname, "videonote.mp4")

            await file.download_to_drive(custom_path=inputpath)
            logger.info("Video saved: %s", inputpath)

            if video.duration > 60:
                ffmpegcmd = ["./ffmpeg", "-y", "-i", inputpath, 
                           "-t", "60",
                           "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=240:240", 
                           "-c:a", "copy", outputpath]
            else:
                ffmpegcmd = ["./ffmpeg", "-y", "-i", inputpath, 
                           "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=240:240", 
                           "-c:a", "copy", outputpath]

            process = subprocess.run(ffmpegcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if process.returncode != 0:
                logger.error("ffmpeg error: %s", process.stderr)
                await status_message.edit_text("❌ Ошибка при обработке")
                return

            logger.info("Video successfully converted: %s", outputpath)
            await status_message.delete()
            
            with open(outputpath, "rb") as videofile:
                await context.bot.sendVideoNote(
                    chat_id=update.effective_chat.id,
                    video_note=videofile,
                    duration=min(video.duration, 60)
                )
    except Exception as e:
        logger.exception("Error in video processing")
        await status_message.edit_text("❌ Ошибка")

def main() -> None:
    """The main function for launching a bot"""
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, videotonote))
    app.run_polling()

if __name__ == "__main__":
    main()
