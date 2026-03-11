FROM python:3.11-slim@sha256:d6e4d224f70f9e0172a06a3a2eba2f768eb146811a349278b38fff3a36463b47
WORKDIR /app
RUN apt-get update \
	&& apt-get install -y --no-install-recommends nodejs npm \
	&& npm install -g @anthropic-ai/claude-code \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/*
COPY ui/requirements.txt /app/ui/
RUN pip install --no-cache-dir -r /app/ui/requirements.txt
COPY shared/ /app/shared/
COPY mcp_server/ /app/mcp_server/
COPY ui/app.py /app/ui/
COPY ui/static/ /app/ui/static/
WORKDIR /app/ui
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8088"]
