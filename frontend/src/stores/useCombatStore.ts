import { create } from 'zustand'
import type { CombatUnit, CombatLog, MonitorRegion, BattleState } from '@/types'

interface OCRDebugData {
  popup_numbers: Array<{
    value: number
    unit_name: string
    raw_text: string
    confidence: number
  }>
  actions: Array<{
    action_type: string
    text: string
    unit_name: string | null
    skill_name: string | null
    round_num: number | null
    hp_value: number | null
  }>
  timestamp: number
}

interface CombatStore extends BattleState {
  selected_unit_id: string | null
  monitor_region: MonitorRegion | null
  is_monitoring: boolean
  currentView: 'combat' | 'history'
  ocrDebug: OCRDebugData | null

  setUnits: (units: CombatUnit[]) => void
  updateUnit: (unit: CombatUnit) => void
  setLogs: (logs: CombatLog[]) => void
  addLog: (log: CombatLog) => void
  setCurrentRound: (round: number) => void
  setIsActive: (active: boolean) => void
  setSelectedUnit: (id: string | null) => void
  setMonitorRegion: (region: MonitorRegion | null) => void
  setIsMonitoring: (monitoring: boolean) => void
  setCurrentView: (view: 'combat' | 'history') => void
  setOcrDebug: (data: OCRDebugData | null) => void
  updateFromState: (state: BattleState) => void
  reset: () => void
}

const initialState: BattleState = {
  units: [],
  current_round: 0,
  logs: [],
  is_active: false,
}

export const useCombatStore = create<CombatStore>((set) => ({
  ...initialState,
  selected_unit_id: null,
  monitor_region: null,
  is_monitoring: false,
  currentView: 'combat',
  ocrDebug: null,

  setUnits: (units) => set({ units }),
  updateUnit: (unit) =>
    set((state) => ({
      units: state.units.map((u) => (u.id === unit.id ? unit : u)),
    })),
  setLogs: (logs) => set({ logs }),
  addLog: (log) =>
    set((state) => ({
      logs: [...state.logs, log],
    })),
  setCurrentRound: (current_round) => set({ current_round }),
  setIsActive: (is_active) => set({ is_active }),
  setSelectedUnit: (selected_unit_id) => set({ selected_unit_id }),
  setMonitorRegion: (monitor_region) => set({ monitor_region }),
  setIsMonitoring: (is_monitoring) => set({ is_monitoring }),
  setCurrentView: (currentView) => set({ currentView }),
  setOcrDebug: (ocrDebug) => set({ ocrDebug }),
  updateFromState: (state) => set({ ...state }),
  reset: () => set({ ...initialState, selected_unit_id: null, ocrDebug: null }),
}))
