FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bigdance ./bigdance
COPY app ./app
COPY web ./web
COPY data/example_picks.json ./data/example_picks.json
COPY data/team_ratings.csv ./data/team_ratings.csv
COPY data/team_aliases.yaml ./data/team_aliases.yaml

RUN mkdir -p data/runs

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
