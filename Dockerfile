FROM python:3-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./sftp-cleanup.py ./sftp-cleanup.py

ENTRYPOINT ["/usr/local/bin/python", "sftp-cleanup.py", "--scheduler"]
