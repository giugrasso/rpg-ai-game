import requests
from sqlmodel import select

from app.core.config import settings
from app.core.db import async_session
from app.models import (
    AIModel,
    AIResponseValidator,
    CharacterRoleSchema,
    GameMode,
    Scenario,
    ScenarioRole,
    ScenarioSchema,
)

from .logging_config import logger

SYSTEM_PROMPT = f"""
⚠️ RÈGLE ABSOLUE : TU DOIS **TOUJOURS** répondre avec un JSON valide **ET RIEN D'AUTRE**.
Ne commence **JAMAIS** ta réponse par du texte comme "Voici la réponse :", "Le joueur voit...", ou toute autre narration en dehors du JSON.
Si tu ne respectes pas cette règle, le jeu ne fonctionnera pas.

---
### Rôle et Responsabilités
Tu es un **maître du jeu (MJ) expert** pour un jeu de rôle narratif. Ton objectif est de :
1. **Créer une immersion totale** en décrivant les scènes, personnages et événements avec des détails **sensoriels** (sons, odeurs, textures, ambiance).
2. **Adapter dynamiquement l'histoire** au scénario, aux actions des joueurs et à leurs statistiques.
3. **Guider subtilement les joueurs vers l'objectif principal** du scénario **sans le révéler explicitement**.
    - Utilise des indices environnementaux (ex : "Un bruit vient de la direction de ton objectif...").
    - Évite les digressions qui n'avancent pas l'histoire.
4. **Respecter les règles du monde** (ex : pas de magie dans un scénario scientifique, pas de technologie futuriste dans un monde médiéval).
5. **Gérer les actions risquées** (combats, pièges, négociations) avec des mécaniques de succès/échec basées sur les statistiques des joueurs.

---
### Structure de Réponse Obligatoire
Ton JSON doit **toujours** suivre ce schéma :
{AIResponseValidator.model_json_schema()}

---
### Règles pour les Options
- **Nombre** : Propose **toujours 2 ou 3 options** (sauf cas exceptionnel justifié par le scénario).
- **Variété** :
    - Une option doit avoir un `success_rate` **élevé** (> 0.6) et un risque faible.
    - Une option doit avoir un `success_rate` **faible** (< 0.4) mais un gain potentiel important.
    - Les valeurs de `health_point_change`/`mana_point_change` doivent être **cohérentes** avec le risque (ex : une attaque puissante a un `health_point_change` négatif élevé).
- **Lien avec les stats** :
    - `related_stat` doit correspondre à une statistique du joueur (ex : "force" pour un combat, "intelligence" pour résoudre une énigme).
    - Une option ne peut pas dépendre d'une stat que le joueur n'a pas.
- **Cohérence** :
    - Les effets (`health_point_change`, `mana_point_change`) doivent être **réalistes** dans le contexte (ex : une potion de soin ne restaure pas 100% des PV si le scénario est difficile).
    - Si une action est impossible (ex : "voler sans ailes"), fixe `success_rate=0.0` et propose des alternatives.

---

### Règles spéciales pour les échecs
1. EN CAS D'ÉCHEC D'UNE ACTION :
   - Décris uniquement la conséquence de l'échec dans la narration.
   - NE METS PAS de schéma JSON ou d'explications sur le format.
   - Respecte STRICTEMENT le format requis :
{AIResponseValidator.model_json_schema()}
   - Les options doivent refléter les conséquences de l'échec (ex: 'Se soigner', 'Fuir', 'Tenter une autre approche')."

---
### Gestion des Cas Spéciaux
- **Actions absurdes/hors contexte** :
    - Narration : Décris l'échec de manière immersive (ex : "Ton personnage, sous l'emprise d'une illusion, tente de parler aux murs...").
    - Options : Propose des moyens de **revenir à une situation normale** (ex : "Secouer la tête pour te ressaisir").
    - `success_rate` : 0.0 pour l'action absurde, > 0.5 pour les options de rattrapage.
- **Objectif du scénario** :
    - Toutes les options doivent **indirectement rapprocher** les joueurs de l'objectif (même après un échec).
    - Utilise des PNJ, des événements ou des indices pour **recadrer l'histoire** si les joueurs s'éloignent trop.
- **Combats/Conflits** :
    - Décris les ennemis, leur état (blessés, enragés, affaiblis) et les conséquences des actions.
    - Les dégâts (`health_point_change`) doivent être **proportionnels** à la menace (ex : un boss inflige plus de dégâts qu'un ennemi basique).

---
### Consignes Supplémentaires
- **Langue** : Réponds **uniquement en français**, avec un style **vivant et captivant**.
- **Équilibre** :
    - Un joueur ne doit **jamais** être bloqué sans solution (même après un échec).
    - Les récompenses/risques doivent être **équilibrés** (ex : un trésor bien gardé a un haut risque mais une grande récompense).
- **Dynamicité** :
    - Fais évoluer l'environnement en fonction des actions (ex : un dinosaure blessé peut fuir ou devenir plus agressif).
    - Les PNJ ont des personnalités et réagissent de manière cohérente (ex : un scientifique aura peur des dinosaures).
- **Immersion** :
    - Utilise des **métaphores** et des **comparaisons** pour rendre les descriptions plus vivantes (ex : "Le rugissement du raptor ressemble à un moteur qui tousse").
    - Varier les sens utilisés (ouïe, odorat, toucher) pour enrichir l'expérience.

---
### Interdictions Formelles
- ❌ **Ne révèle JAMAIS** l'objectif du scénario ou des éléments clés à l'avance.
- ❌ **Ne brise JAMAIS l'immersion** (même pour une action absurde, trouve une explication narrative).
- ❌ **Ne dépasse JAMAIS** les limites des multiplicateurs :
    - `health_point_change` et `mana_point_change` doivent toujours être entre **-1.0 et 1.0**.
    - `success_rate` doit toujours être entre **0.0 et 1.0**.
- ❌ **N'invente pas** de nouvelles statistiques ou compétences pour les joueurs.
"""


async def init_game_master():
    async with async_session() as session:  # type: ignore
        result = await session.execute(
            select(AIModel).where(AIModel.name == "game_master")
        )
        model = result.scalars().first()

        # Création si absent
        if not model:
            model = AIModel(
                name="game_master",
                base=settings.OLLAMA_MODEL,
                system_prompt=SYSTEM_PROMPT,
                installed=False,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)

        # Vérification si déjà présent dans Ollama
        model_exists = False
        try:
            resp = requests.get(f"{settings.OLLAMA_SERVER}/api/tags")
            resp.raise_for_status()
            models = resp.json()
            for m in models["models"]:
                if m.get("name") == "game_master:latest":
                    model_exists = True
                    logger.info("Custom Ollama model already exists.")
                    break
        except Exception as exc:
            logger.error(f"Failed to get Ollama model: {exc}")

        # Si pas présent dans Ollama → on le crée
        if not model_exists:
            try:
                resp = requests.post(
                    f"{settings.OLLAMA_SERVER}/api/create",
                    json={
                        "model": "game_master",
                        "from": settings.OLLAMA_MODEL,
                        "system": SYSTEM_PROMPT,
                    },
                )
                resp.raise_for_status()
                model.installed = True

                # run model
                requests.post(
                    f"{settings.OLLAMA_SERVER}/api/generate",
                    json={"model": "game_master", "prompt": "Bonjour"},
                )
                resp.raise_for_status()

                # Check if model is running
                ollama_ps = requests.get(f"{settings.OLLAMA_SERVER}/api/ps")
                ollama_ps.raise_for_status()

                logger.info(f"Ollama ps: {ollama_ps.json()}")

                # check if "game_master" is present in ollama_ps.json().get("models", [])
                if "game_master" not in [
                    m.get("name") for m in ollama_ps.json().get("models", [])
                ]:
                    raise Exception("Custom Ollama model is not running.")

                logger.info("Custom Ollama model created and running.")

                # Sauvegarde dans la BDD
                session.add(model)
                await session.commit()
                await session.refresh(model)
                logger.info("Custom Ollama model created and saved in DB.")
            except Exception as exc:
                logger.error(f"Failed to create Ollama model: {exc}")


async def init_first_scenario():
    async with async_session() as session:  # type: ignore
        result = await session.execute(
            select(Scenario).where(Scenario.name == "L'ile des dinosaures")
        )

        existing = result.scalars().first()
        if existing:
            logger.info("Initial scenario already exists.")
            return

        scenario_data = ScenarioSchema(
            name="L'ile des dinosaures",
            description="Une ile mystérieuse peuplée de dinosaures issus d'une expérience scientifique.",
            objectives="Survivre, trouver le scientifique George, et atteindre l'héliport.",
            mode=GameMode.PVE,
            max_players=4,
            roles=[
                CharacterRoleSchema(
                    name="Chasseur",
                    stats={
                        "force": 18,
                        "intelligence": 12,
                        "charisme": 14,
                        "courage": 16,
                        "chance": 10,
                    },
                    description="Utilise des armes à feu et des pièges",
                ),
                CharacterRoleSchema(
                    name="Scientifique",
                    stats={
                        "force": 10,
                        "intelligence": 18,
                        "charisme": 14,
                        "courage": 12,
                        "chance": 12,
                    },
                    description="Connaissances en biologie et chimie",
                ),
                CharacterRoleSchema(
                    name="Médecin",
                    stats={
                        "force": 12,
                        "intelligence": 16,
                        "charisme": 14,
                        "courage": 14,
                        "chance": 10,
                    },
                    description="Soigne les blessures et maladies",
                ),
                CharacterRoleSchema(
                    name="Explorateur",
                    stats={
                        "force": 14,
                        "intelligence": 14,
                        "charisme": 12,
                        "courage": 16,
                        "chance": 12,
                    },
                    description="Expert en survie et navigation",
                ),
            ],
            context="""
**Contexte connu des joueurs:**
Vous venez de débarquer de nuit dans un petit port de pêcheur d'une île tropicale isolée de 20 km², après avoir répondu à un appel de détresse lancé par une station de recherche scientifique.
Le message était incomplet, mais mentionnait une "urgence biologique" et une évacuation par héliport au centre de l'île.
Votre mission initiale : localiser le Dr. George, le responsable de la station, et vous rendre à l'héliport pour une extraction d'urgence.

**Ce que les joueurs ignorent (à découvrir via l'exploration) :**
- L'île abritait un **projet de recherche secret** sur la **résurrection d'espèces éteintes**, financé par une organisation inconnue.
- Une **panne de courant générale** a plongé les installations dans le chaos il y a 48 heures. Depuis, plus aucun contact avec l'extérieur.
- Les systèmes de sécurité sont hors ligne, et les **portes des enclos de quarantaine** se sont ouvertes...
- Des **bruits étranges** (grondements, craquements de végétation) résonnent dans la jungle, surtout la nuit.
- Les rares notes retrouvées parlent de "sujets d'expérience non contrôlés" et de "protocole Ichthyosaure" (un code interne).

**Éléments clés à découvrir :**
- **George** : Le scientifique en chef. D'après les transmissions interceptées, il se dirigeait vers le **bunker central** (près de l'héliport) avec des échantillons "critiques".
  - *Indices pour le trouver* :
    - Une carte partielle de l'île (trouvable dans le camp de base) montre un chemin vers le centre.
    - Des **traces de pas humains** récentes mènent vers les collines centrales.
    - Des **messages audio** dispersés (via talkies-walkies) mentionnent un "protocole d'urgence activé".
- **L'héliport** : Situé au cœur de l'île, c'est le seul point d'évacuation. Son générateur de secours clignote encore, visible de loin la nuit.
  - *Obstacles* :
    - La jungle est dense, avec des **zones marquées "DANGER - ACCÈS RESTREINT"** (anciens enclos).
    - Des **câbles électriques arrachés** et des **équipements endommagés** jonchent les sentiers.
- **Ressources** :
  - Nourriture et eau sont limitées. Les joueurs devront **piller les caches de la station** ou chasser (avec des risques).
  - Des **armoires médicales** (dans les avant-postes) contiennent des soins, mais certaines sont vides... ou ouvertes de l'intérieur.
- **Règles de survie** :
  - **Jets de dés** : Toute action risquée (escalade, combat, fouille) dépend des stats des joueurs.
  - **Gestion des ressources** : Un inventaire limité force à faire des choix (ex : garder une lampe torche ou des munitions).
  - **Rencontres aléatoires** : Des **bruits inexpliqués** (feuillages qui bougent, souffles chauds) peuvent survenir, surtout près des zones restreintes.

**Ambiance à instaurer :**
- **Jour** : L'île semble déserte, mais des détails trahissent une présence (ex : branches cassées à 3 mètres de haut, odeurs musquées).
- **Nuit** : Les bruits s'intensifient. Une **lueur verdâtre** émane parfois des zones restreintes...
- **Indices environnementaux** :
  - Des **cages vides** (portes arrachées) près des laboratoires.
  - Des **cadavres d'animaux** (moutons, singes) partiellement dévorés, avec des morsures anormalement larges.
  - Des **écrans de surveillance** (si réactivés) montrent des silhouettes se déplaçant rapidement entre les arbres.

**Objectif caché (pour le MJ) :**
- Les "sujets d'expérience" sont des **dinosaures génétiquement modifiés**, conçus pour être dociles... jusqu'à la panne.
- George sait comment les neutraliser (via un **émetteur à ultrasons** dans son labo), mais il est blessé et traqué.
- L'héliport a un **système de verrouillage** nécessitant un code (que George possède).

**Ton en tant que MJ :**
- Décris l'île comme **belle mais inquiétante** : plages de sable blanc contrastant avec des bâtiments vandalisés, odeurs de jungle mélangées à un **arôme métallique** (sang ? produits chimiques ?).
- Utilise des **métaphores** pour évoquer les dinosaures sans les nommer :
  - *"Un grognement sourd fait vibrer le sol, comme un moteur diesel au ralenti."*
  - *"Une ombre massive passe entre les arbres, trop grande pour un humain..."*
- Révèle la vérité **progressivement** :
  1. D'abord des **indices indirects** (empreintes, bruits).
  2. Puis des **aperçus** (queue qui disparaît dans les buissons).
  3. Enfin, une **rencontre claire** (ex : un raptor bloquant le chemin de l'héliport).
""",
        )

        # Crée le scénario
        db_scenario = Scenario(
            name=scenario_data.name,
            description=scenario_data.description,
            objectives=scenario_data.objectives,
            mode=scenario_data.mode,
            max_players=scenario_data.max_players,
            context=scenario_data.context,
            roles=[
                ScenarioRole(
                    scenario_id=None,  # sera rempli par la relation
                    name=r.name,
                    stats=r.stats,
                    description=r.description,
                )
                for r in scenario_data.roles
            ],
        )

        session.add(db_scenario)
        await session.commit()
        await session.refresh(db_scenario)

        logger.info("Initial scenario with roles created.")
