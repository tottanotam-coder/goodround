import os
import subprocess
import logging
import tempfile
import asyncio
import glob

def install_ffmpeg():
    if not os.path.exists("ffmpeg"):
        print("Downloading ffmpeg...")

        os.system("wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz")
        os.system("tar -xf ffmpeg-release-amd64-static.tar.xz")

        folder = glob.glob("ffmpeg-*-amd64-static")[0]

        os.system(f"cp {folder}/ffmpeg ./ffmpeg")
        os.system("chmod +x ffmpeg")

        print("ffmpeg installed")

install_ffmpeg()

os.environ["FFMPEG_BINARY"] = "./ffmpeg"

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Logging Settings
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# PUT YOUR TOKEN HERE
TOKEN = os.getenv("API_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /start command"""
    await update.message.reply_text("Загрузи своё видео 🎥")


async def videotonote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Video handler: downloads, converts and sends video note"""

    if not update.message.video:
        await update.message.reply_text("Отправь видео")
        return

    logger.info("Received video from user: %s", update.effective_user.username)

    status_message = await update.message.reply_text("Терпение...")
    status_message_2 = await update.message.reply_text(
        "P.S. Если видео не пришло, подожди немного, бот может быть занят"
    )

    try:
        video = update.message.video
        file = await video.get_file()

        with tempfile.TemporaryDirectory() as tmpdirname:

            inputpath = os.path.join(tmpdirname, "inputvideo.mp4")
            outputpath = os.path.join(tmpdirname, "videonote.mp4")

            await file.download_to_drive(custom_path=inputpath)

            logger.info("Video saved: %s", inputpath)

            ffmpegcmd = (
                "./ffmpeg",
                "-y",
                "-i", inputpath,
                "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=240:240",
                "-c:v", "libx264",
                "-preset", "fast",
                "-c:a", "copy",
                outputpath
            )

if not os.path.exists("./ffmpeg"):
    raise Exception("ffmpeg not found in project folder")
            
            process = subprocess.run(
                ffmpegcmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if process.returncode != 0:
                logger.error("ffmpeg error: %s", process.stderr)
                await update.message.reply_text("Ошибка при обработке видео")
                return

            logger.info("Video successfully converted: %s", outputpath)

            await context.bot.deleteMessage(
                chat_id=update.effective_chat.id,
                message_id=status_message.message_id
            )

            await context.bot.deleteMessage(
                chat_id=update.effective_chat.id,
                message_id=status_message_2.message_id
            )

            await asyncio.sleep(2)

            await update.message.reply_text("Видео готово!")

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
    """Main function to run the bot"""

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, videotonote))

    logger.info("Bot started...")

    app.run_polling()


if __name__ == "__main__":
    main()
