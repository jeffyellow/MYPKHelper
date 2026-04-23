import { useWebSocket } from '@/hooks/useWebSocket'
import { useCombatStore } from '@/stores/useCombatStore'
import LogViewer from './LogViewer'
import OCRDebugPanel from './OCRDebugPanel'

export default function ActionPanel() {
  const { startBattle, endBattle } = useWebSocket()
  const isActive = useCombatStore((s) => s.is_active)
  const currentRound = useCombatStore((s) => s.current_round)

  return (
    <div className="w-1/5 min-w-[240px] flex flex-col border-l border-border-gray bg-white">
      <div className="flex-1 overflow-hidden">
        <LogViewer />
      </div>
      <OCRDebugPanel />
      <div className="shrink-0 border-t border-border-gray p-4 space-y-3">
        <div className="text-center text-sm text-gray-500">
          {isActive ? `第 ${currentRound} 回合` : '战斗未开始'}
        </div>
        <button
          onClick={startBattle}
          disabled={isActive}
          className={`w-full py-3 rounded-xl font-medium text-white transition-colors ${
            isActive
              ? 'bg-gray-300 cursor-not-allowed'
              : 'bg-airtable-blue hover:bg-blue-700'
          }`}
        >
          战斗开始
        </button>
        <button
          onClick={endBattle}
          disabled={!isActive}
          className={`w-full py-3 rounded-xl font-medium text-white transition-colors ${
            !isActive
              ? 'bg-gray-300 cursor-not-allowed'
              : 'bg-red-500 hover:bg-red-600'
          }`}
        >
          战斗结束
        </button>
      </div>
    </div>
  )
}
