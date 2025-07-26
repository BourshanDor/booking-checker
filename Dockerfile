FROM python:3.13.0-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    bash curl unzip fonts-liberation libnss3 libx11-xcb1 libxcomposite1 libxcursor1 libxdamage1 libxrandr2 libasound2 libatk1.0-0 libatk-bridge2.0-0 libgtk-3-0 libdrm2 xdg-utils \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -o chrome.deb && \
    apt-get update && apt-get install -y ./chrome.deb && \
    rm chrome.deb

ENV CHROMEDRIVER_VERSION=114.0.5735.90

RUN curl -sSL "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" -o /tmp/chromedriver.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    rm /tmp/chromedriver.zip && \
    chmod +x /usr/local/bin/chromedriver

COPY BOOKING.env .
COPY requirements.txt .
COPY booking.py .
COPY email_template.html .
COPY email_utils.py .
COPY mylog.py .

RUN pip install --no-cache-dir -r requirements.txt

ENV DISPLAY=:99

ENTRYPOINT ["python", "booking.py"]
CMD []
