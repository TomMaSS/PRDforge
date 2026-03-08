FROM python:3.11-slim
WORKDIR /app
COPY mcp_server/requirements.txt /app/mcp_server/
RUN pip install --no-cache-dir -r /app/mcp_server/requirements.txt
COPY shared/ /app/shared/
COPY mcp_server/server.py /app/mcp_server/
WORKDIR /app/mcp_server
CMD ["python", "server.py"]
