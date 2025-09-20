import { Button, Card } from 'react-bootstrap'
import { Option, Player } from '../types/gameTypes.js'  // Ajout de l'extension .js

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
  return (
    <Card>
      <Card.Header>Options disponibles</Card.Header>
      <Card.Body>
        <div className="d-grid gap-2">
          {options.map((option) => {
            const statValue = player.stats[option.related_stat] || 10
            const adjustedSuccess = option.success_rate * (statValue / 10)

            return (
              <Button
                key={option.id}
                variant={selectedOption === option.id ? "primary" : "outline-primary"}
                size="lg"
                className="text-start mb-2 btn-option"
                onClick={() => onSelectOption(option.id)}
                disabled={selectedOption !== null && selectedOption !== option.id}
              >
                <div className="text-start">
                  <div className="fw-bold">{option.description}</div>
                  <div className="small text-muted mt-1">
                    <span className="me-2">
                      Succès: {option.success_rate.toFixed(1)} → {adjustedSuccess.toFixed(2)}
                      (avec {option.related_stat}={statValue})
                    </span>
                    {option.health_point_change !== 0 && (
                      <span className={`me-2 ${option.health_point_change > 0 ? 'text-success' : 'text-danger'}`}>
                        ΔPV: {(option.health_point_change * 100).toFixed(0)}
                      </span>
                    )}
                    {option.mana_point_change !== 0 && (
                      <span className={`text-${option.mana_point_change > 0 ? 'info' : 'warning'}`}>
                        ΔMana: {(option.mana_point_change * 100).toFixed(0)}
                      </span>
                    )}
                  </div>
                </div>
              </Button>
            )
          })}
        </div>
      </Card.Body>
    </Card>
  )
}
