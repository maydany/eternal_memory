import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import ChatPage from './pages/ChatPage'
import VaultPage from './pages/VaultPage'
import SettingsPage from './pages/SettingsPage'
import DatabasePage from './pages/DatabasePage'
import TimelinePage from './pages/TimelinePage'
import MetricsPage from './pages/MetricsPage'


function App() {
  return (
    <div className="h-full dark">
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<ChatPage />} />
          <Route path="vault" element={<VaultPage />} />
          <Route path="database" element={<DatabasePage />} />
          <Route path="timeline" element={<TimelinePage />} />
          <Route path="metrics" element={<MetricsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </div>
  )
}

export default App
