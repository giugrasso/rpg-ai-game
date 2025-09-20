import { useState, useEffect } from 'react'
import { Container, Row, Col, Spinner, Alert, Navbar, Nav, Button } from 'react-bootstrap'
import { GameApi } from './api/gameApi.js'  // Ajout de l'extension .js
import { GameBoard } from './components/GameBoard.js'  // Ajout de l'extension .js
import { PlayerStats } from './components/PlayerStats.js'  // Ajout de l'extension .js
import { ActionOptions } from './components/ActionOptions.js'  // Ajout de l'extension .js
import { GameState, AIResponse, Scenario, Player } from './types/gameTypes.js'  // Ajout de l'extension .js
import './App.css'


function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [gameState, setGameState] = useState<GameState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedOption, setSelectedOption] = useState<number | null>(null)
  const [currentAction, setCurrentAction] = useState("")
  const [aiResponse, setAiResponse] = useState<AIResponse | null>(null)

  // Vérifier et créer le modèle Ollama au démarrage
  useEffect(() => {
    const initialize = async () => {
      try {
        setLoading(true)
        const { model_exists } = await GameApi.checkModel()
        if (!model_exists) {
          await GameApi.createModel()
        }
        await loadScenarios()
      } catch (err) {
        setError("Erreur d'initialisation: " + (err instanceof Error ? err.message : String(err)))
      } finally {
        setLoading(false)
      }
    }
    initialize()
  }, [])

  // Charger les scénarios disponibles
  const loadScenarios = async () => {
    try {
      const scenarios = await GameApi.getScenarios()
      setScenarios(scenarios)
    } catch (err) {
      setError("Impossible de charger les scénarios: " + (err instanceof Error ? err.message : String(err)))
    }
  }

  // Créer une nouvelle partie
  const createGame = async (scenarioId: string) => {
    try {
      setLoading(true)
      const newGame = await GameApi.createGame(scenarioId)
      setGameState(newGame)
      setError(null)
    } catch (err) {
      setError("Impossible de créer la partie: " + (err instanceof Error ? err.message : String(err)))
    } finally {
      setLoading(false)
    }
  }

  // Rejoindre une partie avec un personnage
  const joinGame = async (gameId: string, player: Omit<Player, 'id'>) => {
    try {
      setLoading(true)
      const updatedGame = await GameApi.joinGame(gameId, player)
      setGameState(updatedGame)
      setError(null)
    } catch (err) {
      setError("Impossible de rejoindre la partie: " + (err instanceof Error ? err.message : String(err)))
    } finally {
      setLoading(false)
    }
  }

  // Envoyer une action au backend
  const sendAction = async () => {
    if (!gameState || !currentAction) return

    try {
      setLoading(true)
      const player = gameState.players[0]
      const response = await GameApi.sendAction(gameState.id, player.player_id, currentAction)
      setAiResponse(response)
      setSelectedOption(null)
    } catch (err) {
      setError("Erreur lors de l'envoi de l'action: " + (err instanceof Error ? err.message : String(err)))
    } finally {
      setLoading(false)
    }
  }

  // Choisir une option
  const chooseOption = async (optionId: number) => {
    if (!gameState || !aiResponse) return

    try {
      setLoading(true)
      setSelectedOption(optionId)
      const player = gameState.players[0]
      const updatedGame = await GameApi.chooseOption(gameState.id, player.player_id, optionId)
      setGameState(updatedGame)
      setAiResponse(null)
    } catch (err) {
      setError("Erreur lors du choix de l'option: " + (err instanceof Error ? err.message : String(err)))
    } finally {
      setLoading(false)
    }
  }

  // Exemple de création de partie et ajout d'un joueur
  const startExampleGame = async () => {
    if (scenarios.length === 0) return

    try {
      setLoading(true)
      // 1. Créer une partie
      const newGame = await GameApi.createGame(scenarios[0].id)
      setGameState(newGame)

      // 2. Ajouter un joueur
      const player: Omit<Player, 'id'> = {
        player_id: "player-1",
        display_name: "Aventurier",
        role: "Chasseur",
        hp: 100,
        mp: 50,
        stats: {
          force: 18,
          intelligence: 12,
          charisme: 14,
          courage: 16,
          chance: 10
        }
      }

      const updatedGame = await GameApi.joinGame(newGame.id, player)
      setGameState(updatedGame)

      // 3. Envoyer une action initiale
      setCurrentAction("Observer les alentours pour évaluer la situation")
      await sendAction()
    } catch (err) {
      setError("Erreur lors de la création de la partie: " + (err instanceof Error ? err.message : String(err)))
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center vh-100">
        <Spinner animation="border" role="status">
          <span className="visually-hidden">Chargement...</span>
        </Spinner>
      </div>
    )
  }

  if (error) {
    return <Alert variant="danger">{error}</Alert>
  }

  if (!gameState) {
    return (
      <Container className="mt-5 text-center">
        <h2>Bienvenue dans RPG AI Game</h2>
        <p>Sélectionnez un scénario pour commencer</p>
        <Button variant="primary" onClick={startExampleGame}>
          Démarrer une partie d'exemple
        </Button>
      </Container>
    )
  }

  const player = gameState.players[0]

  return (
    <>
      <Navbar bg="dark" variant="dark" expand="lg">
        <Container>
          <Navbar.Brand>RPG AI Game</Navbar.Brand>
          <Navbar.Toggle aria-controls="basic-navbar-nav" />
          <Navbar.Collapse id="basic-navbar-nav">
            <Nav className="me-auto">
              <Nav.Link href="#">Partie en cours</Nav.Link>
              <Nav.Link href="#">Historique</Nav.Link>
            </Nav>
          </Navbar.Collapse>
        </Container>
      </Navbar>

      <Container className="mt-4">
        <Row className="g-4">
          {/* Zone de narration */}
          <Col md={8}>
            <GameBoard gameState={gameState} />

            {/* Options si une réponse AI est disponible */}
            {aiResponse && (
              <ActionOptions
                options={aiResponse.options}
                player={player}
                onSelectOption={chooseOption}
                selectedOption={selectedOption}
              />
            )}
          </Col>

          {/* Stats du joueur */}
          <Col md={4}>
            <PlayerStats player={player} />
          </Col>
        </Row>

        {/* Zone d'action */}
        {selectedOption === null && aiResponse && (
          <Row className="mt-3">
            <Col>
              <div className="d-grid gap-2">
                <Button
                  variant="success"
                  size="lg"
                  onClick={() => {
                    const firstOption = aiResponse.options[0]
                    if (firstOption) {
                      chooseOption(firstOption.id)
                    }
                  }}
                >
                  Choisir la première option rapidement
                </Button>
                <Button
                  variant="primary"
                  size="lg"
                  onClick={startExampleGame}
                >
                  Recommencer une nouvelle partie
                </Button>
              </div>
            </Col>
          </Row>
        )}
      </Container>
    </>
  )
}

export default App
