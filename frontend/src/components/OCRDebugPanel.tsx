import { useCombatStore } from '@/stores/useCombatStore'

export default function OCRDebugPanel() {
  const ocrDebug = useCombatStore((s) => s.ocrDebug)
  const logs = useCombatStore((s) => s.logs)

  return (
    <div className="border-t border-border-gray p-3 bg-light-surface">
      <h3 className="text-xs font-semibold text-gray-500 mb-2">OCR 调试</h3>
      {ocrDebug ? (
        <div className="space-y-2 text-xs">
          {ocrDebug.popup_numbers.length > 0 && (
            <div>
              <span className="text-gray-400">弹出数字:</span>
              {ocrDebug.popup_numbers.map((n, i) => (
                <span
                  key={i}
                  className={`ml-2 font-mono ${n.value < 0 ? 'text-red-600' : 'text-green-600'}`}
                >
                  {n.unit_name}: {n.value > 0 ? '+' : ''}{n.value}
                </span>
              ))}
            </div>
          )}
          {ocrDebug.actions.length > 0 && (
            <div>
              <span className="text-gray-400">操作文字:</span>
              {ocrDebug.actions.map((a, i) => (
                <span key={i} className="ml-2 text-deep-navy">
                  {a.action_type === 'round' && `回合${a.round_num}`}
                  {a.action_type === 'skill' && `${a.unit_name || '?'}·${a.skill_name}`}
                  {a.action_type === 'damage_desc' && `伤${a.hp_value}`}
                  {a.action_type === 'heal_desc' && `治${a.hp_value}`}
                </span>
              ))}
            </div>
          )}
          <div className="text-gray-400">
            最新日志: {logs.length > 0 ? logs[logs.length - 1].description : '无'}
          </div>
        </div>
      ) : (
        <div className="text-gray-400 text-xs">等待 OCR 数据...</div>
      )}
    </div>
  )
}
