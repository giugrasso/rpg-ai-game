from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from ollama import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app import crud, models
from app.core.config import settings
from app.core.db import get_session

router = APIRouter()


@router.get("/games", response_model=list[models.Game])
async def get_games(db: AsyncSession = Depends(get_session)):
    return await crud.get_games(db)


@router.post("/game", response_model=models.Game, status_code=201)
async def create_game(game: models.GameSchema, db: AsyncSession = Depends(get_session)):
    game_obj = models.Game(
        scenario_id=game.scenario_id,
        turn=game.turn,
        active=game.active,
        current_player_id=None,
    )
    await crud.create_game(db, game_obj)
    return game_obj


@router.get("/game/{game_id}", response_model=models.Game)
async def get_game(game_id: UUID, db: AsyncSession = Depends(get_session)):
    game = await crud.get_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.delete("/game/{game_id}", status_code=204)
async def delete_game(game_id: UUID, db: AsyncSession = Depends(get_session)):
    game = await crud.get_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    await crud.delete_game(db, game)
    return None


@router.post("/game/{game_id}/roll_initiative", response_model=list[models.Player])
async def roll_initiative(game_id: UUID, db: AsyncSession = Depends(get_session)):
    game = await crud.get_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    players = await crud.get_players_by_game(db, game_id)
    if not players:
        raise HTTPException(status_code=404, detail="No players found for this game")

    import random

    # Roll initiative for each player and assign turn order
    for player in players:
        player.initiative = random.randint(1, 20) + player.stats.get("dexterity", 0)
        await crud.update_player(db, player)

    # Sort players by turn order descending
    players = sorted(players, key=lambda p: p.initiative, reverse=True)

    # Set players' order based on initiative
    for index, player in enumerate(players):
        player.order = index + 1
        await crud.update_player(db, player)

    # Set the current player to the one with the highest initiative
    game.current_player_id = players[0].id
    await crud.update_game(db, game)

    return players


@router.get("/game/{game_id}/history", response_model=list[models.History])
async def get_game_history(game_id: UUID, db: AsyncSession = Depends(get_session)):
    game = await crud.get_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    history_entries = await crud.get_history_by_game(db, game_id)
    return history_entries


@router.post("/game/{game_id}/player_turn", response_model=models.Game)
async def play_player_turn(
    game_id: UUID,
    turn_data: models.PlayerTurnSchema,
    db: AsyncSession = Depends(get_session),
):
    """
    Joue un tour pour le joueur en cours, en fonction de l'option choisie.
    """
    game = await crud.get_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if game.phase != models.Phase.PLAYER:
        raise HTTPException(status_code=400, detail="It's not the player's turn")

    players = game.players
    actual_player = next((p for p in players if p.id == game.current_player_id), None)

    if actual_player is None:
        raise HTTPException(status_code=500, detail="Current player not found")

    # Récupérer l'option choisie
    option_id = turn_data.option_id

    # On récupère la description de l'option choisie dans l'historique
    history_entries = await crud.get_history_by_game(db, game_id)
    if not history_entries:
        raise HTTPException(status_code=404, detail="No history found for this game")

    last_entry = history_entries[-1]

    options = last_entry.result.get("options", [])
    option_description = None

    for option in options:
        if option.get("id") == option_id:
            option_description = option.get("description")
            break

    if not option_description:
        raise HTTPException(status_code=400, detail="Invalid option selected")

    print(
        f"Player {actual_player.display_name} selected option {option_id}: {option_description}"
    )

    # On place l'option choisie dans l'historique
    history_entry = models.History(
        game_id=game.id,
        player_id=actual_player.id,
        action_role=models.ChatRole.USER,
        success=True,
        result={
            "narration": f"{actual_player.display_name} choisit l'option {option_id}: {option_description}.",
            "options": [],
        },
    )

    await crud.create_history_entry(db, history_entry)
    # On passe le tour à l'IA
    game.phase = models.Phase.AI

    # On passe au joueur suivant
    players_sorted = sorted(players, key=lambda p: p.order)
    current_index = next(
        (i for i, p in enumerate(players_sorted) if p.id == actual_player.id), None
    )
    if current_index is not None:
        next_index = (current_index + 1) % len(players_sorted)
        game.current_player_id = players_sorted[next_index].id

    await crud.update_game(db, game)

    return game


@router.post("/game/{game_id}/ai_turn", response_model=models.Game)
async def play_ai_turn(game_id: UUID, db: AsyncSession = Depends(get_session)):
    """
    Joue un tour : soit l'IA parle (si c'est son tour), soit le joueur exécute une action.
    """
    game = await crud.get_game(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    players = game.players

    if game.phase == "AI":
        # C'est le tour de l'IA

        if game.turn == 0:
            # Premier tour : l'IA décrit la scène
            scenario = game.scenario
            if not scenario:
                raise HTTPException(
                    status_code=404, detail="Scenario not found for this game"
                )

            # Prompt qui permet de souhaiter la bienvenue aux joueurs (en donnant les détails des joueurs à l'IA) dans le scénario
            prompt = f"Le scénario est le suivant : {scenario.context}.\n\n"
            prompt += "Les joueurs sont : \n"
            for player in players:
                prompt += f"\t{player.display_name}, un {player.role} avec {player.hp} points de vie et {player.mp} points de mana. \n"
                prompt += f"\t\tLes statistiques de {player.display_name} sont : {player.stats} et initiative {player.initiative}. \n"
            prompt += "\n\nSouhaite la **bienvenue aux joueurs** en **introduisant le scénario** et en **rappelant aux joueurs pourquoi ils sont là**, décris la scène en donnant les infos d'où les joueurs sont et ce que les joueurs voient, puis propose des options d'actions possibles au joueur en cours.\n"
            # Récupération du joueur avec l'initiative la plus haute
            actual_player = next(
                (p for p in players if p.id == game.current_player_id), None
            )

            if actual_player is None:
                raise HTTPException(status_code=500, detail="Current player not found")

            prompt += f"\nC'est le tour de {actual_player.display_name}, qui a l'initiative la plus haute. "

            print(f"Prompt pour l'IA : {prompt}")

            # Enregistre l'entrée d'historique
            history_entry = models.History(
                game_id=game.id,
                player_id=None,
                action_role=models.ChatRole.USER,
                success=True,
                result={
                    "narration": prompt,
                    "options": [],
                },  # Options vides pour l'instant
            )

            await crud.create_history_entry(db, history_entry)

            client = AsyncClient(host=settings.OLLAMA_SERVER)
            response = await client.chat(
                model="game_master",
                messages=[{"role": models.ChatRole.USER, "content": prompt}],
                stream=False,
                format=models.AIResponseValidator.model_json_schema(),
            )

            print(f"Réponse brute de l'IA : {response}")

            # Valide la réponse de l'IA
            try:
                ai_message = models.AIResponseValidator.model_validate_json(
                    response["message"]["content"]
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid response format from AI: {e}",
                )

            print(f"Réponse de l'IA : {ai_message}")

            # Enregistre l'entrée d'historique
            history_entry = models.History(
                game_id=game.id,
                player_id=game.current_player_id,
                action_role=models.ChatRole.ASSISTANT,
                success=True,
                result=ai_message.model_dump(),
            )

            await crud.create_history_entry(db, history_entry)
            game.turn += 1
            game.phase = models.Phase.PLAYER
            await crud.update_game(db, game)

        else:
            # Ce n'est pas le tour 0
            # On récupère l'historique pour "messages" à envoyer à l'IA
            # On ajoute l'ordre de répondre au format attendu par l'IA (dernier message = ordre)

            history_entries = await crud.get_history_by_game(db, game_id)
            messages = []
            for entry in history_entries:
                role = entry.action_role
                content = entry.result.get("narration", "")
                if content:
                    # Si c'est le dernier message, on insiste pour que l'IA réponde au format attendu
                    if entry == history_entries[-1]:
                        if not game.scenario:
                            raise HTTPException(
                                status_code=404, detail="Scenario not found for this game"
                            )
                        content += "\n\nTon rôle est de diriger une aventure interactive avec exploration, énigmes et combats obligatoires."
                        content += f"\n\nRappel de l'obectif : {game.scenario.objectives}.\n"
                        content += f"\n\nRéponds strictement au format JSON demandé, sans rien ajouter d'autre.\n\nLe schema est le suivant:\n{models.AIResponseValidator.model_json_schema()}"
                    messages.append({"role": role, "content": content})

            print(f"Messages pour l'IA : {messages}")

            client = AsyncClient(host=settings.OLLAMA_SERVER)
            response = await client.chat(
                model="game_master",
                messages=messages,
                stream=False,
                format=models.AIResponseValidator.model_json_schema(),
            )

            print(f"Réponse brute de l'IA : {response}")

            # Valide la réponse de l'IA
            try:
                ai_message = models.AIResponseValidator.model_validate_json(
                    response["message"]["content"]
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid response format from AI: {e}",
                )
            
            # On vérifie que les options ne sont pas vides
            if not ai_message.options:
                raise HTTPException(
                    status_code=500,
                    detail="AI response contains no options, which is invalid.",
                )

            print(f"Réponse de l'IA : {ai_message}")

            # Enregistre l'entrée d'historique
            history_entry = models.History(
                game_id=game.id,
                player_id=game.current_player_id,
                action_role=models.ChatRole.ASSISTANT,
                success=True,
                result=ai_message.model_dump(),
            )

            await crud.create_history_entry(db, history_entry)

            game.turn += 1
            game.phase = models.Phase.PLAYER

            # On passe au joueur suivant
            players_sorted = sorted(players, key=lambda p: p.order)
            actual_player = next(
                (p for p in players_sorted if p.id == game.current_player_id), None
            )

            if actual_player is None:
                raise HTTPException(status_code=500, detail="Current player not found")

            current_index = next(
                (i for i, p in enumerate(players_sorted) if p.id == actual_player.id),
                None,
            )
            if current_index is not None:
                next_index = (current_index + 1) % len(players_sorted)
                game.current_player_id = players_sorted[next_index].id

            await crud.update_game(db, game)

        return game

    else:
        raise HTTPException(status_code=400, detail="It's not the AI's turn")
