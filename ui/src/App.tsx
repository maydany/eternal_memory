import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import ChatPage from './pages/ChatPage'
import VaultPage from './pages/VaultPage'
import SettingsPage from './pages/SettingsPage'

function App() {
  return (
    <div className="h-full dark">
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<ChatPage />} />
          <Route path="vault" element={<VaultPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </div>
  )
}

export default App
