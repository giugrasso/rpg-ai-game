import { GameState, AIResponse, Scenario, Player, DiceRoll } from '../types/gameTypes'

const API_BASE = '/api'

// Fonction utilitaire pour gérer les erreurs de réponse
async function handleResponse(response: Response) {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(`Erreur ${response.status}: ${JSON.stringify(errorData)}`)
  }

  const data = await response.json()

  // Vérification minimale de la structure de la réponse
  if (data.error) {
    throw new Error(`Erreur API: ${data.error}`)
  }

  return data
}

export const GameApi = {
  // Récupérer les scénarios disponibles
  async getScenarios(): Promise<Scenario[]> {
    const response = await fetch(`${API_BASE}/scenarios`)
    return handleResponse(response)
  },

  // Créer une nouvelle partie
  async createGame(scenarioId: string): Promise<GameState> {
    const response = await fetch(`${API_BASE}/games`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_id: scenarioId })
    })
    return handleResponse(response)
  },

  // Rejoindre une partie
  async joinGame(gameId: string, player: Omit<Player, 'id'>): Promise<GameState> {
    const response = await fetch(`${API_BASE}/games/${gameId}/join`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(player)
    })
    return handleResponse(response)
  },

  // Envoyer une action
  async sendAction(gameId: string, playerId: string, action: string): Promise<AIResponse> {
    const response = await fetch(`${API_BASE}/games/${gameId}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player_id: playerId, action })
    })

    const data = await handleResponse(response)

    // Vérification minimale de la structure de la réponse
    if (!data.narration || !data.options) {
      throw new Error("Réponse de l'IA mal formatée: narration ou options manquantes")
    }

    return data
  },

  // Choisir une option
  async chooseOption(gameId: string, playerId: string, optionId: number): Promise<GameState> {
    const response = await fetch(`${API_BASE}/games/${gameId}/choose`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player_id: playerId, option_id: optionId })
    })
    return handleResponse(response)
  },

  // Vérifier le modèle Ollama
  async checkModel(): Promise<{ model_exists: boolean }> {
    const response = await fetch(`${API_BASE}/config/get_model`)
    return handleResponse(response)
  },

  // Créer le modèle Ollama si nécessaire
  async createModel(): Promise<{ status: string }> {
    const response = await fetch(`${API_BASE}/config/set_model`, {
      method: 'POST'
    })
    return handleResponse(response)
  },

  // Récupérer le dernier jet de dé
  async getLastRoll(gameId: string): Promise<DiceRoll|null> {
    try {
      const response = await fetch(`${API_BASE}/games/${gameId}/last_roll`)
      if (response.status === 404) {
        return null
      }
      return handleResponse(response)
    } catch (error) {
      if (error instanceof Error && error.message.includes('404')) {
        return null
      }
      throw error
    }
  }
}
