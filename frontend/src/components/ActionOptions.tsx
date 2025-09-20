import { Button, Card } from 'react-bootstrap'
import { Option, Player } from '../types/gameTypes'

interface ActionOptionsProps {
  options: Option[]
  player: Player
  onSelectOption: (optionId: number) => void
  selectedOption: number | null
}

export function ActionOptions({
  options,
  player,
  onSelectOption,
  selectedOption
}: ActionOptionsProps) {
  // Déterminer le type d'option pour le style
  const getOptionType = (option: Option) => {
    if (option.health_point_change < 0) return 'danger'
    if (option.health_point_change > 0 || option.mana_point_change > 0) return 'success'
    return 'neutral'
  }

  return (
    <Card className="card-glow mb-4">
      <Card.Header className="dnd-title">Options disponibles</Card.Header>
      <Card.Body>
        <div className="d-grid gap-3">
          {options.map((option) => {
            const statValue = player.stats[option.related_stat] || 10
            const adjustedSuccess = option.success_rate * (statValue / 10)

            return (
              <div
                key={option.id}
                className={`option-card option-${getOptionType(option)} ${selectedOption === option.id ? 'selected' : ''}`}
                onClick={() => onSelectOption(option.id)}
              >
                <div className="d-flex flex-column">
                  <div className="fw-bold mb-2">{option.description}</div>

                  <div className="d-flex justify-content-between align-items-center mt-2">
                    <div className="stat-details">
                      <span className="stat-value me-2">
                        Succès: {option.success_rate.toFixed(1)} → {adjustedSuccess.toFixed(2)}
                      </span>
                      <span className="badge stat-badge me-1">
                        {option.related_stat} {statValue}
                      </span>

                      {option.health_point_change !== 0 && (
                        <span className={`badge me-1 ${option.health_point_change > 0 ? 'bg-success' : 'bg-danger'}`}>
                          ΔPV: {(option.health_point_change * 100).toFixed(0)}
                        </span>
                      )}

                      {option.mana_point_change !== 0 && (
                        <span className="badge bg-info me-1">
                          ΔMana: {(option.mana_point_change * 100).toFixed(0)}
                        </span>
                      )}
                    </div>

                    <Button
                      variant={selectedOption === option.id ? "primary" : "outline-primary"}
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        onSelectOption(option.id)
                      }}
                    >
                      Choisir
                    </Button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </Card.Body>
    </Card>
  )
}
