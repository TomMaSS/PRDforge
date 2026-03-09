FROM python:3.11-slim@sha256:d6e4d224f70f9e0172a06a3a2eba2f768eb146811a349278b38fff3a36463b47
WORKDIR /app
COPY ui/requirements.txt /app/ui/
RUN pip install --no-cache-dir -r /app/ui/requirements.txt
COPY shared/ /app/shared/
COPY ui/app.py /app/ui/
COPY ui/static/ /app/ui/static/
WORKDIR /app/ui
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8088"]
