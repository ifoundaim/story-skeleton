FROM python:3.11-bullseye

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY purpose_agents/ ./purpose_agents/
COPY codex/ ./codex/

# Ensure Python can import both backend (as top-level) and repo root modules
ENV PYTHONPATH=/app:/app/backend

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
