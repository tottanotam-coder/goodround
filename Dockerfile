FROM python:3.11-slim

# Устанавливаем FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

# Создаем рабочую папку
WORKDIR /app

# Копируем файлы с зависимостями
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код
COPY . .

# Запускаем бота
CMD ["python", "main.py"]
