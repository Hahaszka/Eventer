FROM python:3.11-slim

WORKDIR /code

ENV HF_HOME=/code/hf_cache

# Zależności systemowe
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY requirements.txt .

RUN pip install --progress-bar on -v torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --progress-bar on -v -r requirements.txt

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY ./app ./app
COPY .env .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]