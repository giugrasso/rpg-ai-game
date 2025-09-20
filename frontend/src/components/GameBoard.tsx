import { Card, Badge } from 'react-bootstrap'
import { GameState, AIResponse } from '../types/gameTypes'

interface GameBoardProps {
  gameState: GameState
  aiResponse?: AIResponse | null
}

export function GameBoard({ gameState, aiResponse }: GameBoardProps) {
  const lastAction = gameState.history.length > 0
    ? gameState.history[gameState.history.length - 1]
    : null

  // Déterminer quelle narration afficher
  const narrationToDisplay = aiResponse?.narration ||
                            lastAction?.ai_narration ||
                            "La partie va commencer..."

  // Déterminer le type d'option pour le style
  const getOptionType = (option: any) => {
    if (!option) return 'neutral'
    if (option.health_point_change < 0) return 'danger'
    if (option.health_point_change > 0 || option.mana_point_change > 0) return 'success'
    return 'neutral'
  }

  return (
    <Card className="card-glow mb-4">
      <Card.Header>
        <div className="d-flex justify-content-between align-items-center">
          <span className="stat-value">Tour {gameState.turn}</span>
          {lastAction && (
            <Badge bg="primary" className="ms-2 stat-badge">
              {lastAction.action.substring(0, 30)}...
            </Badge>
          )}
        </div>
      </Card.Header>
      <Card.Body>
        <Card.Title className="dnd-title">Narration</Card.Title>
        <div className="parchment-effect narration-text p-3 mb-3">
          {narrationToDisplay}
        </div>

        {lastAction?.chosen_option && (
          <div className="mt-3 pt-3 border-top border-secondary">
            <Card.Subtitle className="mb-2 text-muted">
              <strong>Dernière option choisie:</strong>
            </Card.Subtitle>
            <div className={`option-card option-${getOptionType(
              lastAction.options?.find(opt => opt.id === lastAction.chosen_option)
            )}`}>
              {lastAction.options?.find(opt => opt.id === lastAction.chosen_option)?.description ||
               "Aucune option sélectionnée"}
            </div>
          </div>
        )}
      </Card.Body>
    </Card>
  )
}
