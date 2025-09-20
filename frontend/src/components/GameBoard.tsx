import { Card, Badge } from 'react-bootstrap'
import { GameState } from '../types/gameTypes.js'  // Ajout de l'extension .js

interface GameBoardProps {
  gameState: GameState
}

export function GameBoard({ gameState }: GameBoardProps) {
  const lastAction = gameState.history[gameState.history.length - 1]

  return (
    <Card className="mb-4">
      <Card.Header>
        <div className="d-flex justify-content-between">
          <span>Tour {gameState.turn}</span>
          {lastAction && (
            <Badge bg="primary">
              {lastAction.action.split(' ').slice(0, 3).join(' ')}...
            </Badge>
          )}
        </div>
      </Card.Header>
      <Card.Body>
        <Card.Title>Narration</Card.Title>
        <Card.Text className="narration-text">
          {lastAction?.ai_narration || "La partie va commencer..."}
        </Card.Text>
      </Card.Body>
    </Card>
  )
}
