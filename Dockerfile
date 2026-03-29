FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY canuckduck_mcp.py .

EXPOSE 8765

CMD ["python", "canuckduck_mcp.py"]
