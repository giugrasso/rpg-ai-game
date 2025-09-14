# 🧙‍♂️ RPG-AI-Game

Un jeu de rôle narratif inspiré de Donjons & Dragons, propulsé par l'IA locale [Ollama](https://ollama.ai/).  
Le jeu propose des parties courtes (~1h), en **mode solo, PvE coopératif ou PvP compétitif**, avec des classes aux caractéristiques uniques.  
L’IA agit comme maître du jeu, se souvient des actions précédentes et adapte l’histoire en fonction de vos choix.

---

## 🚀 Fonctionnalités (MVP)
- 🎲 Création de personnage avec répartition de 20 points sur les attributs.
- ⚔️ Mode **PvE** (joueurs coopèrent contre des ennemis contrôlés par l’IA).
- 🛡️ Mode **PvP** (joueurs s’affrontent dans des factions différentes).
- 🧠 IA (via Ollama, modèle `llama3.2:latest`) pour la narration et la résolution des actions.
- 🔄 Sauvegarde et reprise de parties (PostgreSQL).
- ⚡ Gestion des états temps réel et des tours (Redis).
- 🌐 Interface web (React + Bootstrap).
- 🐍 Backend (FastAPI + Poetry).

---

## 🐳 Démarrage rapide avec Docker Compose

### 1. Cloner le projet
```bash
git clone https://github.com/giugrasso/rpg-ai-game.git
cd rpg-ai-game
```

### 2. Lancer la stack

```bash
docker-compose up --build
```

### 3. Accéder aux services

* Frontend : [http://localhost:3000](http://localhost:3000)
* Backend (FastAPI docs) : [http://localhost:8000/docs](http://localhost:8000/docs)
* Ollama API : [http://localhost:11434](http://localhost:11434)

---

## 📂 Structure du projet

```
rpg-ai-game/
│
├── backend/              # FastAPI + Poetry
│   ├── pyproject.toml
│   └── app/
│       ├── main.py
│       ├── models.py
│       └── routes/
│
├── frontend/             # React + Bootstrap
│   ├── package.json
│   └── src/
│
├── docker-compose.yml
└── README.md
```

---

## 🤝 Contribuer

Les contributions sont bienvenues !
Pour contribuer :

1. Forkez le projet.
2. Créez une branche.
3. Commitez vos changements.
4. Poussez la branche.
5. Ouvrez une Pull Request 🚀.

Consultez le fichier [CONTRIBUTING](CONTRIBUTING.md) pour plus de détails.

---

## 🧑‍💻 Roadmap

* [ ] MVP jouable en mode solo (FastAPI + Ollama).
* [ ] Gestion multijoueur (WebSocket).
* [ ] Scénarios PvE et PvP.
* [ ] Sauvegarde/chargement de parties.
* [ ] Génération d’images pour immersion (V2).

---

## 📜 Licence

Ce projet est sous licence **Apache 2.0**.
Voir le fichier [LICENSE](LICENSE) pour plus d’informations.
