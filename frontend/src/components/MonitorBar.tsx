import { useState } from 'react'
import { useCombatStore } from '@/stores/useCombatStore'

export default function MonitorBar() {
  const isMonitoring = useCombatStore((s) => s.is_monitoring)
  const setCurrentView = useCombatStore((s) => s.setCurrentView)
  const [isSelecting, setIsSelecting] = useState(false)

  const startSelection = async () => {
    if (isSelecting) return
    setIsSelecting(true)
    try {
      await fetch('/api/select-region', { method: 'POST' })
    } catch (err) {
      console.error('选区请求失败:', err)
    } finally {
      setIsSelecting(false)
    }
  }

  return (
    <div className="flex items-center h-16 px-6 bg-white border-b border-border-gray">
      <div className="flex items-center gap-4">
        <span className="text-deep-navy font-medium">监控设置</span>
        <button
          onClick={startSelection}
          disabled={isSelecting}
          className={`px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors ${
            isSelecting
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-airtable-blue hover:bg-blue-700'
          }`}
        >
          {isSelecting ? '请在屏幕上选择区域...' : '选择监控区域'}
        </button>
      </div>
      <div className="flex-1 flex justify-center">
        {isMonitoring && (
          <span className="text-red-600 font-bold animate-pulse">
            画面监控中
          </span>
        )}
      </div>
      <div className="flex items-center gap-3">
        <button
          onClick={() => setCurrentView('history')}
          className="px-4 py-2 rounded-lg border border-border-gray text-deep-navy text-sm font-medium hover:bg-light-surface transition-colors"
        >
          历史记录
        </button>
      </div>
    </div>
  )
}
