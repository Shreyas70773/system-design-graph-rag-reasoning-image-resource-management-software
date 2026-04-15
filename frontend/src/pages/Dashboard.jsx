import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { 
  Sparkles, Image, Palette, ShoppingBag, 
  Clock, ArrowRight, Loader2, Settings, Linkedin, Newspaper
} from 'lucide-react'
import { getBrand, getBrandProducts } from '../services/api'

export default function Dashboard() {
  const { brandId } = useParams()
  const [brand, setBrand] = useState(null)
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    loadBrandData()
  }, [brandId])
  
  const loadBrandData = async () => {
    try {
      const [brandData, productsData] = await Promise.all([
        getBrand(brandId),
        getBrandProducts(brandId).catch(() => ({ products: [] }))
      ])
      setBrand(brandData)
      setProducts(productsData.products || [])
    } catch (err) {
      console.error('Failed to load brand:', err)
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
  
  if (!brand) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Brand not found</h2>
        <Link to="/" className="text-primary-600 hover:underline">Go back home</Link>
      </div>
    )
  }
  
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{brand.name}</h1>
          {brand.tagline && (
            <p className="text-gray-600 mt-1">{brand.tagline}</p>
          )}
          <p className="text-sm text-gray-500 mt-2">{brand.website}</p>
        </div>
        
        {brand.logo_url && (
          <img 
            src={brand.logo_url} 
            alt="Logo"
            className="w-20 h-20 object-contain bg-white rounded-lg border p-2"
          />
        )}
      </div>
      
      {/* Quick Actions */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link 
          to={`/generate/${brandId}`}
          className="card hover:shadow-lg transition-shadow group"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center group-hover:bg-primary-200 transition-colors">
              <Sparkles className="w-6 h-6 text-primary-600" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900">Generate Images</h3>
              <p className="text-sm text-gray-500">Create visuals & copy</p>
            </div>
            <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-primary-600" />
          </div>
        </Link>
        
        <Link 
          to={`/linkedin/${brandId}`}
          className="card hover:shadow-lg transition-shadow group border-2 border-[#0077B5]/20"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-[#0077B5]/10 rounded-lg flex items-center justify-center group-hover:bg-[#0077B5]/20 transition-colors">
              <Linkedin className="w-6 h-6 text-[#0077B5]" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900">LinkedIn Posts</h3>
              <p className="text-sm text-gray-500">News & thought leadership</p>
            </div>
            <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-[#0077B5]" />
          </div>
        </Link>
        
        <Link 
          to={`/history/${brandId}`}
          className="card hover:shadow-lg transition-shadow group"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center group-hover:bg-gray-200 transition-colors">
              <Clock className="w-6 h-6 text-gray-600" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900">View History</h3>
              <p className="text-sm text-gray-500">Past generations</p>
            </div>
            <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-gray-600" />
          </div>
        </Link>
        
        <Link 
          to={`/onboarding`}
          state={{ websiteUrl: brand.website }}
          className="card hover:shadow-lg transition-shadow group"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center group-hover:bg-gray-200 transition-colors">
              <Settings className="w-6 h-6 text-gray-600" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900">Update Brand</h3>
              <p className="text-sm text-gray-500">Re-scrape & edit</p>
            </div>
            <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-gray-600" />
          </div>
        </Link>
      </div>
      
      {/* Brand Details */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Colors */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Palette className="w-5 h-5 text-primary-600" />
            <h3 className="font-semibold text-gray-900">Brand Colors</h3>
          </div>
          
          {brand.colors?.length > 0 ? (
            <div className="flex flex-wrap gap-3">
              {brand.colors.map((color, i) => (
                <div key={i} className="text-center">
                  <div 
                    className="w-14 h-14 rounded-lg border shadow-sm"
                    style={{ backgroundColor: color.hex || color }}
                  />
                  <span className="text-xs text-gray-500 mt-1 block">
                    {color.hex || color}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No colors extracted</p>
          )}
        </div>
        
        {/* Products */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <ShoppingBag className="w-5 h-5 text-primary-600" />
            <h3 className="font-semibold text-gray-900">Products ({products.length})</h3>
          </div>
          
          {products.length > 0 ? (
            <ul className="space-y-2">
              {products.slice(0, 5).map((product, i) => (
                <li key={i} className="text-sm text-gray-700">
                  • {product.name} {product.price && <span className="text-gray-500">({product.price})</span>}
                </li>
              ))}
              {products.length > 5 && (
                <li className="text-sm text-gray-500">...and {products.length - 5} more</li>
              )}
            </ul>
          ) : (
            <p className="text-gray-500 text-sm">No products added yet</p>
          )}
        </div>
      </div>
    </div>
  )
}
