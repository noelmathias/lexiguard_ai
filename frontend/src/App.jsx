import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout           from './components/Layout'
import Chat             from './pages/Chat'
import ContractAnalysis from './pages/ContractAnalysis'
import Comparison       from './pages/Comparison'
import DocumentGen      from './pages/DocumentGen'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index               element={<Chat />} />
          <Route path="contract"     element={<ContractAnalysis />} />
          <Route path="compare"      element={<Comparison />} />
          <Route path="generate"     element={<DocumentGen />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}