import { Card, ProgressBar } from 'react-bootstrap'
import { Player } from '../types/gameTypes'

interface PlayerStatsProps {
  player: Player
}

export function PlayerStats({ player }: PlayerStatsProps) {
  return (
    <Card className="card-glow">
      <Card.Header className="dnd-title">Votre personnage</Card.Header>
      <Card.Body>
        <div className="text-center mb-3">
          <h4 className="stat-value mb-1">{player.display_name}</h4>
          <div className="badge stat-badge fs-6">{player.role}</div>
        </div>

        <div className="stats-container mb-4">
          <div className="mb-3">
            <div className="d-flex justify-content-between mb-1">
              <span className="stat-name">Points de vie</span>
              <span className="stat-value">{player.hp.toFixed(1)}/100</span>
            </div>
            <ProgressBar
              variant="danger"
              now={player.hp}
              max={100}
              className="mb-3"
              style={{ height: '20px' }}
            />

            <div className="d-flex justify-content-between mb-1">
              <span className="stat-name">Mana</span>
              <span className="stat-value">{player.mp.toFixed(1)}/100</span>
            </div>
            <ProgressBar
              variant="primary"
              now={player.mp}
              max={100}
              style={{ height: '20px' }}
            />
          </div>
        </div>

        <Card className="stats-container">
          <Card.Header className="dnd-title">Statistiques</Card.Header>
          <Card.Body>
            <div className="stat-grid">
              {Object.entries(player.stats).map(([stat, value]) => (
                <div key={stat} className="stat-item">
                  <span className="stat-name">{stat.charAt(0).toUpperCase() + stat.slice(1)}</span>
                  <span className="stat-value">{value}</span>
                </div>
              ))}
            </div>
          </Card.Body>
        </Card>
      </Card.Body>
    </Card>
  )
}
