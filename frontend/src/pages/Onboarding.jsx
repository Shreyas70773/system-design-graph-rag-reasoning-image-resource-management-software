import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { 
  Globe, Loader2, CheckCircle, AlertCircle, 
  Image, Palette, ShoppingBag, ArrowRight, 
  Sparkles, Upload, RefreshCw, Link, FileText,
  Trash2, Edit2, X, Plus, Type, Layout, User
} from 'lucide-react'
import { scrapeBrand, checkLogoQuality, generateAILogo, parseProductsFromText, smartScrapeProduct, getAvailableFonts, getTextLayouts, addBrandColor, addBrandProduct, addBrandCharacter } from '../services/api'
import { setActiveBrandId } from '../services/brandSession'

const STEPS = ['scrape', 'review', 'products', 'style', 'complete']

// Font preview styles
const FONT_PREVIEWS = {
  montserrat: "font-['Montserrat',sans-serif]",
  playfair: "font-['Playfair_Display',serif]",
  roboto: "font-['Roboto',sans-serif]",
  poppins: "font-['Poppins',sans-serif]",
  oswald: "font-['Oswald',sans-serif]",
  lora: "font-['Lora',serif]",
  raleway: "font-['Raleway',sans-serif]",
  bebas: "font-['Bebas_Neue',sans-serif]",
}

export default function Onboarding() {
  const location = useLocation()
  const navigate = useNavigate()
  const initialUrl = location.state?.websiteUrl || ''
  
  const [currentStep, setCurrentStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  // Brand data
  const [websiteUrl, setWebsiteUrl] = useState(initialUrl)
  const [brandData, setBrandData] = useState(null)
  const [logoQuality, setLogoQuality] = useState(null)
  const [productText, setProductText] = useState('')
  const [productUrls, setProductUrls] = useState('') // Support multiple URLs (one per line)
  const [productInputMode, setProductInputMode] = useState('text') // 'text', 'url', or 'manual'
  const [products, setProducts] = useState([])
  const [editingProduct, setEditingProduct] = useState(null) // index of product being edited
  const [editForm, setEditForm] = useState({ name: '', price: '', category: '', description: '', image_url: '' })
  const [scrapingProgress, setScrapingProgress] = useState({ current: 0, total: 0, status: '' })
  
  // Style preferences
  const [availableFonts, setAvailableFonts] = useState([])
  const [textLayouts, setTextLayouts] = useState([])
  const [selectedFont, setSelectedFont] = useState('montserrat')
  const [selectedLayout, setSelectedLayout] = useState('bottom_centered')
  
  // Color editing
  const [editingColors, setEditingColors] = useState(false)
  const [newColorHex, setNewColorHex] = useState('#')
  const [newColorName, setNewColorName] = useState('')
  const [newColorRole, setNewColorRole] = useState('accent')
  
  // Logo editing
  const [editingLogo, setEditingLogo] = useState(false)
  const [newLogoUrl, setNewLogoUrl] = useState('')
  
  // Character/person for PuLID
  const [characters, setCharacters] = useState([])
  const [newCharacterName, setNewCharacterName] = useState('')
  const [newCharacterImageUrl, setNewCharacterImageUrl] = useState('')
  const [newCharacterBodyType, setNewCharacterBodyType] = useState('average')

  const resolveBrandId = (data) => {
    const candidate = data?.id || data?.brand_id || data?.brandId
    return String(candidate || '').trim()
  }
  
  // Load fonts and layouts when reaching style step
  useEffect(() => {
    if (currentStep === 3) {
      loadStyleOptions()
    }
  }, [currentStep])
  
  const loadStyleOptions = async () => {
    try {
      const [fonts, layouts] = await Promise.all([
        getAvailableFonts().catch(() => []),
        getTextLayouts().catch(() => [])
      ])
      setAvailableFonts(fonts)
      setTextLayouts(layouts)
    } catch (e) {
      console.log('Failed to load style options:', e)
    }
  }
  
  // Auto-scrape if URL provided
  useEffect(() => {
    if (initialUrl && !brandData) {
      handleScrape()
    }
  }, [])
  
  // Step 1: Scrape website
  const handleScrape = async () => {
    if (!websiteUrl.trim()) return
    
    setLoading(true)
    setError(null)
    
    try {
      const data = await scrapeBrand(websiteUrl)
      const resolvedBrandId = resolveBrandId(data)

      if (!resolvedBrandId) {
        throw new Error('Brand ID was not returned from onboarding. Please retry website scan.')
      }

      setBrandData({ ...data, id: resolvedBrandId })
      setActiveBrandId(resolvedBrandId)
      
      // Check logo quality if logo exists
      if (data.logo?.url && resolvedBrandId) {
        try {
          const quality = await checkLogoQuality(resolvedBrandId)
          setLogoQuality(quality)
        } catch (e) {
          console.log('Logo quality check failed:', e)
        }
      }
      
      setCurrentStep(1) // Move to review step
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }
  
  // Generate AI logo
  const handleGenerateLogo = async () => {
    if (!brandData?.id) return
    
    setLoading(true)
    setError(null)
    
    try {
      const result = await generateAILogo(brandData.id)
      setBrandData(prev => ({
        ...prev,
        logo: { ...prev.logo, url: result.logo_url }
      }))
      setLogoQuality({ ...logoQuality, quality_score: 0.9, needs_enhancement: false })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }
  
  // Parse products
  const handleParseProducts = async () => {
    if (!productText.trim() || !brandData?.id) return
    
    setLoading(true)
    setError(null)
    
    try {
      const result = await parseProductsFromText(brandData.id, productText)
      setProducts(prev => [...prev, ...result.products])
      setProductText('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }
  
  // Scrape product from URL(s) - supports multiple URLs
  const handleScrapeProductUrls = async () => {
    if (!productUrls.trim() || !brandData?.id) return
    
    // Parse URLs (one per line, filter empty lines)
    const urls = productUrls
      .split('\n')
      .map(url => url.trim())
      .filter(url => url && (url.startsWith('http://') || url.startsWith('https://')))
    
    if (urls.length === 0) {
      setError('Please enter valid URLs (starting with http:// or https://)')
      return
    }
    
    setLoading(true)
    setError(null)
    setScrapingProgress({ current: 0, total: urls.length, status: 'Starting...' })
    
    const newProducts = []
    const errors = []
    
    for (let i = 0; i < urls.length; i++) {
      const url = urls[i]
      setScrapingProgress({ 
        current: i + 1, 
        total: urls.length, 
        status: `Scraping ${i + 1}/${urls.length}: ${url.substring(0, 50)}...` 
      })
      
      try {
        const product = await smartScrapeProduct(brandData.id, url)
        if (product && product.name) {
          newProducts.push({
            name: product.name,
            price: product.price,
            category: product.category,
            description: product.summary || product.description,
            image_url: product.image_url
          })
        } else {
          errors.push(`Could not extract from: ${url}`)
        }
      } catch (err) {
        errors.push(`Failed: ${url} - ${err.message}`)
      }
    }
    
    if (newProducts.length > 0) {
      setProducts(prev => [...prev, ...newProducts])
      setProductUrls('')
    }
    
    if (errors.length > 0) {
      setError(`Added ${newProducts.length} products. Errors:\n${errors.join('\n')}`)
    }
    
    setScrapingProgress({ current: 0, total: 0, status: '' })
    setLoading(false)
  }
  
  // Continue to style step
  const handleContinueToStyle = () => {
    setCurrentStep(3)
  }
  
  // Continue to complete from style
  const handleContinueToComplete = () => {
    // Store font preference in brandData for later use
    setBrandData(prev => ({
      ...prev,
      font_id: selectedFont,
      text_layout: selectedLayout
    }))
    setCurrentStep(4)
  }
  
  // Remove a product from the list
  const handleRemoveProduct = (index) => {
    setProducts(prev => prev.filter((_, i) => i !== index))
  }
  
  // Start editing a product
  const handleEditProduct = (index) => {
    const product = products[index]
    setEditForm({
      name: product.name || '',
      price: product.price || '',
      category: product.category || '',
      description: product.description || '',
      image_url: product.image_url || ''
    })
    setEditingProduct(index)
  }
  
  // Save product edits
  const handleSaveEdit = () => {
    if (!editForm.name.trim()) return
    
    setProducts(prev => prev.map((p, i) => 
      i === editingProduct ? { ...editForm } : p
    ))
    setEditingProduct(null)
    setEditForm({ name: '', price: '', category: '', description: '', image_url: '' })
  }
  
  // Cancel editing
  const handleCancelEdit = () => {
    setEditingProduct(null)
    setEditForm({ name: '', price: '', category: '', description: '', image_url: '' })
  }
  
  // Add manual product
  const handleAddManualProduct = () => {
    if (!editForm.name.trim()) return
    
    setProducts(prev => [...prev, { ...editForm }])
    setEditForm({ name: '', price: '', category: '', description: '', image_url: '' })
  }
  
  // Update product image URL
  const handleUpdateProductImage = (index, newImageUrl) => {
    setProducts(prev => prev.map((p, i) => 
      i === index ? { ...p, image_url: newImageUrl } : p
    ))
  }
  
  // Remove product image
  const handleRemoveProductImage = (index) => {
    setProducts(prev => prev.map((p, i) => 
      i === index ? { ...p, image_url: null } : p
    ))
  }
  
  // Skip products
  const handleSkipProducts = () => {
    setCurrentStep(3) // Go to style step
  }
  
  // Go to generation - save all data to Brand DNA first
  const handleComplete = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const resolvedBrandId = resolveBrandId(brandData)
      if (!resolvedBrandId) {
        throw new Error('Brand ID is missing. Please retry onboarding scan.')
      }

      setActiveBrandId(resolvedBrandId)

      // Save colors to Brand DNA
      for (const color of (brandData.colors || [])) {
        try {
          await addBrandColor(resolvedBrandId, {
            hex: color.hex,
            name: color.name || color.hex,
            role: color.role || 'accent'
          })
        } catch (e) {
          console.log('Color may already exist:', e)
        }
      }
      
      // Save products to Brand DNA
      for (const product of products) {
        try {
          await addBrandProduct(resolvedBrandId, {
            name: product.name,
            category: product.category || 'general',
            image_url: product.image_url || '',
            description: product.description || ''
          })
        } catch (e) {
          console.log('Product save error:', e)
        }
      }
      
      // Save characters to Brand DNA
      for (const char of characters) {
        try {
          await addBrandCharacter(resolvedBrandId, {
            name: char.name,
            reference_image_url: char.reference_image_url,
            body_type: char.body_type || 'average'
          })
        } catch (e) {
          console.log('Character save error:', e)
        }
      }
      
      // Navigate to generate page
      navigate(`/generate/${resolvedBrandId}`, {
        state: {
          fontId: selectedFont,
          textLayout: selectedLayout
        }
      })
    } catch (err) {
      setError('Failed to save brand data: ' + err.message)
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <div className="max-w-3xl mx-auto">
      {/* Progress Steps */}
      <div className="flex items-center justify-between mb-8">
        {['Website', 'Review', 'Products', 'Style', 'Complete'].map((step, index) => (
          <div key={step} className="flex items-center">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              index <= currentStep 
                ? 'bg-primary-600 text-white' 
                : 'bg-gray-200 text-gray-600'
            }`}>
              {index < currentStep ? <CheckCircle className="w-5 h-5" /> : index + 1}
            </div>
            <span className={`ml-2 text-sm ${index <= currentStep ? 'text-gray-900 font-medium' : 'text-gray-500'}`}>
              {step}
            </span>
            {index < 3 && (
              <div className={`w-16 h-0.5 mx-4 ${index < currentStep ? 'bg-primary-600' : 'bg-gray-200'}`} />
            )}
          </div>
        ))}
      </div>
      
      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-medium text-red-800">Error</h4>
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        </div>
      )}
      
      {/* Step Content */}
      <div className="card">
        {/* Step 0: Enter URL */}
        {currentStep === 0 && (
          <div className="space-y-6">
            <div className="text-center">
              <Globe className="w-12 h-12 text-primary-600 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Enter Your Website</h2>
              <p className="text-gray-600">We'll extract your brand information automatically</p>
            </div>
            
            <div>
              <label className="label">Website URL</label>
              <input
                type="url"
                value={websiteUrl}
                onChange={(e) => setWebsiteUrl(e.target.value)}
                placeholder="https://www.yourcompany.com"
                className="input"
                disabled={loading}
              />
            </div>
            
            <button 
              onClick={handleScrape} 
              disabled={loading || !websiteUrl.trim()}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Analyzing website...
                </>
              ) : (
                <>
                  Analyze Website
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
          </div>
        )}
        
        {/* Step 1: Review Brand Data */}
        {currentStep === 1 && brandData && (
          <div className="space-y-6">
            <div className="text-center">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Brand Data Extracted</h2>
              <p className="text-gray-600">Review and customize your brand information</p>
            </div>
            
            {/* Brand Info */}
            <div className="bg-gray-50 rounded-lg p-4 space-y-4">
              <div>
                <span className="text-sm text-gray-500">Company Name</span>
                <p className="font-semibold text-gray-900">{brandData.company_name}</p>
              </div>
              
              {brandData.tagline && (
                <div>
                  <span className="text-sm text-gray-500">Tagline</span>
                  <p className="text-gray-700">{brandData.tagline}</p>
                </div>
              )}
              
              {/* Logo Section - Enhanced */}
              <div className="border-t pt-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">Logo</span>
                  <button 
                    onClick={() => setEditingLogo(!editingLogo)}
                    className="text-xs text-primary-600 hover:text-primary-700"
                  >
                    {editingLogo ? 'Cancel' : 'Edit Logo'}
                  </button>
                </div>
                
                <div className="flex items-start gap-4">
                  {brandData.logo?.url ? (
                    <img 
                      src={brandData.logo.url} 
                      alt="Logo" 
                      className="w-24 h-24 object-contain bg-white border rounded-lg p-2"
                    />
                  ) : (
                    <div className="w-24 h-24 bg-gray-200 rounded-lg flex items-center justify-center">
                      <Image className="w-8 h-8 text-gray-400" />
                    </div>
                  )}
                  
                  <div className="flex-1">
                    {logoQuality && (
                      <div className="mb-2">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-medium">Quality Score:</span>
                          <span className={`text-sm font-bold ${
                            logoQuality.quality_score >= 0.7 ? 'text-green-600' : 'text-orange-500'
                          }`}>
                            {(logoQuality.quality_score * 100).toFixed(0)}%
                          </span>
                        </div>
                        {logoQuality.needs_enhancement && (
                          <p className="text-sm text-orange-600">Logo quality is low. Consider enhancing.</p>
                        )}
                      </div>
                    )}
                    
                    {/* Logo Edit Form */}
                    {editingLogo && (
                      <div className="space-y-2 mb-3">
                        <input
                          type="url"
                          value={newLogoUrl}
                          onChange={(e) => setNewLogoUrl(e.target.value)}
                          placeholder="Paste new logo URL..."
                          className="input text-sm"
                        />
                        <button 
                          onClick={() => {
                            if (newLogoUrl) {
                              setBrandData(prev => ({ ...prev, logo: { ...prev.logo, url: newLogoUrl } }))
                              setNewLogoUrl('')
                              setEditingLogo(false)
                            }
                          }}
                          disabled={!newLogoUrl}
                          className="btn-primary text-sm py-1.5 w-full"
                        >
                          Update Logo
                        </button>
                      </div>
                    )}
                    
                    <div className="flex gap-2 flex-wrap">
                      <button 
                        onClick={handleGenerateLogo}
                        disabled={loading}
                        className="btn-outline text-sm py-1.5 flex items-center gap-1"
                      >
                        <Sparkles className="w-4 h-4" />
                        Generate AI Logo
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Colors Section - Enhanced with editing */}
              <div className="border-t pt-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">Brand Colors</span>
                  <button 
                    onClick={() => setEditingColors(!editingColors)}
                    className="text-xs text-primary-600 hover:text-primary-700"
                  >
                    {editingColors ? 'Done' : 'Edit Colors'}
                  </button>
                </div>
                
                <div className="flex gap-2 flex-wrap">
                  {brandData.colors?.map((color, i) => (
                    <div key={i} className="text-center relative group">
                      <div 
                        className="w-12 h-12 rounded-lg border shadow-sm"
                        style={{ backgroundColor: color.hex }}
                      />
                      <span className="text-xs text-gray-500 mt-1 block">{color.hex}</span>
                      {editingColors && (
                        <button
                          onClick={() => {
                            setBrandData(prev => ({
                              ...prev,
                              colors: prev.colors.filter((_, idx) => idx !== i)
                            }))
                          }}
                          className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center text-xs"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  ))}
                  
                  {editingColors && (
                    <button
                      onClick={() => setNewColorHex('#')}
                      className="w-12 h-12 rounded-lg border-2 border-dashed border-gray-300 flex items-center justify-center text-gray-400 hover:border-primary-400 hover:text-primary-500"
                    >
                      <Plus className="w-5 h-5" />
                    </button>
                  )}
                </div>
                
                {/* Add Color Form */}
                {editingColors && newColorHex === '#' && (
                  <div className="mt-3 p-3 bg-white rounded-lg border space-y-2">
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="label text-xs">Hex Code</label>
                        <input
                          type="text"
                          value={newColorHex}
                          onChange={(e) => setNewColorHex(e.target.value)}
                          placeholder="#FF5733"
                          className="input text-sm"
                        />
                      </div>
                      <div>
                        <label className="label text-xs">Color Name</label>
                        <input
                          type="text"
                          value={newColorName}
                          onChange={(e) => setNewColorName(e.target.value)}
                          placeholder="Brand Orange"
                          className="input text-sm"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="label text-xs">Role</label>
                      <select
                        value={newColorRole}
                        onChange={(e) => setNewColorRole(e.target.value)}
                        className="input text-sm"
                      >
                        <option value="primary">Primary</option>
                        <option value="secondary">Secondary</option>
                        <option value="accent">Accent</option>
                        <option value="background">Background</option>
                      </select>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => {
                          if (newColorHex && newColorHex !== '#') {
                            setBrandData(prev => ({
                              ...prev,
                              colors: [...(prev.colors || []), { hex: newColorHex, name: newColorName, role: newColorRole }]
                            }))
                            setNewColorHex('#')
                            setNewColorName('')
                            setNewColorRole('accent')
                          }
                        }}
                        disabled={!newColorHex || newColorHex === '#'}
                        className="btn-primary text-sm py-1.5 flex-1"
                      >
                        Add Color
                      </button>
                      <button
                        onClick={() => setNewColorHex('')}
                        className="btn-secondary text-sm py-1.5"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            <button 
              onClick={() => setCurrentStep(2)}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              Continue to Products
              <ArrowRight className="w-5 h-5" />
            </button>
          </div>
        )}
        
        {/* Step 2: Add Products */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <div className="text-center">
              <ShoppingBag className="w-12 h-12 text-primary-600 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Add Your Products</h2>
              <p className="text-gray-600">Add products via text description or product page URL</p>
            </div>
            
            {/* Input Mode Toggle */}
            <div className="flex gap-2 bg-gray-100 p-1 rounded-lg">
              <button
                type="button"
                onClick={() => setProductInputMode('text')}
                className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                  productInputMode === 'text'
                    ? 'bg-white text-primary-700 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <FileText className="w-4 h-4" />
                Text
              </button>
              <button
                type="button"
                onClick={() => setProductInputMode('url')}
                className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                  productInputMode === 'url'
                    ? 'bg-white text-primary-700 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <Link className="w-4 h-4" />
                URL
              </button>
              <button
                type="button"
                onClick={() => setProductInputMode('manual')}
                className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                  productInputMode === 'manual'
                    ? 'bg-white text-primary-700 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <Plus className="w-4 h-4" />
                Manual
              </button>
            </div>
            
            {/* Text Input Mode */}
            {productInputMode === 'text' && (
              <div>
                <label className="label">Describe your products or services</label>
                <textarea
                  value={productText}
                  onChange={(e) => setProductText(e.target.value)}
                  placeholder="Example: We sell coffee ($15), cold brew ($5), and pastries ($3-8). We also offer catering services for events."
                  className="input min-h-[120px]"
                  disabled={loading}
                />
                <p className="text-xs text-gray-500 mt-1">
                  AI will extract product names, prices, and categories automatically
                </p>
                <button 
                  onClick={handleParseProducts}
                  disabled={loading || !productText.trim()}
                  className="btn-primary w-full mt-3 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Parsing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Extract Products
                    </>
                  )}
                </button>
              </div>
            )}
            
            {/* URL Input Mode - Multiple URLs */}
            {productInputMode === 'url' && (
              <div>
                <label className="label">Product Page URLs (one per line)</label>
                <textarea
                  value={productUrls}
                  onChange={(e) => setProductUrls(e.target.value)}
                  placeholder="https://store.example.com/product/item-1&#10;https://store.example.com/product/item-2&#10;https://store.example.com/product/item-3"
                  className="input min-h-[120px] font-mono text-sm"
                  disabled={loading}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Enter multiple URLs (one per line). AI will scrape each page and extract product details.
                </p>
                
                {/* Progress indicator */}
                {scrapingProgress.total > 0 && (
                  <div className="mt-3 p-3 bg-blue-50 rounded-lg">
                    <div className="flex items-center gap-2 text-sm text-blue-700">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>{scrapingProgress.status}</span>
                    </div>
                    <div className="mt-2 h-2 bg-blue-200 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-blue-600 transition-all duration-300"
                        style={{ width: `${(scrapingProgress.current / scrapingProgress.total) * 100}%` }}
                      />
                    </div>
                  </div>
                )}
                
                <button 
                  onClick={handleScrapeProductUrls}
                  disabled={loading || !productUrls.trim()}
                  className="btn-primary w-full mt-3 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Scraping {scrapingProgress.current}/{scrapingProgress.total}...
                    </>
                  ) : (
                    <>
                      <Globe className="w-4 h-4" />
                      Scrape Products
                    </>
                  )}
                </button>
              </div>
            )}
            
            {/* Manual Input Mode */}
            {productInputMode === 'manual' && (
              <div className="space-y-3">
                <div>
                  <label className="label">Product Name *</label>
                  <input
                    type="text"
                    value={editForm.name}
                    onChange={(e) => setEditForm(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., Premium Coffee Blend"
                    className="input"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="label">Price</label>
                    <input
                      type="text"
                      value={editForm.price}
                      onChange={(e) => setEditForm(prev => ({ ...prev, price: e.target.value }))}
                      placeholder="e.g., $15.99"
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="label">Category</label>
                    <input
                      type="text"
                      value={editForm.category}
                      onChange={(e) => setEditForm(prev => ({ ...prev, category: e.target.value }))}
                      placeholder="e.g., Beverages"
                      className="input"
                    />
                  </div>
                </div>
                <div>
                  <label className="label">Image URL</label>
                  <input
                    type="url"
                    value={editForm.image_url}
                    onChange={(e) => setEditForm(prev => ({ ...prev, image_url: e.target.value }))}
                    placeholder="https://example.com/product-image.jpg"
                    className="input"
                  />
                </div>
                <div>
                  <label className="label">Description</label>
                  <textarea
                    value={editForm.description}
                    onChange={(e) => setEditForm(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Brief product description..."
                    className="input min-h-[60px]"
                  />
                </div>
                <button 
                  onClick={handleAddManualProduct}
                  disabled={!editForm.name.trim()}
                  className="btn-primary w-full flex items-center justify-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  Add Product
                </button>
              </div>
            )}
            
            {/* Products List */}
            {products.length > 0 && (
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-800 mb-3">Added Products ({products.length}):</h4>
                <ul className="space-y-3">
                  {products.map((p, i) => (
                    <li key={i} className="bg-white rounded-lg p-3 border border-gray-200">
                      {editingProduct === i ? (
                        // Edit mode
                        <div className="space-y-3">
                          <div>
                            <label className="label text-xs">Product Name *</label>
                            <input
                              type="text"
                              value={editForm.name}
                              onChange={(e) => setEditForm(prev => ({ ...prev, name: e.target.value }))}
                              className="input text-sm"
                            />
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <label className="label text-xs">Price</label>
                              <input
                                type="text"
                                value={editForm.price}
                                onChange={(e) => setEditForm(prev => ({ ...prev, price: e.target.value }))}
                                className="input text-sm"
                              />
                            </div>
                            <div>
                              <label className="label text-xs">Category</label>
                              <input
                                type="text"
                                value={editForm.category}
                                onChange={(e) => setEditForm(prev => ({ ...prev, category: e.target.value }))}
                                className="input text-sm"
                              />
                            </div>
                          </div>
                          <div>
                            <label className="label text-xs">Image URL</label>
                            <input
                              type="url"
                              value={editForm.image_url}
                              onChange={(e) => setEditForm(prev => ({ ...prev, image_url: e.target.value }))}
                              className="input text-sm"
                              placeholder="Paste image URL or leave empty"
                            />
                          </div>
                          <div>
                            <label className="label text-xs">Description</label>
                            <textarea
                              value={editForm.description}
                              onChange={(e) => setEditForm(prev => ({ ...prev, description: e.target.value }))}
                              className="input text-sm min-h-[50px]"
                            />
                          </div>
                          <div className="flex gap-2">
                            <button onClick={handleSaveEdit} className="btn-primary text-sm py-1.5 flex-1">
                              Save
                            </button>
                            <button onClick={handleCancelEdit} className="btn-secondary text-sm py-1.5 flex-1">
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        // View mode
                        <div className="flex items-start gap-3">
                          <div className="relative group">
                            {p.image_url ? (
                              <div className="relative">
                                <img src={p.image_url} alt={p.name} className="w-16 h-16 object-cover rounded" />
                                <button
                                  onClick={() => handleRemoveProductImage(i)}
                                  className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                                  title="Remove image"
                                >
                                  <X className="w-3 h-3" />
                                </button>
                              </div>
                            ) : (
                              <div className="w-16 h-16 bg-gray-100 rounded flex items-center justify-center">
                                <Image className="w-6 h-6 text-gray-400" />
                              </div>
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <span className="font-medium text-gray-900">{p.name}</span>
                            {p.price && <span className="text-primary-600 ml-2">({p.price})</span>}
                            {p.category && <span className="text-gray-500 ml-2">— {p.category}</span>}
                            {p.description && (
                              <p className="text-xs text-gray-500 mt-1 line-clamp-2">{p.description}</p>
                            )}
                          </div>
                          <div className="flex gap-1">
                            <button
                              onClick={() => handleEditProduct(i)}
                              className="p-1.5 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded transition-colors"
                              title="Edit product"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleRemoveProduct(i)}
                              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                              title="Remove product"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {/* Characters Section for PuLID */}
            <div className="border-t pt-6 mt-6">
              <div className="text-center mb-4">
                <User className="w-8 h-8 text-purple-600 mx-auto mb-2" />
                <h3 className="text-lg font-semibold text-gray-900">Add Characters (Optional)</h3>
                <p className="text-sm text-gray-500">Add people or mascots for face consistency using PuLID</p>
              </div>
              
              {/* Character Input Form */}
              <div className="space-y-3 bg-purple-50 rounded-lg p-4">
                <div>
                  <label className="label text-sm">Character Name</label>
                  <input
                    type="text"
                    value={newCharacterName}
                    onChange={(e) => setNewCharacterName(e.target.value)}
                    placeholder="e.g., Mohammad, Brand Mascot"
                    className="input"
                  />
                </div>
                <div>
                  <label className="label text-sm">Reference Image URL</label>
                  <input
                    type="url"
                    value={newCharacterImageUrl}
                    onChange={(e) => setNewCharacterImageUrl(e.target.value)}
                    placeholder="https://example.com/person-photo.jpg"
                    className="input"
                  />
                  <p className="text-xs text-gray-500 mt-1">Use a clear face photo for best results</p>
                </div>
                <div>
                  <label className="label text-sm">Body Type (for full-body scenes)</label>
                  <select
                    value={newCharacterBodyType}
                    onChange={(e) => setNewCharacterBodyType(e.target.value)}
                    className="input"
                  >
                    <option value="average">Average</option>
                    <option value="athletic">Athletic</option>
                    <option value="slim">Slim</option>
                    <option value="heavy">Heavy</option>
                  </select>
                </div>
                <button
                  onClick={() => {
                    if (newCharacterName && newCharacterImageUrl) {
                      setCharacters(prev => [...prev, {
                        name: newCharacterName,
                        reference_image_url: newCharacterImageUrl,
                        body_type: newCharacterBodyType
                      }])
                      setNewCharacterName('')
                      setNewCharacterImageUrl('')
                      setNewCharacterBodyType('average')
                    }
                  }}
                  disabled={!newCharacterName || !newCharacterImageUrl}
                  className="btn-primary w-full flex items-center justify-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  Add Character
                </button>
              </div>
              
              {/* Characters List */}
              {characters.length > 0 && (
                <div className="mt-4 space-y-2">
                  <h4 className="text-sm font-medium text-gray-700">Added Characters:</h4>
                  {characters.map((char, i) => (
                    <div key={i} className="flex items-center gap-3 bg-white rounded-lg p-3 border">
                      {char.reference_image_url ? (
                        <img 
                          src={char.reference_image_url} 
                          alt={char.name}
                          className="w-12 h-12 rounded-full object-cover border-2 border-purple-300"
                        />
                      ) : (
                        <div className="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center">
                          <User className="w-6 h-6 text-purple-400" />
                        </div>
                      )}
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{char.name}</p>
                        <p className="text-xs text-gray-500">{char.body_type}</p>
                      </div>
                      <button
                        onClick={() => setCharacters(prev => prev.filter((_, idx) => idx !== i))}
                        className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <div className="flex gap-3">
              <button 
                onClick={handleSkipProducts}
                className="btn-secondary flex-1"
                disabled={loading}
              >
                {products.length > 0 || characters.length > 0 ? 'Continue' : 'Skip for Now'}
              </button>
              {(products.length > 0 || characters.length > 0) && (
                <button 
                  onClick={handleContinueToStyle}
                  className="btn-primary flex-1 flex items-center justify-center gap-2"
                >
                  Continue
                  <ArrowRight className="w-5 h-5" />
                </button>
              )}
            </div>
          </div>
        )}
        
        {/* Step 3: Style Preferences */}
        {currentStep === 3 && (
          <div className="space-y-6">
            <div className="text-center">
              <Type className="w-12 h-12 text-primary-600 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Style Preferences</h2>
              <p className="text-gray-600">Choose how text will appear on your generated images</p>
            </div>
            
            {/* Font Selection */}
            <div>
              <label className="label flex items-center gap-2">
                <Type className="w-4 h-4" />
                Select Font Style
              </label>
              <div className="grid grid-cols-2 gap-3 mt-2">
                {(availableFonts.length > 0 ? availableFonts : [
                  { id: 'montserrat', name: 'Montserrat', description: 'Modern, clean sans-serif', style: 'modern' },
                  { id: 'playfair', name: 'Playfair Display', description: 'Elegant serif for luxury brands', style: 'elegant' },
                  { id: 'roboto', name: 'Roboto', description: 'Versatile, professional sans-serif', style: 'professional' },
                  { id: 'poppins', name: 'Poppins', description: 'Friendly, geometric sans-serif', style: 'friendly' },
                  { id: 'oswald', name: 'Oswald', description: 'Bold, impactful condensed', style: 'bold' },
                  { id: 'bebas', name: 'Bebas Neue', description: 'All-caps display font', style: 'display' },
                ]).map(font => (
                  <button
                    key={font.id}
                    type="button"
                    onClick={() => setSelectedFont(font.id)}
                    className={`p-4 rounded-lg border-2 text-left transition-all ${
                      selectedFont === font.id
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <p className={`text-lg font-bold mb-1 ${
                      selectedFont === font.id ? 'text-primary-700' : 'text-gray-900'
                    }`} style={{ fontFamily: font.name }}>
                      {font.name}
                    </p>
                    <p className="text-xs text-gray-500">{font.description}</p>
                  </button>
                ))}
              </div>
            </div>
            
            {/* Text Layout Selection */}
            <div>
              <label className="label flex items-center gap-2">
                <Layout className="w-4 h-4" />
                Text Placement
              </label>
              <div className="grid grid-cols-2 gap-3 mt-2">
                {[
                  { id: 'bottom_centered', name: 'Bottom Center', description: 'Text centered at bottom', icon: '▼' },
                  { id: 'top_centered', name: 'Top Center', description: 'Text centered at top', icon: '▲' },
                  { id: 'center_overlay', name: 'Center', description: 'Text in middle', icon: '●' },
                  { id: 'bottom_left', name: 'Bottom Left', description: 'Text aligned left', icon: '◣' },
                ].map(layout => (
                  <button
                    key={layout.id}
                    type="button"
                    onClick={() => setSelectedLayout(layout.id)}
                    className={`p-4 rounded-lg border-2 text-left transition-all ${
                      selectedLayout === layout.id
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xl">{layout.icon}</span>
                      <span className={`font-medium ${
                        selectedLayout === layout.id ? 'text-primary-700' : 'text-gray-900'
                      }`}>{layout.name}</span>
                    </div>
                    <p className="text-xs text-gray-500">{layout.description}</p>
                  </button>
                ))}
              </div>
            </div>
            
            {/* Preview */}
            <div className="bg-gray-100 rounded-lg p-4">
              <p className="text-sm text-gray-500 mb-2">Preview:</p>
              <div className="bg-gradient-to-br from-gray-700 to-gray-900 rounded-lg aspect-video relative overflow-hidden">
                {/* Simulated image background */}
                <div className="absolute inset-0 opacity-30">
                  <div className="w-full h-full bg-gradient-to-r from-primary-600/50 to-purple-600/50" />
                </div>
                
                {/* Text overlay preview */}
                <div className={`absolute inset-0 flex flex-col p-4 ${
                  selectedLayout === 'bottom_centered' ? 'justify-end items-center text-center' :
                  selectedLayout === 'top_centered' ? 'justify-start items-center text-center pt-6' :
                  selectedLayout === 'center_overlay' ? 'justify-center items-center text-center' :
                  'justify-end items-start text-left'
                }`}>
                  <div className={`${
                    selectedLayout.includes('bottom') ? 'bg-gradient-to-t from-black/70 to-transparent absolute inset-x-0 bottom-0 h-1/2' :
                    selectedLayout.includes('top') ? 'bg-gradient-to-b from-black/70 to-transparent absolute inset-x-0 top-0 h-1/2' :
                    ''
                  }`} />
                  <div className="relative z-10">
                    <h3 className="text-white text-lg font-bold mb-1" style={{ fontFamily: selectedFont === 'playfair' ? 'serif' : 'sans-serif' }}>
                      YOUR HEADLINE HERE
                    </h3>
                    <p className="text-white/80 text-sm">
                      Your body copy will appear here
                    </p>
                  </div>
                </div>
              </div>
            </div>
            
            <button 
              onClick={handleContinueToComplete}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              Continue
              <ArrowRight className="w-5 h-5" />
            </button>
          </div>
        )}
        
        {/* Step 4: Complete */}
        {currentStep === 4 && (
          <div className="space-y-6 text-center">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto" />
            <h2 className="text-2xl font-bold text-gray-900">Setup Complete!</h2>
            <p className="text-gray-600">
              Your brand "{brandData?.company_name}" is ready. Start generating content!
            </p>
            
            <div className="bg-gray-50 rounded-lg p-4 text-left">
              <h4 className="font-medium text-gray-900 mb-2">Summary:</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>✓ Brand: {brandData?.company_name}</li>
                <li>✓ Logo: {brandData?.logo?.url ? 'Captured' : 'Not available'}</li>
                <li>✓ Colors: {brandData?.colors?.length || 0} colors extracted</li>
                <li>✓ Products: {products.length} products added</li>
                <li>✓ Font: {selectedFont.charAt(0).toUpperCase() + selectedFont.slice(1)}</li>
                <li>✓ Text Layout: {selectedLayout.replace('_', ' ')}</li>
              </ul>
            </div>
            
            <button 
              onClick={handleComplete}
              className="btn-primary px-8 py-3 text-lg flex items-center justify-center gap-2 mx-auto"
            >
              <Sparkles className="w-5 h-5" />
              Generate Content
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
