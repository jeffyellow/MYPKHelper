import { useState, useEffect } from 'react'
import { useCombatStore } from '@/stores/useCombatStore'
import type { BattleRecord } from '@/types'

export default function HistoryPage() {
  const [records, setRecords] = useState<BattleRecord[]>([])
  const [loading, setLoading] = useState(true)
  const setCurrentView = useCombatStore((s) => s.setCurrentView)

  useEffect(() => {
    fetch('http://localhost:8765/api/battles')
      .then((res) => res.json())
      .then((data) => {
        setRecords(data.battles || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const formatTime = (ts: number) => {
    return new Date(ts).toLocaleString('zh-CN')
  }

  const exportTxt = (record: BattleRecord) => {
    const lines = [
      `战斗记录: ${record.id}`,
      `对手: ${record.opponent_name || '未知'}`,
      `结果: ${record.result || '未知'}`,
      `开始: ${formatTime(record.start_time)}`,
      `结束: ${record.end_time ? formatTime(record.end_time) : '未结束'}`,
      '',
    ]
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `battle-${record.id}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col h-full bg-light-surface">
      <div className="flex items-center justify-between h-16 px-6 bg-white border-b border-border-gray">
        <h1 className="text-deep-navy font-medium text-lg">历史战斗记录</h1>
        <button
          onClick={() => setCurrentView('combat')}
          className="px-4 py-2 rounded-lg bg-airtable-blue text-white text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          返回战斗
        </button>
      </div>
      <div className="flex-1 overflow-auto p-6">
        {loading ? (
          <div className="text-center text-gray-400 py-12">加载中...</div>
        ) : records.length === 0 ? (
          <div className="text-center text-gray-400 py-12">暂无战斗记录</div>
        ) : (
          <div className="space-y-4 max-w-4xl mx-auto">
            {records.map((record) => (
              <div
                key={record.id}
                className="bg-white rounded-2xl border border-border-gray p-5"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        record.result === 'win'
                          ? 'bg-green-100 text-green-700'
                          : record.result === 'lose'
                          ? 'bg-red-100 text-red-700'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {record.result === 'win'
                        ? '胜利'
                        : record.result === 'lose'
                        ? '失败'
                        : '未知'}
                    </span>
                    <span className="text-deep-navy font-medium">
                      对手: {record.opponent_name || '未知'}
                    </span>
                  </div>
                  <button
                    onClick={() => exportTxt(record)}
                    className="text-airtable-blue text-sm hover:underline"
                  >
                    导出 TXT
                  </button>
                </div>
                <div className="text-sm text-gray-500 space-y-1">
                  <div>开始时间: {formatTime(record.start_time)}</div>
                  {record.end_time && (
                    <div>结束时间: {formatTime(record.end_time)}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
