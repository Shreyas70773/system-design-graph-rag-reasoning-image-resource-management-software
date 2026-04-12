import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Clock, Image, ArrowLeft, Loader2, Sparkles } from 'lucide-react'
import { getGenerationHistory, getBrand } from '../services/api'

export default function History() {
  const { brandId } = useParams()
  const [brand, setBrand] = useState(null)
  const [generations, setGenerations] = useState([])
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    loadData()
  }, [brandId])
  
  const loadData = async () => {
    try {
      const [brandData, historyData] = await Promise.all([
        getBrand(brandId),
        getGenerationHistory(brandId, 20)
      ])
      setBrand(brandData)
      setGenerations(historyData)
    } catch (err) {
      console.error('Failed to load history:', err)
    } finally {
      setLoading(false)
    }
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }
  
  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link 
          to={`/dashboard/${brandId}`}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-600" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">Generation History</h1>
          <p className="text-gray-600 text-sm">{brand?.name}</p>
        </div>
        <Link to={`/generate/${brandId}`} className="btn-primary flex items-center gap-2">
          <Sparkles className="w-4 h-4" />
          New Generation
        </Link>
      </div>
      
      {/* History List */}
      {generations.length === 0 ? (
        <div className="card text-center py-12">
          <Clock className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No generations yet</h3>
          <p className="text-gray-600 mb-4">Start creating content for your brand</p>
          <Link to={`/generate/${brandId}`} className="btn-primary inline-flex items-center gap-2">
            <Sparkles className="w-4 h-4" />
            Generate Content
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {generations.map((gen) => (
            <div key={gen.id} className="card hover:shadow-lg transition-shadow">
              <div className="flex gap-4">
                {/* Thumbnail */}
                <div className="w-24 h-24 rounded-lg overflow-hidden bg-gray-100 flex-shrink-0">
                  {gen.image_url ? (
                    <img 
                      src={gen.image_url}
                      alt="Generated"
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <Image className="w-8 h-8 text-gray-300" />
                    </div>
                  )}
                </div>
                
                {/* Details */}
                <div className="flex-1 min-w-0">
                  <p className="text-gray-900 font-medium truncate mb-1">
                    "{gen.prompt}"
                  </p>
                  
                  {gen.headline && (
                    <p className="text-sm text-gray-600 truncate mb-2">
                      {gen.headline}
                    </p>
                  )}
                  
                  <div className="flex items-center gap-4 text-sm">
                    <span className={`font-medium ${
                      gen.brand_score >= 0.7 ? 'text-green-600' : 
                      gen.brand_score >= 0.5 ? 'text-amber-600' : 'text-red-600'
                    }`}>
                      {Math.round(gen.brand_score * 100)}% match
                    </span>
                    
                    <span className="text-gray-400">
                      {formatDate(gen.created_at)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function formatDate(dateString) {
  if (!dateString) return ''
  
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)
  
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  
  return date.toLocaleDateString()
}
