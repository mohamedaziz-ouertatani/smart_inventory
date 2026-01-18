FROM python:3.11-slim

WORKDIR /workspace

RUN pip install apscheduler

COPY scheduler.py .

CMD ["python", "scheduler.py"]