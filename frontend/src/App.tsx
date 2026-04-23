import MonitorBar from '@/components/MonitorBar'
import CombatTable from '@/components/CombatTable'
import ActionPanel from '@/components/ActionPanel'
import HistoryPage from '@/components/HistoryPage'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useCombatStore } from '@/stores/useCombatStore'

function App() {
  useWebSocket()
  const currentView = useCombatStore((s) => s.currentView)

  if (currentView === 'history') {
    return (
      <div className="h-screen bg-light-surface">
        <HistoryPage />
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-light-surface">
      <MonitorBar />
      <div className="flex flex-1 overflow-hidden">
        <CombatTable />
        <ActionPanel />
      </div>
    </div>
  )
}

export default App
