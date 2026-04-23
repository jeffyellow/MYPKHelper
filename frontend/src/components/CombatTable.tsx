import { useCombatStore } from '@/stores/useCombatStore'
import { useWebSocket } from '@/hooks/useWebSocket'

const HEADERS = [
  '名字',
  '门派',
  '最大气血',
  '当前气血',
  '护盾值',
  '当前愤怒',
  '叶障护盾值',
]

export default function CombatTable() {
  const units = useCombatStore((s) => s.units)
  const selectedId = useCombatStore((s) => s.selected_unit_id)
  const setSelected = useCombatStore((s) => s.setSelectedUnit)
  const { sendManualUpdate } = useWebSocket()

  return (
    <div className="flex-1 overflow-auto p-4">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border-gray">
            {HEADERS.map((h) => (
              <th
                key={h}
                className="text-left py-3 px-4 font-medium text-deep-navy"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {units.length === 0 ? (
            <tr>
              <td colSpan={HEADERS.length} className="py-8 text-center text-gray-400">
                暂无战斗数据，请点击"战斗开始"
              </td>
            </tr>
          ) : (
            units.map((unit) => (
              <tr
                key={unit.id}
                onClick={() => setSelected(unit.id)}
                className={`border-b border-border-gray cursor-pointer transition-colors hover:bg-light-surface ${
                  selectedId === unit.id ? 'bg-blue-50' : ''
                }`}
              >
                <td className="py-3 px-4">{unit.name}</td>
                <td className="py-3 px-4">{unit.faction}</td>
                <td className="py-3 px-4">{unit.max_hp}</td>
                <td className="py-3 px-4">{unit.current_hp}</td>
                <td className="py-3 px-4">{unit.shield}</td>
                <td className="py-3 px-4">{unit.current_anger}</td>
                <td className="py-3 px-4">
                  <input
                    type="number"
                    className="w-20 px-2 py-1 border border-border-gray rounded text-right"
                    value={unit.ye_zhang_shield}
                    onChange={(e) => {
                      const val = parseInt(e.target.value) || 0
                      sendManualUpdate(unit.id, 'set_ye_zhang', val)
                    }}
                    onClick={(e) => e.stopPropagation()}
                  />
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
