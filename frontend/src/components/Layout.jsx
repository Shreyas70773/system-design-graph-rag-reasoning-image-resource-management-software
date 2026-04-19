import { useEffect } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { Sparkles, Home, FlaskConical, Layers, Wand2 } from 'lucide-react'
import { setActiveBrandId } from '../services/brandSession'

export default function Layout() {
  const location = useLocation()

  useEffect(() => {
    const match = location.pathname.match(/^\/(dashboard|generate|results|results-advanced|history|linkedin)\/([^/]+)/)
    const routeBrandId = match?.[2]
    if (routeBrandId) {
      setActiveBrandId(routeBrandId)
    }
  }, [location.pathname])
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2">
              <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900">BrandGen</span>
            </Link>
            
            {/* Navigation */}
            <nav className="flex items-center gap-4">
              <Link 
                to="/" 
                className={`flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  location.pathname === '/' 
                    ? 'bg-primary-50 text-primary-700' 
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <Home className="w-4 h-4" />
                Home
              </Link>

              <Link
                to="/research"
                className={`flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  location.pathname.startsWith('/research')
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <FlaskConical className="w-4 h-4" />
                Research Lab
              </Link>

              <Link
                to="/v2"
                className={`flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  location.pathname.startsWith('/v2')
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <Layers className="w-4 h-4" />
                Layer Studio
              </Link>

              <Link
                to="/capstone"
                className={`flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  location.pathname.startsWith('/capstone')
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <Wand2 className="w-4 h-4" />
                Capstone Studio
              </Link>
            </nav>
          </div>
        </div>
      </header>
      
      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
      
      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-gray-500 text-sm">
            Brand-Aligned Content Generation Platform — Capstone Project
          </p>
        </div>
      </footer>
    </div>
  )
}
