import { Card, ProgressBar } from 'react-bootstrap'
import { Player } from '../types/gameTypes.js'  // Ajout de l'extension .js

interface PlayerStatsProps {
  player: Player
}

export function PlayerStats({ player }: PlayerStatsProps) {
  return (
    <Card>
      <Card.Header>Votre personnage</Card.Header>
      <Card.Body>
        <Card.Title>{player.display_name}</Card.Title>
        <Card.Subtitle className="mb-2 text-muted">{player.role}</Card.Subtitle>

        <div className="mb-3">
          <div className="mb-2">
            <div className="d-flex justify-content-between">
              <span>Points de vie</span>
              <span>{player.hp.toFixed(1)}/100</span>
            </div>
            <ProgressBar
              variant="danger"
              now={player.hp}
              max={100}
              label={`${player.hp.toFixed(1)}%`}
              striped
              animated={player.hp < 30}
            />
          </div>

          <div>
            <div className="d-flex justify-content-between">
              <span>Mana</span>
              <span>{player.mp.toFixed(1)}/100</span>
            </div>
            <ProgressBar
              variant="primary"
              now={player.mp}
              max={100}
              label={`${player.mp.toFixed(1)}%`}
            />
          </div>
        </div>

        <Card className="mt-3">
          <Card.Header>Statistiques</Card.Header>
          <Card.Body>
            <ul className="list-group list-group-flush">
              {Object.entries(player.stats).map(([stat, value]) => (
                <li key={stat} className="list-group-item d-flex justify-content-between">
                  {stat.charAt(0).toUpperCase() + stat.slice(1)}
                  <span className="badge bg-secondary">{value}</span>
                </li>
              ))}
            </ul>
          </Card.Body>
        </Card>
      </Card.Body>
    </Card>
  )
}
