FROM python:3.11-slim@sha256:d6e4d224f70f9e0172a06a3a2eba2f768eb146811a349278b38fff3a36463b47
WORKDIR /app
COPY mcp_server/requirements.txt /app/mcp_server/
RUN pip install --no-cache-dir -r /app/mcp_server/requirements.txt
COPY shared/ /app/shared/
COPY mcp_server/server.py /app/mcp_server/
WORKDIR /app/mcp_server
CMD ["python", "server.py"]
