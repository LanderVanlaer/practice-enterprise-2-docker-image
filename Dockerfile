FROM python:3.10.0

WORKDIR /app

RUN apt update && apt upgrade -y
RUN apt install -y libmariadb-dev cron

RUN pip install --upgrade pip

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY crontab /app/
RUN chmod 0644 /app/
RUN /usr/bin/crontab -u root /app/crontab


COPY model.h5 min-max-scaler.joblib .env /app/
COPY app.py /app/

CMD ["cron", "-f"]
