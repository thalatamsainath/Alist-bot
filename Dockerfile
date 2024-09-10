FROM python:3.10-slim

WORKDIR /usr/src/app
RUN apt update && apt install -y bash curl gcc 

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "bot.py"]
