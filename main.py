import os
import subprocess
import logging
import tempfile
import asyncio

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Скачиваем ffmpeg, если его нет
if not os.path.exists("./ffmpeg"):
    print("📥 Скачиваю ffmpeg...")
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

# Токен бота
TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет 👋\n"
        "🎥 Просто отправь мне видео, и я сделаю из него кружок\n\n"
        "👤 Автор: @TommiFox"
    )

async def author(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("👤 Автор бота: @TommiFox")

async def videotonote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message.video:
        await update.message.reply_text("🎥 Отправь видео")
        return

    msg = await update.message.reply_text("⏳ Обрабатываю видео...")

    try:
        video = update.message.video
        file = await video.get_file()

        with tempfile.TemporaryDirectory() as tmpdirname:
            inputpath = os.path.join(tmpdirname, "input.mp4")
            outputpath = os.path.join(tmpdirname, "output.mp4")

            await file.download_to_drive(custom_path=inputpath)

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
                    duration=video.duration
                )
    except Exception as e:
        logger.exception("Error")
        await msg.edit_text("❌ Что-то пошло не так")

def main():
    if not TOKEN:
        logger.error("Нет токена!")
        return
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("author", author))
    app.add_handler(MessageHandler(filters.VIDEO, videotonote))
    app.run_polling()

if __name__ == "__main__":
    main()
