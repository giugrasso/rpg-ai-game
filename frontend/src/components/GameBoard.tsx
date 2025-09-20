import { Card, Badge } from 'react-bootstrap'
import { GameState } from '../types/gameTypes'

interface GameBoardProps {
  gameState: GameState
  aiResponse?: {
    narration: string
  }
}

export function GameBoard({ gameState, aiResponse }: GameBoardProps) {
  const lastAction = gameState.history.length > 0
    ? gameState.history[gameState.history.length - 1]
    : null

  // Déterminer quelle narration afficher
  const narrationToDisplay = aiResponse?.narration ||
                            lastAction?.ai_narration ||
                            "La partie va commencer..."

  return (
    <Card className="mb-4">
      <Card.Header>
        <div className="d-flex justify-content-between align-items-center">
          <span>Tour {gameState.turn}</span>
          {lastAction && (
            <Badge bg="primary" className="ms-2">
              {lastAction.action.substring(0, 30)}...
            </Badge>
          )}
        </div>
      </Card.Header>
      <Card.Body>
        <Card.Title>Narration</Card.Title>
        <Card.Text className="narration-text">
          {narrationToDisplay}
        </Card.Text>

        {lastAction?.chosen_option && (
          <div className="mt-3 pt-3 border-top">
            <Card.Subtitle className="mb-2 text-muted">
              Dernière option choisie:
            </Card.Subtitle>
            <Card.Text>
              {lastAction.options?.find(opt => opt.id === lastAction.chosen_option)?.description ||
               "Aucune option sélectionnée"}
            </Card.Text>
          </div>
        )}
      </Card.Body>
    </Card>
  )
}
