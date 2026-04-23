import { useEffect, useRef, useCallback } from 'react'
import { useCombatStore } from '@/stores/useCombatStore'
import type { CombatUnit, CombatLog, BattleState } from '@/types'

const WS_URL = 'ws://localhost:8765/ws'

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const store = useCombatStore()

  const send = useCallback((message: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    }
  }, [])

  useEffect(() => {
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        handleMessage(msg)
      } catch {
        console.error('Failed to parse WebSocket message')
      }
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
    }

    ws.onerror = (err) => {
      console.error('WebSocket error:', err)
    }

    return () => {
      ws.close()
    }
  }, [])

  const handleMessage = (msg: any) => {
    switch (msg.type) {
      case 'state_update': {
        const state: BattleState = msg.data
        store.updateFromState(state)
        break
      }
      case 'unit_updated': {
        const unit: CombatUnit = msg.unit
        store.updateUnit(unit)
        break
      }
      case 'logs': {
        const logs: CombatLog[] = msg.logs
        store.setLogs(logs)
        break
      }
      case 'region_set': {
        store.setMonitorRegion(msg.region)
        store.setIsMonitoring(true)
        break
      }
      case 'battle_started':
        store.setIsActive(true)
        break
      case 'battle_ended':
        store.setIsActive(false)
        break
      case 'ocr_debug': {
        store.setOcrDebug(msg.data)
        break
      }
    }
  }

  const startBattle = useCallback(() => {
    send({ action: 'start_battle' })
  }, [send])

  const endBattle = useCallback(() => {
    send({ action: 'end_battle' })
  }, [send])

  const setRegion = useCallback(
    (region: { x: number; y: number; width: number; height: number }) => {
      send({ action: 'set_region', region })
    },
    [send]
  )

  const fetchLogs = useCallback(
    (unitId: string) => {
      send({ action: 'get_logs', unit_id: unitId })
    },
    [send]
  )

  const initUnit = useCallback(
    (unitId: string, name: string, faction: string, yeZhangShield?: number) => {
      send({
        action: 'init_unit',
        unit_id: unitId,
        name,
        faction,
        ye_zhang_shield: yeZhangShield ?? 0,
      })
    },
    [send]
  )

  const sendManualUpdate = useCallback(
    (unitId: string, updateType: string, value: number, description?: string) => {
      send({
        action: 'manual_update',
        unit_id: unitId,
        update_type: updateType,
        value,
        description: description ?? '',
      })
    },
    [send]
  )

  // 监听 Chrome 扩展的区域选择
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (event.data?.type === 'MYPK_REGION_SELECTED') {
        setRegion(event.data.region)
      }
    }
    window.addEventListener('message', handler)
    return () => window.removeEventListener('message', handler)
  }, [setRegion])

  return {
    startBattle,
    endBattle,
    setRegion,
    fetchLogs,
    initUnit,
    sendManualUpdate,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
  }
}
