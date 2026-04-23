export type ActionType = 'cast' | 'hit' | 'heal' | 'skill' | 'other'

export interface CombatUnit {
  id: string
  name: string
  faction: string
  max_hp: number
  current_hp: number
  shield: number
  current_anger: number
  ye_zhang_shield: number
}

export interface CombatLog {
  id: string
  round: number
  unit_id: string
  action_type: ActionType
  description: string
  hp_change: number
  anger_change: number
  timestamp: number
}

export interface BattleState {
  units: CombatUnit[]
  current_round: number
  logs: CombatLog[]
  is_active: boolean
}

export interface MonitorRegion {
  x: number
  y: number
  width: number
  height: number
}

export interface BattleRecord {
  id: string
  start_time: number
  end_time: number | null
  opponent_name: string | null
  result: string | null
  unit_ids: string[]
}
