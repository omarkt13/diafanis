import { Route, Routes } from 'react-router-dom'

import { FundPage } from '@/pages/FundPage'
import { Home } from '@/pages/Home'
import { ProviderPage } from '@/pages/ProviderPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/providers/:slug" element={<ProviderPage />} />
      <Route path="/funds/:id" element={<FundPage />} />
    </Routes>
  )
}

export default App
