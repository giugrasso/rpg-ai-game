export interface Player {
  id: string
  player_id: string
  display_name: string
  role: string
  hp: number
  mp: number
  stats: Record<string, number>
  position?: string
}

export interface Option {
  id: number
  description: string
  success_rate: number
  health_point_change: number
  mana_point_change: number
  related_stat: string
}

export interface GameState {
  id: string
  scenario_id: string
  players: Player[]
  turn: number
  history: Array<{
    timestamp: string
    actor: string
    action: string
    ai_narration: string
    options?: Option[]
    chosen_option?: number
  }>
}

export interface AIResponse {
  narration: string
  options: Option[]
}

export interface Scenario {
  id: string
  name: string
  description: string
  objectives: string
  mode: string
  max_players: number
  roles: Record<string, {
    name: string
    stats: Record<string, number>
    description: string
  }>
  context: string
}

export interface DiceRoll {
  roll: number
  success: boolean
  narration: string
}
