# Используем официальный образ Python
FROM python:3.12-slim

# Устанавливаем bash и зависимости для работы с Chrome и ChromeDriver
RUN apt-get update && apt-get install -y \
    bash \
    libxss1 \
    libappindicator3-1 \
    fonts-liberation \
    libu2f-udev \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libgbm1 \
    xdg-utils \
    wget \
    curl \
    unzip \
    chromium \
    chromium-driver \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*  # Очистка кэша apt для уменьшения размера образа

# Устанавливаем pip и создаем виртуальное окружение
RUN python -m venv /opt/venv

# Обновляем pip в виртуальном окружении
RUN /opt/venv/bin/pip install --upgrade pip

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt /app/requirements.txt
RUN /opt/venv/bin/pip install -r /app/requirements.txt

# Копируем все файлы приложения в контейнер
COPY . /app

# Устанавливаем переменные окружения для работы с виртуальным окружением
ENV PATH="/opt/venv/bin:$PATH"

# Указываем рабочую директорию
WORKDIR /app

# Запускаем приложение
CMD ["python", "main.py"]
