# Stage 1: build the React frontend
FROM node:20-slim AS ui
WORKDIR /ui
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Stage 2: FastAPI serves API + built frontend as one service
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 DB_PATH=/tmp/coach.db
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY samples/ ./samples/
COPY --from=ui /ui/dist ./frontend/dist
EXPOSE 8000
CMD ["sh", "-c", "cd backend && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
