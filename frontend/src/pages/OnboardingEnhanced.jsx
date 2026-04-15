import { useState, useEffect, useCallback, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { 
  Globe, Loader2, CheckCircle, AlertCircle, 
  Image, Palette, ShoppingBag, ArrowRight, 
  Sparkles, Upload, RefreshCw, Link, FileText,
  Trash2, Edit2, X, Plus, Type, Layout,
  Network, Eye, Play, User, Layers, Zap,
  GitBranch, Database, Brain, Settings
} from 'lucide-react'
import { 
  scrapeBrand, 
  checkLogoQuality, 
  generateAILogo,
  getBrandDNA,
  getBrandGraph,
  addBrandColor,
  addBrandStyle,
  addBrandProduct,
  addBrandCharacter,
  updateBrandComposition,
  initializeBrandDNA,
  API_BASE_URL
} from '../services/api'
import { getActiveBrandId, setActiveBrandId } from '../services/brandSession'

// Node colors for graph visualization
const NODE_COLORS = {
  brand: '#6366f1',      // Indigo
  color: '#f59e0b',      // Amber
  style: '#8b5cf6',      // Purple
  composition: '#06b6d4', // Cyan
  product: '#ec4899',    // Pink
  character: '#10b981',  // Emerald
  learned_preference: '#ef4444' // Red
}

const EDGE_COLORS = {
  HAS_COLOR: '#f59e0b',
  HAS_STYLE: '#8b5cf6',
  HAS_COMPOSITION: '#06b6d4',
  SELLS: '#ec4899',
  HAS_CHARACTER: '#10b981',
  LEARNED: '#ef4444'
}

export default function OnboardingEnhanced() {
  const location = useLocation()
  const navigate = useNavigate()
  const initialUrl = location.state?.websiteUrl || ''
  const initialIndustry = location.state?.industry || ''
  const initialBrief = location.state?.businessBrief || ''
  const persistedBrandId = location.state?.brandId || getActiveBrandId() || null
  const redirectAfterOnboarding = location.state?.redirectAfterOnboarding || 'generate'
  
  const [currentStep, setCurrentStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  // Brand data
  const [websiteUrl, setWebsiteUrl] = useState(initialUrl)
  const [industry, setIndustry] = useState(initialIndustry)
  const [businessBrief, setBusinessBrief] = useState(initialBrief)
  const [brandData, setBrandData] = useState(null)
  const [brandId, setBrandId] = useState(persistedBrandId)
  
  // Live graph visualization
  const [graphNodes, setGraphNodes] = useState([])
  const [graphEdges, setGraphEdges] = useState([])
  const [animatingNodes, setAnimatingNodes] = useState(new Set())
  const [graphStats, setGraphStats] = useState({ nodes: 0, edges: 0 })
  
  // Brand DNA editing
  const [colors, setColors] = useState([])
  const [styles, setStyles] = useState([])
  const [products, setProducts] = useState([])
  const [characters, setCharacters] = useState([])
  const [composition, setComposition] = useState({
    layout: 'centered',
    text_density: 'moderate',
    text_position: 'bottom',
    overlay_opacity: 0.0
  })
  
  // New item forms
  const [newColor, setNewColor] = useState({ hex: '#000000', name: '', role: 'accent' })
  const [newStyle, setNewStyle] = useState({ type: '', keywords: '' })
  const [newProduct, setNewProduct] = useState({ name: '', category: '', image_url: '' })
  const [newCharacter, setNewCharacter] = useState({ name: '', reference_image_url: '', body_type: 'average' })
  
  // Logo editing
  const [logo, setLogo] = useState(null)
  const [editingLogo, setEditingLogo] = useState(false)
  const [newLogoUrl, setNewLogoUrl] = useState('')
  
  // Color editing
  const [editingColors, setEditingColors] = useState(false)
  
  const graphContainerRef = useRef(null)
  
  // Steps for onboarding
  const STEPS = [
    { id: 'scrape', label: 'Website Scan', icon: Globe },
    { id: 'colors', label: 'Brand Colors', icon: Palette },
    { id: 'style', label: 'Brand Style', icon: Sparkles },
    { id: 'products', label: 'Products', icon: ShoppingBag },
    { id: 'characters', label: 'Characters', icon: User },
    { id: 'complete', label: 'Complete', icon: CheckCircle }
  ]
  
  // Auto-scrape if URL provided
  useEffect(() => {
    if (initialUrl && !brandData) {
      handleScrape()
    }
  }, [])
  
  // Fetch brand DNA graph when brand is loaded
  useEffect(() => {
    if (brandId) {
      fetchBrandGraph()
    }
  }, [brandId])

  // Keep brand id available across navigation and reloads.
  useEffect(() => {
    if (brandId) {
      setActiveBrandId(brandId)
    }
  }, [brandId])

  const resolveBrandId = (data) => {
    const candidate = data?.id || data?.brand_id || data?.brandId
    return String(candidate || '').trim()
  }
  
  const fetchBrandGraph = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/brand-dna/${brandId}/graph`)
      const data = await response.json()
      
      if (data.success) {
        setGraphNodes(data.graph.nodes)
        setGraphEdges(data.graph.edges)
        setGraphStats({
          nodes: data.graph.stats.total_nodes,
          edges: data.graph.stats.total_edges
        })
      }
    } catch (err) {
      console.error('Failed to fetch brand graph:', err)
    }
  }
  
  const addNodeWithAnimation = (node) => {
    setAnimatingNodes(prev => new Set([...prev, node.id]))
    setGraphNodes(prev => [...prev, node])
    
    setTimeout(() => {
      setAnimatingNodes(prev => {
        const next = new Set(prev)
        next.delete(node.id)
        return next
      })
    }, 1000)
  }
  
  const addEdgeWithAnimation = (edge) => {
    setGraphEdges(prev => [...prev, { ...edge, isNew: true }])
    
    setTimeout(() => {
      setGraphEdges(prev => prev.map(e => 
        e.source === edge.source && e.target === edge.target 
          ? { ...e, isNew: false } 
          : e
      ))
    }, 1000)
  }
  
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
      
      // Merge user-provided industry if available
      const brandIndustry = industry || data.industry || 'General'
      
      setBrandData({ ...data, id: resolvedBrandId, industry: brandIndustry, businessBrief })
      setBrandId(resolvedBrandId)
      setActiveBrandId(resolvedBrandId)
      
      // Set logo if extracted - handle both object and string formats
      if (data.logo?.url) {
        setLogo(data.logo.url)
      } else if (data.logo_url) {
        setLogo(data.logo_url)
      }
      
      // Add brand node to graph with industry
      addNodeWithAnimation({
        id: `brand_${resolvedBrandId}`,
        type: 'brand',
        label: data.name || 'Brand',
        data: { tagline: data.tagline, industry: brandIndustry, brief: businessBrief }
      })
      
      // Add extracted colors
      if (data.colors && data.colors.length > 0) {
        setColors(data.colors.map((c, i) => ({
          hex: typeof c === 'string' ? c : c.hex,
          name: typeof c === 'object' ? c.name : `Color ${i + 1}`,
          role: i === 0 ? 'primary' : i === 1 ? 'secondary' : 'accent'
        })))
        
        // Animate color nodes being added
        data.colors.forEach((c, i) => {
          setTimeout(() => {
            const hex = typeof c === 'string' ? c : c.hex
            // Use unique ID to avoid collisions with duplicate hex values
            const uniqueId = `color_${i}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
            addNodeWithAnimation({
              id: uniqueId,
              type: 'color',
              label: hex,
              data: { hex, index: i }
            })
            addEdgeWithAnimation({
              source: `brand_${resolvedBrandId}`,
              target: uniqueId,
              type: 'HAS_COLOR'
            })
          }, 500 + i * 300)
        })
      }
      
      setCurrentStep(1)
    } catch (err) {
      setError(err.message || 'Failed to scrape website')
    } finally {
      setLoading(false)
    }
  }

  const handleContinueAfterOnboarding = () => {
    const activeId = brandId || getActiveBrandId()
    if (!activeId) {
      setError('Brand ID is missing. Please run website scan again before continuing.')
      return
    }

    setActiveBrandId(activeId)
    navigate(`/${redirectAfterOnboarding}/${activeId}`)
  }
  
  // Add color to brand DNA
  const handleAddColor = async () => {
    if (!newColor.hex || !newColor.name) return
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/brand-dna/${brandId}/colors`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newColor)
      })
      
      const result = await response.json()
      
      if (result.success) {
        setColors(prev => [...prev, newColor])
        
        // Add to graph with animation - use timestamp for unique IDs
        const colorId = `color_${newColor.hex.replace('#', '')}_${Date.now()}`
        addNodeWithAnimation({
          id: colorId,
          type: 'color',
          label: newColor.name,
          data: newColor
        })
        addEdgeWithAnimation({
          source: `brand_${brandId}`,
          target: colorId,
          type: 'HAS_COLOR'
        })
        
        setNewColor({ hex: '#000000', name: '', role: 'accent' })
      }
    } catch (err) {
      console.error('Failed to add color:', err)
    }
  }
  
  // Add style to brand DNA
  const handleAddStyle = async () => {
    if (!newStyle.type) return
    
    const keywords = newStyle.keywords.split(',').map(k => k.trim()).filter(k => k)
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/brand-dna/${brandId}/styles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...newStyle, keywords })
      })
      
      const result = await response.json()
      
      if (result.success) {
        const style = { ...newStyle, keywords, id: result.style?.id }
        setStyles(prev => [...prev, style])
        
        // Add to graph with animation
        addNodeWithAnimation({
          id: `style_${style.id || Date.now()}`,
          type: 'style',
          label: style.type,
          data: style
        })
        addEdgeWithAnimation({
          source: `brand_${brandId}`,
          target: `style_${style.id || Date.now()}`,
          type: 'HAS_STYLE'
        })
        
        setNewStyle({ type: '', keywords: '' })
      }
    } catch (err) {
      console.error('Failed to add style:', err)
    }
  }
  
  // Add product to brand DNA
  const handleAddProduct = async () => {
    if (!newProduct.name || !newProduct.image_url) return
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/brand-dna/${brandId}/products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newProduct)
      })
      
      const result = await response.json()
      
      if (result.success) {
        const product = { ...newProduct, id: result.product?.id }
        setProducts(prev => [...prev, product])
        
        // Add to graph with animation
        addNodeWithAnimation({
          id: `product_${product.id || Date.now()}`,
          type: 'product',
          label: product.name,
          data: product
        })
        addEdgeWithAnimation({
          source: `brand_${brandId}`,
          target: `product_${product.id || Date.now()}`,
          type: 'SELLS'
        })
        
        setNewProduct({ name: '', category: '', image_url: '' })
      }
    } catch (err) {
      console.error('Failed to add product:', err)
    }
  }
  
  // Add character to brand DNA
  const handleAddCharacter = async () => {
    if (!newCharacter.name || !newCharacter.reference_image_url) return
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/brand-dna/${brandId}/characters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newCharacter)
      })
      
      const result = await response.json()
      
      if (result.success) {
        const character = { ...newCharacter, id: result.character?.id }
        setCharacters(prev => [...prev, character])
        
        // Add to graph with animation
        addNodeWithAnimation({
          id: `character_${character.id || Date.now()}`,
          type: 'character',
          label: character.name,
          data: character
        })
        addEdgeWithAnimation({
          source: `brand_${brandId}`,
          target: `character_${character.id || Date.now()}`,
          type: 'HAS_CHARACTER'
        })
        
        setNewCharacter({ name: '', reference_image_url: '', body_type: 'average' })
      }
    } catch (err) {
      console.error('Failed to add character:', err)
    }
  }
  
  // Update composition
  const handleUpdateComposition = async (updates) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/brand-dna/${brandId}/composition`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      })
      
      const result = await response.json()
      
      if (result.success) {
        setComposition(prev => ({ ...prev, ...updates }))
      }
    } catch (err) {
      console.error('Failed to update composition:', err)
    }
  }
  
  // Calculate node positions for visualization
  const getNodePosition = (node, index, total) => {
    if (node.type === 'brand') {
      return { x: 250, y: 200 }
    }
    
    // Arrange other nodes in a circle around the brand
    const typeIndex = ['color', 'style', 'composition', 'product', 'character', 'learned_preference'].indexOf(node.type)
    const sameTypeNodes = graphNodes.filter(n => n.type === node.type)
    const indexInType = sameTypeNodes.findIndex(n => n.id === node.id)
    
    const baseAngle = (typeIndex / 6) * 2 * Math.PI - Math.PI / 2
    const offsetAngle = sameTypeNodes.length > 1 ? (indexInType / (sameTypeNodes.length - 1) - 0.5) * 0.5 : 0
    const angle = baseAngle + offsetAngle
    
    const radius = 150
    return {
      x: 250 + Math.cos(angle) * radius,
      y: 200 + Math.sin(angle) * radius
    }
  }
  
  // Render graph visualization
  const renderGraph = () => {
    return (
      <svg width="100%" height="400" viewBox="0 0 500 400" className="bg-gray-900 rounded-xl">
        <defs>
          <marker id="arrowhead-graph" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#6b7280" />
          </marker>
        </defs>
        
        {/* Draw edges */}
        {graphEdges.map((edge, i) => {
          const sourceNode = graphNodes.find(n => n.id === edge.source)
          const targetNode = graphNodes.find(n => n.id === edge.target)
          if (!sourceNode || !targetNode) return null
          
          const sourcePos = getNodePosition(sourceNode)
          const targetPos = getNodePosition(targetNode)
          
          return (
            <g key={`edge-${i}`}>
              <line
                x1={sourcePos.x}
                y1={sourcePos.y}
                x2={targetPos.x}
                y2={targetPos.y}
                stroke={EDGE_COLORS[edge.type] || '#6b7280'}
                strokeWidth={edge.isNew ? 3 : 2}
                strokeDasharray={edge.isNew ? "5,5" : "0"}
                className={edge.isNew ? 'animate-pulse' : ''}
                markerEnd="url(#arrowhead-graph)"
              />
              <text
                x={(sourcePos.x + targetPos.x) / 2}
                y={(sourcePos.y + targetPos.y) / 2 - 5}
                fill="#9ca3af"
                fontSize="8"
                textAnchor="middle"
              >
                {edge.type}
              </text>
            </g>
          )
        })}
        
        {/* Draw nodes */}
        {graphNodes.map((node) => {
          const pos = getNodePosition(node)
          const isAnimating = animatingNodes.has(node.id)
          const radius = node.type === 'brand' ? 40 : 25
          
          return (
            <g key={node.id} className={isAnimating ? 'animate-bounce' : ''}>
              <circle
                cx={pos.x}
                cy={pos.y}
                r={radius}
                fill={NODE_COLORS[node.type]}
                stroke="white"
                strokeWidth="2"
                className={`cursor-pointer hover:brightness-110 transition-all ${isAnimating ? 'animate-pulse' : ''}`}
              />
              <text
                x={pos.x}
                y={pos.y + 4}
                fill="white"
                fontSize={node.type === 'brand' ? "12" : "9"}
                textAnchor="middle"
                fontWeight="bold"
              >
                {node.label?.length > 10 ? node.label.substring(0, 8) + '..' : node.label}
              </text>
            </g>
          )
        })}
        
        {/* Empty state */}
        {graphNodes.length === 0 && (
          <text x="250" y="200" fill="#6b7280" fontSize="14" textAnchor="middle">
            Scan a website to start building the Brand DNA graph
          </text>
        )}
      </svg>
    )
  }
  
  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <Network className="w-8 h-8 text-purple-600" />
          Brand DNA Builder
        </h1>
        <p className="text-gray-600 mt-1">
          Build your brand's knowledge graph - watch relationships form in real-time
        </p>
      </div>
      
      {/* Progress Steps */}
      <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
        {STEPS.map((step, index) => {
          const StepIcon = step.icon
          const isActive = index === currentStep
          const isComplete = index < currentStep
          
          return (
            <div key={step.id} className="flex items-center">
              <button
                onClick={() => brandId && setCurrentStep(index)}
                disabled={!brandId && index > 0}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
                  ${isActive ? 'bg-purple-600 text-white' : 
                    isComplete ? 'bg-green-100 text-green-700' : 
                    'bg-gray-100 text-gray-500'}`}
              >
                <StepIcon className="w-4 h-4" />
                {step.label}
              </button>
              {index < STEPS.length - 1 && (
                <ArrowRight className="w-4 h-4 mx-2 text-gray-300" />
              )}
            </div>
          )
        })}
      </div>
      
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Left: Live Graph Visualization */}
        <div className="card border-2 border-purple-200">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-purple-600" />
              <h2 className="font-semibold text-gray-900">Live Knowledge Graph</h2>
              <span className="px-2 py-0.5 bg-green-500 text-white text-xs rounded-full animate-pulse">● LIVE</span>
            </div>
            <div className="text-sm text-gray-500">
              {graphStats.nodes} nodes • {graphStats.edges} edges
            </div>
          </div>
          
          {renderGraph()}
          
          {/* Legend */}
          <div className="mt-4 flex flex-wrap gap-3 text-xs">
            {Object.entries(NODE_COLORS).map(([type, color]) => (
              <div key={type} className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }}></div>
                <span className="capitalize text-gray-600">{type.replace('_', ' ')}</span>
              </div>
            ))}
          </div>
        </div>
        
        {/* Right: Step Content */}
        <div className="card">
          {/* Step 0: Website Scan */}
          {currentStep === 0 && (
            <div>
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <Globe className="w-6 h-6 text-blue-600" />
                Scan Website
              </h2>
              <p className="text-gray-600 mb-4">
                Enter your brand's website URL. We'll extract colors, logo, and create the initial Brand node.
              </p>
              
              <div className="space-y-4 mb-4">
                {/* URL Input */}
                <div className="flex gap-2">
                  <input
                    type="url"
                    value={websiteUrl}
                    onChange={(e) => setWebsiteUrl(e.target.value)}
                    placeholder="https://example.com"
                    className="flex-1 px-4 py-3 border rounded-lg focus:ring-2 focus:ring-purple-500"
                  />
                  <button
                    onClick={handleScrape}
                    disabled={loading || !websiteUrl.trim()}
                    className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
                  >
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5" />}
                    Scan
                  </button>
                </div>
                
                {/* Industry Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Your Industry
                  </label>
                  <select
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500"
                  >
                    <option value="">Select industry (helps with news & content)</option>
                    <option value="Technology">Technology</option>
                    <option value="Finance">Finance / Fintech</option>
                    <option value="Healthcare">Healthcare</option>
                    <option value="Retail">Retail / E-commerce</option>
                    <option value="Manufacturing">Manufacturing</option>
                    <option value="Education">Education / EdTech</option>
                    <option value="Marketing">Marketing / Agency</option>
                    <option value="Real Estate">Real Estate</option>
                    <option value="Hospitality">Hospitality / Travel</option>
                    <option value="Energy">Energy / CleanTech</option>
                    <option value="SaaS">SaaS / Software</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
                
                {/* Business Brief */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Brief Description (optional)
                  </label>
                  <textarea
                    value={businessBrief}
                    onChange={(e) => setBusinessBrief(e.target.value)}
                    placeholder="What does your company do? E.g., 'B2B SaaS providing AI-powered customer support automation'"
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500"
                    rows={2}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    This helps generate more relevant LinkedIn posts and industry news
                  </p>
                </div>
              </div>
              
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {error}
                </div>
              )}
            </div>
          )}
          
          {/* Step 1: Colors */}
          {currentStep === 1 && (
            <div>
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <Palette className="w-6 h-6 text-amber-600" />
                Brand Colors
              </h2>
              <p className="text-gray-600 mb-4">
                These colors were extracted from your website. Add more or adjust roles.
              </p>
              
              {/* Logo Section - Always show with option to add/edit */}
              <div className="mb-6 p-4 bg-gray-50 rounded-lg border">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium text-gray-700 flex items-center gap-2">
                    <Image className="w-4 h-4" /> Brand Logo
                  </h3>
                  <button
                    onClick={() => setEditingLogo(!editingLogo)}
                    className="text-sm text-purple-600 hover:text-purple-800 flex items-center gap-1"
                  >
                    <Edit2 className="w-3 h-3" /> {editingLogo ? 'Cancel' : (logo ? 'Edit' : 'Add')}
                  </button>
                </div>
                <div className="flex items-center gap-4">
                  {logo ? (
                    <img
                      src={logo}
                      alt="Brand Logo"
                      className="h-16 w-auto object-contain bg-white p-2 rounded border"
                      onError={(e) => e.target.style.display = 'none'}
                    />
                  ) : (
                    <div className="h-16 w-16 bg-gray-200 rounded border flex items-center justify-center text-gray-400 text-xs">
                      No logo
                    </div>
                  )}
                  {editingLogo && (
                    <div className="flex-1 flex gap-2">
                      <input
                        type="url"
                        value={newLogoUrl}
                        onChange={(e) => setNewLogoUrl(e.target.value)}
                        placeholder="Logo URL (https://...)"
                        className="flex-1 px-3 py-2 border rounded-lg text-sm"
                      />
                      <button
                        onClick={() => {
                          if (newLogoUrl) {
                            setLogo(newLogoUrl)
                            setNewLogoUrl('')
                            setEditingLogo(false)
                          }
                        }}
                        className="px-3 py-2 bg-green-600 text-white rounded-lg text-sm"
                      >
                        Save
                      </button>
                    </div>
                  )}
                </div>
              </div>
              
              {/* Existing Colors */}
              <div className="grid grid-cols-4 gap-3 mb-6">
                {colors.map((color, i) => (
                  <div key={`color-display-${i}`} className="text-center relative group">
                    <div 
                      className="w-12 h-12 rounded-lg mx-auto mb-1 border-2 border-gray-200"
                      style={{ backgroundColor: color.hex }}
                    ></div>
                    <div className="text-xs text-gray-600 truncate">{color.name || color.hex}</div>
                    <div className="text-xs text-gray-400">{color.role}</div>
                    <button
                      onClick={() => {
                        // Remove from colors state
                        setColors(prev => prev.filter((_, idx) => idx !== i))
                        // Remove from graph visualization - find color node by matching data.index
                        setGraphNodes(prev => prev.filter(n => !(n.type === 'color' && n.data?.index === i)))
                        setGraphEdges(prev => {
                          const removedNodes = graphNodes.filter(n => n.type === 'color' && n.data?.index === i)
                          const removedIds = new Set(removedNodes.map(n => n.id))
                          return prev.filter(e => !removedIds.has(e.target) && !removedIds.has(e.source))
                        })
                        // Update stats
                        setGraphStats(prev => ({ 
                          nodes: Math.max(0, prev.nodes - 1), 
                          edges: Math.max(0, prev.edges - 1) 
                        }))
                      }}
                      className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
                      title="Remove color"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
              
              {/* Add New Color */}
              <div className="border-t pt-4">
                <h3 className="font-medium text-gray-700 mb-3">Add Color</h3>
                <div className="grid grid-cols-4 gap-2">
                  <input
                    type="color"
                    value={newColor.hex}
                    onChange={(e) => setNewColor(prev => ({ ...prev, hex: e.target.value }))}
                    className="h-10 w-full rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    value={newColor.name}
                    onChange={(e) => setNewColor(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="Color name"
                    className="px-3 py-2 border rounded-lg text-sm"
                  />
                  <select
                    value={newColor.role}
                    onChange={(e) => setNewColor(prev => ({ ...prev, role: e.target.value }))}
                    className="px-3 py-2 border rounded-lg text-sm"
                  >
                    <option value="primary">Primary</option>
                    <option value="secondary">Secondary</option>
                    <option value="accent">Accent</option>
                    <option value="background">Background</option>
                  </select>
                  <button
                    onClick={handleAddColor}
                    className="px-3 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 flex items-center justify-center gap-1"
                  >
                    <Plus className="w-4 h-4" /> Add
                  </button>
                </div>
              </div>
              
              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setCurrentStep(2)}
                  className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 flex items-center gap-2"
                >
                  Next: Style <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
          
          {/* Step 2: Style */}
          {currentStep === 2 && (
            <div>
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <Sparkles className="w-6 h-6 text-purple-600" />
                Brand Style
              </h2>
              <p className="text-gray-600 mb-4">
                Define your brand's aesthetic. These keywords will condition the AI model.
              </p>
              
              {/* Existing Styles */}
              <div className="space-y-2 mb-6">
                {styles.map((style, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 bg-purple-50 rounded-lg">
                    <span className="font-medium text-purple-700">{style.type}</span>
                    <span className="text-gray-500">•</span>
                    <span className="text-sm text-gray-600">
                      {Array.isArray(style.keywords) ? style.keywords.join(', ') : style.keywords}
                    </span>
                  </div>
                ))}
              </div>
              
              {/* Add New Style */}
              <div className="border-t pt-4">
                <h3 className="font-medium text-gray-700 mb-3">Add Style</h3>
                <div className="space-y-2">
                  <select
                    value={newStyle.type}
                    onChange={(e) => setNewStyle(prev => ({ ...prev, type: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  >
                    <option value="">Select style type...</option>
                    <option value="bold">Bold</option>
                    <option value="minimalist">Minimalist</option>
                    <option value="playful">Playful</option>
                    <option value="luxury">Luxury</option>
                    <option value="professional">Professional</option>
                    <option value="vintage">Vintage</option>
                    <option value="modern">Modern</option>
                    <option value="organic">Organic</option>
                  </select>
                  <input
                    type="text"
                    value={newStyle.keywords}
                    onChange={(e) => setNewStyle(prev => ({ ...prev, keywords: e.target.value }))}
                    placeholder="Keywords (comma-separated): dynamic, athletic, powerful"
                    className="w-full px-3 py-2 border rounded-lg"
                  />
                  <button
                    onClick={handleAddStyle}
                    disabled={!newStyle.type}
                    className="w-full px-3 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                  >
                    Add Style
                  </button>
                </div>
              </div>
              
              <div className="mt-6 flex justify-between">
                <button
                  onClick={() => setCurrentStep(1)}
                  className="px-6 py-2 border rounded-lg hover:bg-gray-50"
                >
                  Back
                </button>
                <button
                  onClick={() => setCurrentStep(3)}
                  className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 flex items-center gap-2"
                >
                  Next: Products <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
          
          {/* Step 3: Products */}
          {currentStep === 3 && (
            <div>
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <ShoppingBag className="w-6 h-6 text-pink-600" />
                Products
              </h2>
              <p className="text-gray-600 mb-4">
                Add product images for IP-Adapter conditioning. The AI will use these as visual references.
              </p>
              
              {/* Existing Products */}
              <div className="grid grid-cols-3 gap-3 mb-6">
                {products.map((product, i) => (
                  <div key={i} className="border rounded-lg overflow-hidden">
                    <div className="aspect-square bg-gray-100">
                      {product.image_url && (
                        <img src={product.image_url} alt={product.name} className="w-full h-full object-cover" />
                      )}
                    </div>
                    <div className="p-2">
                      <div className="font-medium text-sm truncate">{product.name}</div>
                      <div className="text-xs text-gray-500">{product.category}</div>
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Add New Product */}
              <div className="border-t pt-4">
                <h3 className="font-medium text-gray-700 mb-3">Add Product</h3>
                <div className="space-y-2">
                  <input
                    type="text"
                    value={newProduct.name}
                    onChange={(e) => setNewProduct(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="Product name"
                    className="w-full px-3 py-2 border rounded-lg"
                  />
                  <input
                    type="text"
                    value={newProduct.category}
                    onChange={(e) => setNewProduct(prev => ({ ...prev, category: e.target.value }))}
                    placeholder="Category (e.g., footwear, apparel)"
                    className="w-full px-3 py-2 border rounded-lg"
                  />
                  <input
                    type="url"
                    value={newProduct.image_url}
                    onChange={(e) => setNewProduct(prev => ({ ...prev, image_url: e.target.value }))}
                    placeholder="Product image URL"
                    className="w-full px-3 py-2 border rounded-lg"
                  />
                  <button
                    onClick={handleAddProduct}
                    disabled={!newProduct.name || !newProduct.image_url}
                    className="w-full px-3 py-2 bg-pink-600 text-white rounded-lg hover:bg-pink-700 disabled:opacity-50"
                  >
                    Add Product
                  </button>
                </div>
              </div>
              
              <div className="mt-6 flex justify-between">
                <button
                  onClick={() => setCurrentStep(2)}
                  className="px-6 py-2 border rounded-lg hover:bg-gray-50"
                >
                  Back
                </button>
                <button
                  onClick={() => setCurrentStep(4)}
                  className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 flex items-center gap-2"
                >
                  Next: Characters <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
          
          {/* Step 4: Characters */}
          {currentStep === 4 && (
            <div>
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <User className="w-6 h-6 text-emerald-600" />
                Character References
              </h2>
              <p className="text-gray-600 mb-4">
                Add face references for consistent characters across generations (PuLID/InstantID).
              </p>
              
              {/* Existing Characters */}
              <div className="grid grid-cols-3 gap-3 mb-6">
                {characters.map((char, i) => (
                  <div key={i} className="border rounded-lg overflow-hidden">
                    <div className="aspect-square bg-gray-100">
                      {char.reference_image_url && (
                        <img src={char.reference_image_url} alt={char.name} className="w-full h-full object-cover" />
                      )}
                    </div>
                    <div className="p-2">
                      <div className="font-medium text-sm truncate">{char.name}</div>
                      <div className="text-xs text-gray-500">{char.body_type}</div>
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Add New Character */}
              <div className="border-t pt-4">
                <h3 className="font-medium text-gray-700 mb-3">Add Character</h3>
                <div className="space-y-2">
                  <input
                    type="text"
                    value={newCharacter.name}
                    onChange={(e) => setNewCharacter(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="Character name (e.g., Brand Ambassador 1)"
                    className="w-full px-3 py-2 border rounded-lg"
                  />
                  <input
                    type="url"
                    value={newCharacter.reference_image_url}
                    onChange={(e) => setNewCharacter(prev => ({ ...prev, reference_image_url: e.target.value }))}
                    placeholder="Face reference image URL"
                    className="w-full px-3 py-2 border rounded-lg"
                  />
                  <select
                    value={newCharacter.body_type}
                    onChange={(e) => setNewCharacter(prev => ({ ...prev, body_type: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg"
                  >
                    <option value="average">Average</option>
                    <option value="athletic">Athletic</option>
                    <option value="slim">Slim</option>
                    <option value="muscular">Muscular</option>
                  </select>
                  <button
                    onClick={handleAddCharacter}
                    disabled={!newCharacter.name || !newCharacter.reference_image_url}
                    className="w-full px-3 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50"
                  >
                    Add Character
                  </button>
                </div>
              </div>
              
              <div className="mt-6 flex justify-between">
                <button
                  onClick={() => setCurrentStep(3)}
                  className="px-6 py-2 border rounded-lg hover:bg-gray-50"
                >
                  Back
                </button>
                <button
                  onClick={() => setCurrentStep(5)}
                  className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 flex items-center gap-2"
                >
                  Complete <CheckCircle className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
          
          {/* Step 5: Complete */}
          {currentStep === 5 && (
            <div className="text-center py-8">
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-10 h-10 text-green-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Brand DNA Complete!</h2>
              <p className="text-gray-600 mb-6">
                Your brand knowledge graph has been built with {graphStats.nodes} nodes and {graphStats.edges} relationships.
              </p>
              
              <div className="grid grid-cols-4 gap-4 mb-8 text-center">
                <div className="p-3 bg-amber-50 rounded-lg">
                  <div className="text-2xl font-bold text-amber-600">{colors.length}</div>
                  <div className="text-xs text-gray-600">Colors</div>
                </div>
                <div className="p-3 bg-purple-50 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">{styles.length}</div>
                  <div className="text-xs text-gray-600">Styles</div>
                </div>
                <div className="p-3 bg-pink-50 rounded-lg">
                  <div className="text-2xl font-bold text-pink-600">{products.length}</div>
                  <div className="text-xs text-gray-600">Products</div>
                </div>
                <div className="p-3 bg-emerald-50 rounded-lg">
                  <div className="text-2xl font-bold text-emerald-600">{characters.length}</div>
                  <div className="text-xs text-gray-600">Characters</div>
                </div>
              </div>
              
              <button
                onClick={handleContinueAfterOnboarding}
                className="px-8 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg hover:from-purple-700 hover:to-indigo-700 flex items-center gap-2 mx-auto"
              >
                <Zap className="w-5 h-5" />
                Start Generating Content
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
