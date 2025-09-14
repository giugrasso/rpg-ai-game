
# Contribuer à DnD-AI

Merci de votre intérêt ! 🚀

## Pré-requis
- Python 3.13
- Poetry 1.8.5
- Node.js 20+
- Docker et Docker Compose

## Installation

1. Forkez le repo et clonez votre fork :
   ```bash
   git clone https://github.com/votre-username/dnd-ai.git
   cd dnd-ai
    ````

2. Copiez le fichier `.env.example` :

   ```bash
   cp .env.example .env
   ```

3. Lancez le projet en local :

   ```bash
   docker compose up --build
   ```

## Règles de contribution

* Les PR doivent cibler la branche `main`.
* Ajoutez des tests si vous modifiez la logique métier.
* Respectez le style de code (`black` + `isort` pour Python, `eslint` pour React).
* Documentez vos changements dans le `README.md`.

## Communication

* Les discussions se font via GitHub Issues et Pull Requests.
