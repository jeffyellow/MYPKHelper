import { useCombatStore } from '@/stores/useCombatStore'

export default function LogViewer() {
  const logs = useCombatStore((s) => s.logs)
  const selectedId = useCombatStore((s) => s.selected_unit_id)

  const filteredLogs = selectedId
    ? logs.filter((l) => l.unit_id === selectedId)
    : logs

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-2 border-b border-border-gray bg-light-surface">
        <span className="text-xs font-medium text-gray-500">
          {selectedId ? '选中角色日志' : '全部日志'}
        </span>
      </div>
      <div className="flex-1 overflow-auto p-3 space-y-2">
        {filteredLogs.length === 0 ? (
          <div className="text-center text-gray-400 text-sm py-4">
            暂无日志
          </div>
        ) : (
          filteredLogs.map((log) => (
            <div
              key={log.id}
              className="text-xs p-2 rounded bg-white border border-border-gray"
            >
              <div className="flex justify-between text-gray-500 mb-1">
                <span>第{log.round}回合</span>
                <span>
                  {new Date(log.timestamp).toLocaleTimeString('zh-CN')}
                </span>
              </div>
              <div className="text-deep-navy">{log.description}</div>
              {(log.hp_change !== 0 || log.anger_change !== 0) && (
                <div className="flex gap-3 mt-1">
                  {log.hp_change !== 0 && (
                    <span
                      className={
                        log.hp_change < 0 ? 'text-red-600' : 'text-green-600'
                      }
                    >
                      气血{log.hp_change > 0 ? '+' : ''}
                      {log.hp_change}
                    </span>
                  )}
                  {log.anger_change !== 0 && (
                    <span
                      className={
                        log.anger_change < 0
                          ? 'text-blue-600'
                          : 'text-orange-600'
                      }
                    >
                      愤怒{log.anger_change > 0 ? '+' : ''}
                      {log.anger_change}
                    </span>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
