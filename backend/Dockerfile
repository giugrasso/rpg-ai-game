# Utilise Python 3.13 slim
FROM python:3.13-slim

# Variables d'environnement pour Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Installer Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Copier fichiers de dépendances et installer
WORKDIR /app
COPY pyproject.toml poetry.lock* /app/
RUN poetry install --no-root --only main

# Copier le code de l’application
COPY . /app

# Exposer le port FastAPI
EXPOSE 8000

# Commande par défaut
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
