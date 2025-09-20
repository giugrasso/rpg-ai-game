import { GameState, AIResponse, Scenario, Player, DiceRoll } from '../types/gameTypes.js'  // Ajout de l'extension .js

const API_BASE = '/api'

export const GameApi = {
  /**
   * Récupère la liste des scénarios disponibles
   * @returns Promise<Scenario[]> - Liste des scénarios
   */
  async getScenarios(): Promise<Scenario[]> {
    try {
      const response = await fetch(`${API_BASE}/scenarios`)
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(`Échec de récupération des scénarios: ${response.status} ${response.statusText}. ${JSON.stringify(errorData)}`)
      }
      return response.json()
    } catch (error) {
      console.error("Erreur dans getScenarios:", error)
      throw error
    }
  },

  /**
   * Crée une nouvelle partie
   * @param scenarioId - ID du scénario choisi
   * @returns Promise<GameState> - État initial de la partie
   */
  async createGame(scenarioId: string): Promise<GameState> {
    try {
      const response = await fetch(`${API_BASE}/games`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ scenario_id: scenarioId })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(`Échec de création de partie: ${response.status} ${response.statusText}. ${JSON.stringify(errorData)}`)
      }

      return response.json()
    } catch (error) {
      console.error("Erreur dans createGame:", error)
      throw error
    }
  },

  /**
   * Rejoint une partie existante avec un personnage
   * @param gameId - ID de la partie
   * @param player - Données du joueur (sans l'ID)
   * @returns Promise<GameState> - État mis à jour de la partie
   */
  async joinGame(gameId: string, player: Omit<Player, 'id'>): Promise<GameState> {
    try {
      const response = await fetch(`${API_BASE}/games/${gameId}/join`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(player)
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(`Échec de jointure de partie: ${response.status} ${response.statusText}. ${JSON.stringify(errorData)}`)
      }

      return response.json()
    } catch (error) {
      console.error("Erreur dans joinGame:", error)
      throw error
    }
  },

  /**
   * Envoie une action au backend
   * @param gameId - ID de la partie
   * @param playerId - ID du joueur
   * @param action - Description de l'action
   * @returns Promise<AIResponse> - Réponse de l'IA avec narration et options
   */
  async sendAction(gameId: string, playerId: string, action: string): Promise<AIResponse> {
    try {
      const response = await fetch(`${API_BASE}/games/${gameId}/action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ player_id: playerId, action })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(`Échec d'envoi d'action: ${response.status} ${response.statusText}. ${JSON.stringify(errorData)}`)
      }

      const data = await response.json()

      // Vérification minimale de la structure de la réponse
      if (!data.narration || !data.options) {
        throw new Error("Réponse de l'IA mal formatée: narration ou options manquantes")
      }

      return data
    } catch (error) {
      console.error("Erreur dans sendAction:", error)
      throw error
    }
  },

  /**
   * Choisit une option parmi celles proposées
   * @param gameId - ID de la partie
   * @param playerId - ID du joueur
   * @param optionId - ID de l'option choisie
   * @returns Promise<GameState> - État mis à jour de la partie
   */
  async chooseOption(gameId: string, playerId: string, optionId: number): Promise<GameState> {
    try {
      const response = await fetch(`${API_BASE}/games/${gameId}/choose`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ player_id: playerId, option_id: optionId })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(`Échec de choix d'option: ${response.status} ${response.statusText}. ${JSON.stringify(errorData)}`)
      }

      return response.json()
    } catch (error) {
      console.error("Erreur dans chooseOption:", error)
      throw error
    }
  },

  /**
   * Récupère l'historique d'une partie
   * @param gameId - ID de la partie
   * @returns Promise<Array> - Historique des actions
   */
  async getHistory(gameId: string): Promise<Array<any>> {
    try {
      const response = await fetch(`${API_BASE}/games/${gameId}/history`)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(`Échec de récupération de l'historique: ${response.status} ${response.statusText}. ${JSON.stringify(errorData)}`)
      }

      return response.json()
    } catch (error) {
      console.error("Erreur dans getHistory:", error)
      throw error
    }
  },

  /**
   * Vérifie si le modèle Ollama est disponible
   * @returns Promise<{ model_exists: boolean }> - Statut du modèle
   */
  async checkModel(): Promise<{ model_exists: boolean }> {
    try {
      const response = await fetch(`${API_BASE}/config/get_model`)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(`Échec de vérification du modèle: ${response.status} ${response.statusText}. ${JSON.stringify(errorData)}`)
      }

      return response.json()
    } catch (error) {
      console.error("Erreur dans checkModel:", error)
      throw error
    }
  },

  /**
   * Crée le modèle Ollama si nécessaire
   * @returns Promise<{ status: string }> - Statut de la création
   */
  async createModel(): Promise<{ status: string }> {
    try {
      const response = await fetch(`${API_BASE}/config/set_model`, {
        method: 'POST'
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(`Échec de création du modèle: ${response.status} ${response.statusText}. ${JSON.stringify(errorData)}`)
      }

      return response.json()
    } catch (error) {
      console.error("Erreur dans createModel:", error)
      throw error
    }
  },

  /**
   * Récupère le dernier jet de dé
   * @param gameId - ID de la partie
   * @returns Promise<DiceRoll|null> - Résultat du dernier jet de dé ou null
   */
  async getLastRoll(gameId: string): Promise<DiceRoll|null> {
    try {
      const response = await fetch(`${API_BASE}/games/${gameId}/last_roll`)

      if (!response.ok) {
        if (response.status === 404) {
          return null
        }
        const errorData = await response.json().catch(() => ({}))
        throw new Error(`Échec de récupération du jet de dé: ${response.status} ${response.statusText}. ${JSON.stringify(errorData)}`)
      }

      return response.json()
    } catch (error) {
      console.error("Erreur dans getLastRoll:", error)
      throw error
    }
  }
}
