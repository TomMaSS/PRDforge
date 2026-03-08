FROM python:3.11-slim
WORKDIR /app
COPY ui/requirements.txt /app/ui/
RUN pip install --no-cache-dir -r /app/ui/requirements.txt
COPY shared/ /app/shared/
COPY ui/app.py /app/ui/
COPY ui/static/ /app/ui/static/
WORKDIR /app/ui
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8088"]
