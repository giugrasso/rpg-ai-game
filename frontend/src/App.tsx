import { useState, useEffect } from 'react'
import { Container, Row, Col, Spinner, Alert, Navbar, Nav, Button, Card } from 'react-bootstrap'
import { GameApi } from './api/gameApi'
import { GameBoard } from './components/GameBoard'
import { PlayerStats } from './components/PlayerStats'
import { ActionOptions } from './components/ActionOptions'
import { GameState, AIResponse, Scenario, Player } from './types/gameTypes'
import './App.css'

function App() {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [gameState, setGameState] = useState<GameState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedOption, setSelectedOption] = useState<number | null>(null)
  const [aiResponse, setAiResponse] = useState<AIResponse | null>(null)
  const [currentAction, setCurrentAction] = useState("Observer les alentours pour évaluer la situation")

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

  // Démarrer une nouvelle partie
  const startExampleGame = async () => {
    if (scenarios.length === 0) return

    try {
      setLoading(true)
      setError(null)

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
      await sendAction()

    } catch (err) {
      setError("Erreur lors de la création de la partie: " + (err instanceof Error ? err.message : String(err)))
    } finally {
      setLoading(false)
    }
  }

  // Envoyer une action au backend
  const sendAction = async () => {
    if (!gameState) return

    try {
      setLoading(true)
      setError(null)
      const player = gameState.players[0]

      const response = await GameApi.sendAction(
        gameState.id,
        player.player_id,
        currentAction
      )

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

      const updatedGame = await GameApi.chooseOption(
        gameState.id,
        player.player_id,
        optionId
      )

      setGameState(updatedGame)
      setAiResponse(null)

      // Préparer la prochaine action basée sur la dernière narration
      if (updatedGame.history.length > 0) {
        const lastAction = updatedGame.history[updatedGame.history.length - 1]
        setCurrentAction(`[Suite] ${lastAction.action}`)
      }

    } catch (err) {
      setError("Erreur lors du choix de l'option: " + (err instanceof Error ? err.message : String(err)))
    } finally {
      setLoading(false)
    }
  }

  // Vérifier si le jeu est en attente d'une action
  const isWaitingForAction = !aiResponse && gameState

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
    return (
      <Container className="mt-5">
        <Alert variant="danger">{error}</Alert>
        <Button variant="primary" onClick={startExampleGame} className="mt-3">
          Réessayer
        </Button>
      </Container>
    )
  }

  if (!gameState) {
    return (
      <Container className="mt-5 text-center">
        <h2>Bienvenue dans RPG AI Game</h2>
        <p>Sélectionnez un scénario pour commencer</p>
        <Button variant="primary" onClick={startExampleGame} size="lg">
          Démarrer une partie d'exemple
        </Button>
      </Container>
    )
  }

  const player = gameState.players[0]
  const lastAction = gameState.history.length > 0
    ? gameState.history[gameState.history.length - 1]
    : null

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
          {/* Zone de narration - MODIFICATION ICI */}
          <Col md={8}>
            <GameBoard
              gameState={gameState}
              aiResponse={aiResponse ?? undefined}
            />

            {/* Options si une réponse AI est disponible */}
            {aiResponse && (
              <ActionOptions
                options={aiResponse.options}
                player={player}
                onSelectOption={chooseOption}
                selectedOption={selectedOption}
              />
            )}

            {/* Bouton pour envoyer une action si nécessaire */}
            {isWaitingForAction && (
              <div className="d-grid gap-2 mt-3">
                <Button
                  variant="primary"
                  size="lg"
                  onClick={sendAction}
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" />
                      {' '}Envoi en cours...
                    </>
                  ) : (
                    'Envoyer l\'action actuelle'
                  )}
                </Button>
              </div>
            )}
          </Col>

          {/* Stats du joueur */}
          <Col md={4}>
            <PlayerStats player={player} />

            {/* Informations sur l'action actuelle */}
            {isWaitingForAction && (
              <Card className="mt-3">
                <Card.Header>Action actuelle</Card.Header>
                <Card.Body>
                  <Card.Text>{currentAction}</Card.Text>
                  {lastAction && (
                    <Card.Text className="mt-2 text-muted small">
                      Dernière narration: {lastAction.ai_narration.substring(0, 100)}...
                    </Card.Text>
                  )}
                </Card.Body>
              </Card>
            )}
          </Col>
        </Row>
      </Container>
    </>
  )
}

export default App
