import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import OnboardingEnhanced from './pages/OnboardingEnhanced'
import Dashboard from './pages/Dashboard'
import Generate from './pages/Generate'
import Results from './pages/Results'
import ResultsAdvanced from './pages/ResultsAdvanced'
import History from './pages/History'
import LinkedIn from './pages/LinkedIn'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Home />} />
        {/* Use v2 (Enhanced) onboarding as the default */}
        <Route path="onboarding" element={<OnboardingEnhanced />} />
        <Route path="onboarding-v2" element={<Navigate to="/onboarding" replace />} />
        <Route path="dashboard/:brandId" element={<Dashboard />} />
        <Route path="generate/:brandId" element={<Generate />} />
        <Route path="results/:brandId" element={<Results />} />
        <Route path="results-advanced/:brandId" element={<ResultsAdvanced />} />
        <Route path="history/:brandId" element={<History />} />
        <Route path="linkedin/:brandId" element={<LinkedIn />} />
      </Route>
    </Routes>
  )
}

export default App
