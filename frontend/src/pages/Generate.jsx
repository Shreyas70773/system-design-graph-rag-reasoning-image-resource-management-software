import { useState, useEffect } from 'react'
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom'
import { 
  Sparkles, Image, Type, Wand2, 
  Loader2, ArrowRight, AlertCircle, Package, Check, Layout,
  Brain, Zap, Eye, History, User, ChevronDown, Copy, Linkedin, Download, Search, 
  Lightbulb, TrendingUp, Calendar, FileText, X, Edit3
} from 'lucide-react'
import { getBrand, generateContent, generateAdvancedContent, getBrandProducts, getLearnedPreferences, getBrandDNA, generateWithBrandDNA, discoverTrendingTopics, generateContentIdeas, generateLinkedInPostAI } from '../services/api'
import { uploadCapstoneScene } from '../services/apiV3'

// Text layout options
const TEXT_LAYOUTS = [
  { id: 'bottom_centered', name: 'Bottom Center', icon: '▼' },
  { id: 'top_centered', name: 'Top Center', icon: '▲' },
  { id: 'center_overlay', name: 'Center', icon: '●' },
  { id: 'bottom_left', name: 'Bottom Left', icon: '◣' },
]

// Logo position options
const LOGO_POSITIONS = [
  { id: 'top_left', name: 'Top Left', icon: '◤' },
  { id: 'top_center', name: 'Top Center', icon: '▲' },
  { id: 'top_right', name: 'Top Right', icon: '◥' },
  { id: 'bottom_left', name: 'Bottom Left', icon: '◣' },
  { id: 'bottom_center', name: 'Bottom Center', icon: '▼' },
  { id: 'bottom_right', name: 'Bottom Right', icon: '◢' },
]

export default function Generate() {
  const { brandId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  
  // Get defaults from onboarding if available
  const defaultFont = location.state?.fontId || 'montserrat'
  const defaultLayout = location.state?.textLayout || 'bottom_centered'
  
  const [brand, setBrand] = useState(null)
  const [products, setProducts] = useState([])
  const [characters, setCharacters] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState(null)
  
  // Form state
  const [prompt, setPrompt] = useState('')
  const [contentType, setContentType] = useState('both')
  const [style, setStyle] = useState('')
  const [selectedProductId, setSelectedProductId] = useState('')
  const [selectedCharacterId, setSelectedCharacterId] = useState('')
  const [textLayout, setTextLayout] = useState(defaultLayout)
  const [includeTextOverlay, setIncludeTextOverlay] = useState(true)
  const [includeLogo, setIncludeLogo] = useState(true)
  const [logoPosition, setLogoPosition] = useState('bottom_right')
  const [headline, setHeadline] = useState('')
  const [bodyCopy, setBodyCopy] = useState('')
  
  // Advanced mode state
  const [useAdvancedMode, setUseAdvancedMode] = useState(true) // Default to advanced
  const [useSceneDecomposition, setUseSceneDecomposition] = useState(true)
  const [useConstraintResolution, setUseConstraintResolution] = useState(true)
  const [useLearnedPreferences, setUseLearnedPreferences] = useState(true)
  const [learnedPreferencesCount, setLearnedPreferencesCount] = useState(0)
  const [aspectRatio, setAspectRatio] = useState('1:1')
  
  // Result
  const [result, setResult] = useState(null)
  const [copied, setCopied] = useState(false)
  
  // AI Content Creator state
  const [showContentCreator, setShowContentCreator] = useState(false)
  const [contentCreatorLoading, setContentCreatorLoading] = useState(false)
  const [contentCreatorTab, setContentCreatorTab] = useState('topics') // topics, ideas, post
  const [trendingTopics, setTrendingTopics] = useState(null)
  const [contentIdeas, setContentIdeas] = useState(null)
  const [generatedPost, setGeneratedPost] = useState(null)
  const [selectedTopic, setSelectedTopic] = useState(null)
  const [selectedIdea, setSelectedIdea] = useState(null)
  const [contentGoal, setContentGoal] = useState('engagement')
  const [contentTone, setContentTone] = useState('professional')
  
  useEffect(() => {
    loadBrandAndProducts()
  }, [brandId])
  
  // Load learned preferences count
  useEffect(() => {
    const loadPreferences = async () => {
      try {
        const prefs = await getLearnedPreferences(brandId)
        setLearnedPreferencesCount(
          (prefs.positive_preferences?.length || 0) + 
          (prefs.negative_patterns?.length || 0)
        )
      } catch (err) {
        // Silently fail - not critical
      }
    }
    if (brandId) loadPreferences()
  }, [brandId])
  
  const loadBrandAndProducts = async () => {
    try {
      // Load brand DNA which includes products and characters
      const [brandData, brandDNAData] = await Promise.all([
        getBrand(brandId),
        getBrandDNA(brandId).catch(() => ({ brand_dna: null }))
      ])
      
      setBrand(brandData)
      
      // Set default headline if not already set
      if (brandData?.name && !headline) {
        setHeadline(brandData.name)
        if (brandData.tagline) {
          setBodyCopy(brandData.tagline)
        }
      }
      
      if (brandDNAData?.brand_dna) {
        setProducts(brandDNAData.brand_dna.products || [])
        setCharacters(brandDNAData.brand_dna.characters || [])
      }
    } catch (err) {
      setError('Failed to load brand')
    } finally {
      setLoading(false)
    }
  }
  
  const handleGenerate = async () => {
    if (!prompt.trim()) return
    
    setGenerating(true)
    setError(null)
    setResult(null)
    
    try {
      let data;
      
      // Always use Brand DNA pipeline for GraphRAG
      if (useAdvancedMode) {
        // Use Brand DNA GraphRAG pipeline
        data = await generateWithBrandDNA(brandId, {
          prompt,
          headline: contentType === 'both' && includeTextOverlay && headline.trim() ? headline.trim() : null,
          body_copy: contentType === 'both' && includeTextOverlay && bodyCopy.trim() ? bodyCopy.trim() : null,
          product_id: selectedProductId || null,
          character_id: selectedCharacterId || null,
          aspect_ratio: aspectRatio,
          text_layout: textLayout,
          include_logo: includeLogo && brand?.logo_url ? true : false,
          use_reasoning: true
        })
      } else {
        // Use basic generation
        data = await generateContent({
          brandId,
          prompt,
          type: contentType,
          style: style || undefined,
          productIds: selectedProductId ? [selectedProductId] : undefined,
          textLayout: textLayout,
          includeTextOverlay: contentType === 'both' ? includeTextOverlay : false,
          includeLogo: includeLogo && brand?.logo_url ? true : false
        })
      }
      
      setResult(data)
      
      // Scroll to result instead of navigating away immediately
      setTimeout(() => {
        document.getElementById('generation-result')?.scrollIntoView({ behavior: 'smooth' })
      }, 100)
    } catch (err) {
      setError(err.message)
    } finally {
      setGenerating(false)
    }
  }
  
  // Build brand profile for content creator
  const buildBrandProfile = () => ({
    name: brand?.name || 'Brand',
    industry: brand?.industry || 'Technology',
    tagline: brand?.tagline,
    values: brand?.values || [],
    products_services: products.map(p => p.name),
    past_topics: [],
    bio: brand?.description
  })
  
  // Discover trending topics
  const handleDiscoverTopics = async () => {
    setContentCreatorLoading(true)
    setTrendingTopics(null)
    
    try {
      const result = await discoverTrendingTopics({
        profile: buildBrandProfile(),
        goals: { goal_type: contentGoal, tone: contentTone },
        num_topics: 5,
        focus_areas: prompt ? [prompt] : []
      })
      setTrendingTopics(result)
    } catch (err) {
      setError(`Failed to discover topics: ${err.message}`)
    } finally {
      setContentCreatorLoading(false)
    }
  }
  
  // Generate content ideas
  const handleGenerateIdeas = async (topic = null) => {
    setContentCreatorLoading(true)
    setContentIdeas(null)
    
    try {
      const result = await generateContentIdeas({
        profile: buildBrandProfile(),
        goals: { goal_type: contentGoal, tone: contentTone },
        num_ideas: 5,
        trending_topic: topic || selectedTopic?.title || prompt || null
      })
      setContentIdeas(result)
      setContentCreatorTab('ideas')
    } catch (err) {
      setError(`Failed to generate ideas: ${err.message}`)
    } finally {
      setContentCreatorLoading(false)
    }
  }
  
  // Generate full LinkedIn post
  const handleGeneratePost = async (idea = null) => {
    setContentCreatorLoading(true)
    setGeneratedPost(null)
    
    try {
      // Build request - only include content_idea if it has required fields
      const postRequest = {
        profile: buildBrandProfile(),
        goals: { goal_type: contentGoal, tone: contentTone },
        topic: idea?.main_topic || selectedIdea?.main_topic || selectedTopic?.title || prompt,
        style: 'storytelling',
        include_emoji: true,
        max_length: 2000,
        generate_variations: true
      }
      
      // Only include content_idea if it's a complete ContentIdea object
      const contentIdea = idea || selectedIdea
      if (contentIdea?.hook && contentIdea?.main_topic && contentIdea?.key_points) {
        postRequest.content_idea = {
          hook: contentIdea.hook,
          main_topic: contentIdea.main_topic,
          key_points: contentIdea.key_points || [],
          call_to_action: contentIdea.call_to_action || 'Share your thoughts below',
          estimated_engagement: contentIdea.estimated_engagement || 'medium',
          content_type: contentIdea.content_type || 'story'
        }
      }
      
      const result = await generateLinkedInPostAI(postRequest)
      setGeneratedPost(result)
      setContentCreatorTab('post')
    } catch (err) {
      setError(`Failed to generate post: ${err.message}`)
    } finally {
      setContentCreatorLoading(false)
    }
  }
  
  // Open content creator modal
  const openContentCreator = () => {
    setShowContentCreator(true)
    setContentCreatorTab('topics')
    if (!trendingTopics) {
      handleDiscoverTopics()
    }
  }
  
  const handleCopyLinkedIn = () => {
    if (result?.headline || result?.body_copy) {
      const text = `${result.headline || ''}\n\n${result.body_copy || ''}`
      navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }
  
  const handleDownloadImage = () => {
    if (result?.image_url) {
      const link = document.createElement('a')
      link.href = result.image_url
      link.download = `${brand?.name || 'brand'}-content.png`
      link.click()
    }
  }
  
  const handleEditInStudio = async () => {
    if (!result?.image_url) return
    
    try {
      setGenerating(true)
      
      // Fetch the image and convert to blob
      const response = await fetch(result.image_url)
      const blob = await response.blob()
      const file = new File(blob, `${brand?.name || 'brand'}-generated.png`, { type: 'image/png' })
      
      // Upload to Studio
      const uploadResponse = await uploadCapstoneScene(file, {
        title: `${brand?.name} - ${new Date().toLocaleDateString()}`,
        ownerUserId: brandId
      })
      
      if (uploadResponse?.scene_id) {
        // Navigate to Studio with the scene loaded
        navigate(`/capstone`, { state: { sceneId: uploadResponse.scene_id } })
      } else {
        setError('Failed to upload image to editor. Please try again.')
      }
    } catch (err) {
      console.error('Error uploading to studio:', err)
      setError(`Failed to upload to editor: ${err.message}`)
    } finally {
      setGenerating(false)
    }
  }
  
  const handleViewDetails = () => {
    navigate(`/results/${brandId}`, { 
      state: { 
        result, 
        prompt, 
        brandName: brand?.name,
        isAdvanced: useAdvancedMode,
        pipelineExecutionId: result?.pipeline_execution_id,
        selectedProduct: products.find(p => p.id === selectedProductId),
        selectedCharacter: characters.find(c => c.id === selectedCharacterId)
      }
    })
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }
  
  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-gradient-to-br from-primary-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Wand2 className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Generate Content</h1>
        <p className="text-gray-600">
          Creating content for <span className="font-semibold">{brand?.name}</span>
        </p>
      </div>
      
      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-medium text-red-800">Generation Failed</h4>
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        </div>
      )}
      
      {/* Form */}
      <div className="card space-y-6">
        {/* Prompt */}
        <div>
          <label className="label">What would you like to create?</label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Example: Create a summer promotion for our iced coffee drinks. Make it fresh and inviting."
            className="input min-h-[100px]"
            disabled={generating}
          />
        </div>
        
        {/* Advanced Mode Toggle */}
        <div className="border-2 border-purple-200 rounded-lg p-4 bg-gradient-to-r from-purple-50 to-indigo-50">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-purple-600" />
              <span className="font-semibold text-purple-900">GraphRAG Advanced Mode</span>
              {useAdvancedMode && (
                <span className="text-xs bg-purple-600 text-white px-2 py-0.5 rounded-full">
                  RECOMMENDED
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={() => setUseAdvancedMode(!useAdvancedMode)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                useAdvancedMode ? 'bg-purple-600' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  useAdvancedMode ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
          
          {useAdvancedMode ? (
            <div className="space-y-3">
              <p className="text-sm text-purple-700">
                Uses scene decomposition, constraint resolution, and learns from your feedback.
                {learnedPreferencesCount > 0 && (
                  <span className="ml-1 text-purple-900 font-medium">
                    ({learnedPreferencesCount} learned preferences will be applied)
                  </span>
                )}
              </p>
              
              {/* GraphRAG Options */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setUseSceneDecomposition(!useSceneDecomposition)}
                  className={`p-2 rounded border text-left text-sm transition-all ${
                    useSceneDecomposition 
                      ? 'border-purple-400 bg-purple-100 text-purple-800' 
                      : 'border-gray-300 bg-white text-gray-600'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Eye className={`w-4 h-4 ${useSceneDecomposition ? 'text-purple-600' : 'text-gray-400'}`} />
                    <span className="font-medium">Scene Analysis</span>
                  </div>
                  <p className="text-xs mt-1 opacity-80">Breaks down complex prompts</p>
                </button>
                
                <button
                  type="button"
                  onClick={() => setUseConstraintResolution(!useConstraintResolution)}
                  className={`p-2 rounded border text-left text-sm transition-all ${
                    useConstraintResolution 
                      ? 'border-purple-400 bg-purple-100 text-purple-800' 
                      : 'border-gray-300 bg-white text-gray-600'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Zap className={`w-4 h-4 ${useConstraintResolution ? 'text-purple-600' : 'text-gray-400'}`} />
                    <span className="font-medium">Constraints</span>
                  </div>
                  <p className="text-xs mt-1 opacity-80">Enforces brand rules</p>
                </button>
                
                <button
                  type="button"
                  onClick={() => setUseLearnedPreferences(!useLearnedPreferences)}
                  className={`p-2 rounded border text-left text-sm transition-all ${
                    useLearnedPreferences 
                      ? 'border-purple-400 bg-purple-100 text-purple-800' 
                      : 'border-gray-300 bg-white text-gray-600'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <History className={`w-4 h-4 ${useLearnedPreferences ? 'text-purple-600' : 'text-gray-400'}`} />
                    <span className="font-medium">Learning</span>
                  </div>
                  <p className="text-xs mt-1 opacity-80">Uses your feedback</p>
                </button>
              </div>
              
              {/* Aspect Ratio */}
              <div>
                <label className="text-xs font-medium text-purple-800 mb-1 block">Aspect Ratio</label>
                <div className="flex gap-2">
                  {['1:1', '16:9', '9:16', '4:3'].map(ratio => (
                    <button
                      key={ratio}
                      type="button"
                      onClick={() => setAspectRatio(ratio)}
                      className={`px-3 py-1 text-xs rounded transition-all ${
                        aspectRatio === ratio
                          ? 'bg-purple-600 text-white'
                          : 'bg-white border border-purple-300 text-purple-700 hover:bg-purple-50'
                      }`}
                    >
                      {ratio}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-600">
              Basic mode: Direct generation without GraphRAG pipeline. Faster but less intelligent.
            </p>
          )}
        </div>
        
        {/* Content Type */}
        <div>
          <label className="label">Content Type</label>
          <div className="grid grid-cols-3 gap-3">
            <button
              type="button"
              onClick={() => setContentType('both')}
              disabled={generating}
              className={`p-4 rounded-lg border-2 text-center transition-all ${
                contentType === 'both'
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <Sparkles className={`w-6 h-6 mx-auto mb-2 ${
                contentType === 'both' ? 'text-primary-600' : 'text-gray-400'
              }`} />
              <span className={`text-sm font-medium ${
                contentType === 'both' ? 'text-primary-700' : 'text-gray-700'
              }`}>
                Image + Text
              </span>
            </button>
            
            <button
              type="button"
              onClick={() => setContentType('image')}
              disabled={generating}
              className={`p-4 rounded-lg border-2 text-center transition-all ${
                contentType === 'image'
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <Image className={`w-6 h-6 mx-auto mb-2 ${
                contentType === 'image' ? 'text-primary-600' : 'text-gray-400'
              }`} />
              <span className={`text-sm font-medium ${
                contentType === 'image' ? 'text-primary-700' : 'text-gray-700'
              }`}>
                Image Only
              </span>
            </button>
            
            <button
              type="button"
              onClick={() => setContentType('text')}
              disabled={generating}
              className={`p-4 rounded-lg border-2 text-center transition-all ${
                contentType === 'text'
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <Type className={`w-6 h-6 mx-auto mb-2 ${
                contentType === 'text' ? 'text-primary-600' : 'text-gray-400'
              }`} />
              <span className={`text-sm font-medium ${
                contentType === 'text' ? 'text-primary-700' : 'text-gray-700'
              }`}>
                Text Only
              </span>
            </button>
          </div>
        </div>
        
        {/* Style (optional) - only in basic mode */}
        {!useAdvancedMode && (
          <div>
            <label className="label">Style (optional)</label>
            <select
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              className="input"
              disabled={generating}
            >
              <option value="">Auto (based on brand)</option>
              <option value="modern minimalist">Modern & Minimalist</option>
              <option value="bold and vibrant">Bold & Vibrant</option>
              <option value="warm and cozy">Warm & Cozy</option>
              <option value="professional corporate">Professional & Corporate</option>
              <option value="playful and fun">Playful & Fun</option>
              <option value="elegant luxury">Elegant & Luxury</option>
            </select>
          </div>
        )}
        
        {/* Product Context Selection */}
        {products.length > 0 && (
          <div>
            <label className="label flex items-center gap-2">
              <Package className="w-4 h-4" />
              Select Product (for IP-Adapter conditioning)
            </label>
            <p className="text-xs text-gray-500 mb-3">
              The selected product image will influence the generated content to feature this product
            </p>
            <select
              value={selectedProductId}
              onChange={(e) => setSelectedProductId(e.target.value)}
              disabled={generating}
              className="input"
            >
              <option value="">No product reference</option>
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name} {product.category ? `(${product.category})` : ''}
                </option>
              ))}
            </select>
            
            {/* Show selected product preview */}
            {selectedProductId && (
              <div className="mt-3 p-3 bg-primary-50 rounded-lg flex items-center gap-3">
                {products.find(p => p.id === selectedProductId)?.image_url ? (
                  <img 
                    src={products.find(p => p.id === selectedProductId)?.image_url} 
                    alt="Selected product"
                    className="w-16 h-16 rounded-lg object-cover border"
                  />
                ) : (
                  <div className="w-16 h-16 rounded-lg bg-gray-200 flex items-center justify-center">
                    <Package className="w-6 h-6 text-gray-400" />
                  </div>
                )}
                <div className="flex-1">
                  <p className="font-medium text-gray-900">{products.find(p => p.id === selectedProductId)?.name}</p>
                  <p className="text-sm text-gray-600">{products.find(p => p.id === selectedProductId)?.description?.slice(0, 100)}</p>
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Character Selection */}
        {characters.length > 0 && (
          <div>
            <label className="label flex items-center gap-2">
              <User className="w-4 h-4" />
              Select Character (for PuLID face consistency)
            </label>
            <p className="text-xs text-gray-500 mb-3">
              The selected character's face will be used for identity consistency in the generated image
            </p>
            <select
              value={selectedCharacterId}
              onChange={(e) => setSelectedCharacterId(e.target.value)}
              disabled={generating}
              className="input"
            >
              <option value="">No character reference</option>
              {characters.map((character) => (
                <option key={character.id} value={character.id}>
                  {character.name} {character.body_type ? `(${character.body_type})` : ''}
                </option>
              ))}
            </select>
            
            {/* Show selected character preview */}
            {selectedCharacterId && (
              <div className="mt-3 p-3 bg-purple-50 rounded-lg flex items-center gap-3">
                {characters.find(c => c.id === selectedCharacterId)?.reference_image_url ? (
                  <img 
                    src={characters.find(c => c.id === selectedCharacterId)?.reference_image_url} 
                    alt="Selected character"
                    className="w-16 h-16 rounded-full object-cover border-2 border-purple-300"
                  />
                ) : (
                  <div className="w-16 h-16 rounded-full bg-gray-200 flex items-center justify-center">
                    <User className="w-6 h-6 text-gray-400" />
                  </div>
                )}
                <div className="flex-1">
                  <p className="font-medium text-gray-900">{characters.find(c => c.id === selectedCharacterId)?.name}</p>
                  <p className="text-sm text-purple-600">Face will be preserved in generation</p>
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Add Product/Character if none exist */}
        {products.length === 0 && characters.length === 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <p className="text-sm text-amber-800">
              <strong>Tip:</strong> Add products and characters during onboarding to enable product-specific and character-consistent generation.
            </p>
          </div>
        )}
        
        {/* Text Overlay Options (only show for 'both' content type) */}
        {contentType === 'both' && (
          <div className="border rounded-lg p-4 space-y-4">
            <div className="flex items-center justify-between">
              <label className="label flex items-center gap-2 mb-0">
                <Layout className="w-4 h-4" />
                Text Overlay on Image
              </label>
              <button
                type="button"
                onClick={() => setIncludeTextOverlay(!includeTextOverlay)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  includeTextOverlay ? 'bg-primary-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    includeTextOverlay ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            
            {includeTextOverlay && (
              <div className="space-y-4">
                <p className="text-xs text-gray-500">
                  Enter the text you want on your image:
                </p>
                
                {/* Text Inputs */}
                <div className="space-y-3">
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">Headline</label>
                    <input
                      type="text"
                      value={headline}
                      onChange={(e) => setHeadline(e.target.value)}
                      placeholder={`e.g., ${brand?.name || 'Your Brand'} - Quality Products`}
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">Body Text <span className="text-gray-400 font-normal">(optional)</span></label>
                    <input
                      type="text"
                      value={bodyCopy}
                      onChange={(e) => setBodyCopy(e.target.value)}
                      placeholder="e.g., Discover the difference"
                      className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
                    />
                  </div>
                </div>
                
                {/* Layout Selection */}
                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-2">Text Position</label>
                  <div className="grid grid-cols-4 gap-2">
                    {TEXT_LAYOUTS.map(layout => (
                      <button
                        key={layout.id}
                        type="button"
                        onClick={() => setTextLayout(layout.id)}
                        disabled={generating}
                        className={`p-3 rounded-lg border-2 text-center transition-all ${
                          textLayout === layout.id
                            ? 'border-primary-500 bg-primary-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <span className="text-xl block mb-1">{layout.icon}</span>
                        <span className={`text-xs font-medium ${
                          textLayout === layout.id ? 'text-primary-700' : 'text-gray-600'
                        }`}>{layout.name}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
            
            {!includeTextOverlay && (
              <p className="text-xs text-gray-500">
                Image and text will be generated separately
              </p>
            )}
          </div>
        )}
        
        {/* Logo Toggle */}
        {contentType !== 'text' && brand?.logo_url && (
          <div className="border rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <img 
                  src={brand.logo_url} 
                  alt="Brand logo" 
                  className="w-10 h-10 object-contain rounded border bg-white p-1"
                />
                <div>
                  <label className="font-medium text-gray-900">Add Logo to Image</label>
                  <p className="text-xs text-gray-500">Watermark with your brand logo</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIncludeLogo(!includeLogo)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  includeLogo ? 'bg-primary-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    includeLogo ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            
            {/* Logo Position Selector */}
            {includeLogo && (
              <div className="mt-4 pt-4 border-t">
                <label className="block text-sm font-medium text-gray-700 mb-2">Logo Position</label>
                <div className="grid grid-cols-3 gap-2">
                  {LOGO_POSITIONS.map(pos => (
                    <button
                      key={pos.id}
                      type="button"
                      onClick={() => setLogoPosition(pos.id)}
                      className={`p-2 text-center rounded-lg border-2 transition-all ${
                        logoPosition === pos.id
                          ? 'border-primary-500 bg-primary-50 text-primary-700'
                          : 'border-gray-200 hover:border-gray-300 text-gray-600'
                      }`}
                    >
                      <span className="text-lg block">{pos.icon}</span>
                      <span className="text-xs">{pos.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Brand Colors Preview */}
        {brand?.colors?.length > 0 && (
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500 mb-2">Brand colors will be used:</p>
            <div className="flex gap-2">
              {brand.colors.slice(0, 5).map((color, i) => (
                <div 
                  key={i}
                  className="w-8 h-8 rounded border"
                  style={{ backgroundColor: color.hex || color }}
                  title={color.hex || color}
                />
              ))}
            </div>
          </div>
        )}
        
        {/* Action Buttons */}
        <div className="flex gap-3">
          {/* AI Content Creator Button */}
          <button
            onClick={openContentCreator}
            className="flex-1 py-3 text-lg flex items-center justify-center gap-2 rounded-lg font-medium transition-all border-2 border-blue-500 text-blue-600 hover:bg-blue-50"
          >
            <Lightbulb className="w-5 h-5" />
            AI Content Ideas
          </button>
          
          {/* Generate Button */}
          <button
            onClick={handleGenerate}
            disabled={generating || !prompt.trim()}
            className={`flex-[2] py-3 text-lg flex items-center justify-center gap-2 rounded-lg font-medium transition-all ${
              useAdvancedMode 
                ? 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white'
                : 'btn-primary'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {generating ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                {useAdvancedMode ? 'Running GraphRAG Pipeline...' : 'Generating...'}
              </>
            ) : (
              <>
                {useAdvancedMode ? <Brain className="w-5 h-5" /> : <Sparkles className="w-5 h-5" />}
                {useAdvancedMode ? 'Generate with GraphRAG' : 'Generate Content'}
              </>
            )}
          </button>
        </div>
      </div>
      
      {/* === AI CONTENT CREATOR MODAL === */}
      {showContentCreator && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="p-4 border-b bg-gradient-to-r from-blue-50 to-purple-50 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                  <Lightbulb className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">AI Content Creator</h3>
                  <p className="text-xs text-gray-500">Powered by Perplexity AI • Real-time internet search</p>
                </div>
              </div>
              <button 
                onClick={() => setShowContentCreator(false)}
                className="text-gray-500 hover:text-gray-700 p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {/* Settings Bar */}
            <div className="px-4 py-2 border-b bg-gray-50 flex items-center gap-4 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">Goal:</span>
                <select 
                  value={contentGoal} 
                  onChange={(e) => setContentGoal(e.target.value)}
                  className="text-sm border rounded px-2 py-1"
                >
                  <option value="engagement">Engagement</option>
                  <option value="thought_leadership">Thought Leadership</option>
                  <option value="leads">Lead Generation</option>
                  <option value="followers">Grow Followers</option>
                  <option value="job_search">Job Search</option>
                </select>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">Tone:</span>
                <select 
                  value={contentTone} 
                  onChange={(e) => setContentTone(e.target.value)}
                  className="text-sm border rounded px-2 py-1"
                >
                  <option value="professional">Professional</option>
                  <option value="casual">Casual</option>
                  <option value="inspirational">Inspirational</option>
                  <option value="educational">Educational</option>
                  <option value="humorous">Humorous</option>
                </select>
              </div>
              <span className="text-xs text-gray-400">|</span>
              <span className="text-xs text-gray-500">{brand?.name} • {brand?.industry}</span>
            </div>
            
            {/* Tabs */}
            <div className="flex border-b">
              <button
                onClick={() => setContentCreatorTab('topics')}
                className={`flex-1 px-4 py-3 text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
                  contentCreatorTab === 'topics' 
                    ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/50' 
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <TrendingUp className="w-4 h-4" />
                Trending Topics
              </button>
              <button
                onClick={() => setContentCreatorTab('ideas')}
                className={`flex-1 px-4 py-3 text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
                  contentCreatorTab === 'ideas' 
                    ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/50' 
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <Lightbulb className="w-4 h-4" />
                Content Ideas
              </button>
              <button
                onClick={() => setContentCreatorTab('post')}
                className={`flex-1 px-4 py-3 text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
                  contentCreatorTab === 'post' 
                    ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/50' 
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <FileText className="w-4 h-4" />
                Generated Post
              </button>
            </div>
            
            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
              {contentCreatorLoading ? (
                <div className="flex flex-col items-center justify-center h-64 gap-3">
                  <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
                  <p className="text-gray-500">Searching the internet for trending topics...</p>
                </div>
              ) : (
                <>
                  {/* Topics Tab */}
                  {contentCreatorTab === 'topics' && (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium text-gray-800">Trending in {brand?.industry || 'your industry'}</h4>
                        <button
                          onClick={handleDiscoverTopics}
                          className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
                        >
                          <Search className="w-4 h-4" />
                          Refresh
                        </button>
                      </div>
                      
                      {trendingTopics?.topics?.map((topic, i) => (
                        <div 
                          key={i} 
                          className={`border rounded-lg p-4 cursor-pointer transition-all ${
                            selectedTopic?.title === topic.title 
                              ? 'border-blue-500 bg-blue-50' 
                              : 'hover:border-gray-300'
                          }`}
                          onClick={() => setSelectedTopic(topic)}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1">
                              <h5 className="font-medium text-gray-900">{topic.title}</h5>
                              <p className="text-sm text-gray-600 mt-1">{topic.summary}</p>
                              <p className="text-xs text-gray-500 mt-2">
                                <span className="font-medium">Why it matters:</span> {topic.why_relevant}
                              </p>
                            </div>
                            <span className={`text-xs px-2 py-1 rounded-full ${
                              topic.engagement_potential === 'high' ? 'bg-green-100 text-green-700' :
                              topic.engagement_potential === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                              'bg-gray-100 text-gray-600'
                            }`}>
                              {topic.engagement_potential} potential
                            </span>
                          </div>
                          {selectedTopic?.title === topic.title && (
                            <div className="mt-3 pt-3 border-t flex gap-2">
                              <button
                                onClick={(e) => { e.stopPropagation(); handleGenerateIdeas(topic.title); }}
                                className="flex-1 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 flex items-center justify-center gap-1"
                              >
                                <Lightbulb className="w-4 h-4" />
                                Generate Ideas for This
                              </button>
                              <button
                                onClick={(e) => { e.stopPropagation(); handleGeneratePost({ main_topic: topic.title }); }}
                                className="flex-1 py-2 border border-blue-500 text-blue-600 text-sm rounded-lg hover:bg-blue-50 flex items-center justify-center gap-1"
                              >
                                <FileText className="w-4 h-4" />
                                Write Post Now
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                      
                      {trendingTopics?.personalized_angles?.length > 0 && (
                        <div className="mt-6 p-4 bg-purple-50 rounded-lg">
                          <h5 className="font-medium text-purple-800 mb-2">💡 Personalized Angles for {brand?.name}</h5>
                          <ul className="space-y-2">
                            {trendingTopics.personalized_angles.map((angle, i) => (
                              <li key={i} className="text-sm text-purple-700 flex items-start gap-2">
                                <span className="text-purple-400">•</span>
                                {angle}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      
                      {/* Empty State */}
                      {!trendingTopics && !contentCreatorLoading && (
                        <div className="text-center py-12">
                          <TrendingUp className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                          <p className="text-gray-500 mb-4">Click Refresh to discover trending topics</p>
                          <button
                            onClick={handleDiscoverTopics}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 mx-auto"
                          >
                            <Search className="w-4 h-4" />
                            Discover Topics
                          </button>
                        </div>
                      )}
                      
                      {trendingTopics && (!trendingTopics.topics || trendingTopics.topics.length === 0) && (
                        <div className="text-center py-12">
                          <AlertCircle className="w-12 h-12 mx-auto mb-3 text-yellow-400" />
                          <p className="text-gray-500 mb-4">No topics found. Try refreshing or adjusting your industry.</p>
                          <button
                            onClick={handleDiscoverTopics}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 mx-auto"
                          >
                            <Search className="w-4 h-4" />
                            Try Again
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* Ideas Tab */}
                  {contentCreatorTab === 'ideas' && (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium text-gray-800">Content Ideas</h4>
                        <button
                          onClick={() => handleGenerateIdeas()}
                          className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
                        >
                          <Sparkles className="w-4 h-4" />
                          Generate More
                        </button>
                      </div>
                      
                      {contentIdeas?.daily_suggestion && (
                        <div className="p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg border border-green-200">
                          <div className="flex items-center gap-2 mb-2">
                            <Calendar className="w-4 h-4 text-green-600" />
                            <span className="font-medium text-green-800">Today's Suggestion</span>
                          </div>
                          <p className="text-sm text-green-700">{contentIdeas.daily_suggestion}</p>
                        </div>
                      )}
                      
                      {contentIdeas?.ideas?.map((idea, i) => (
                        <div 
                          key={i} 
                          className={`border rounded-lg p-4 cursor-pointer transition-all ${
                            selectedIdea?.hook === idea.hook 
                              ? 'border-blue-500 bg-blue-50' 
                              : 'hover:border-gray-300'
                          }`}
                          onClick={() => setSelectedIdea(idea)}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1">
                              <p className="text-blue-600 font-medium italic">"{idea.hook}"</p>
                              <h5 className="font-medium text-gray-900 mt-2">{idea.main_topic}</h5>
                              <div className="mt-2 space-y-1">
                                {idea.key_points?.slice(0, 3).map((point, j) => (
                                  <p key={j} className="text-xs text-gray-500 flex items-start gap-1">
                                    <span>•</span> {point}
                                  </p>
                                ))}
                              </div>
                              <p className="text-xs text-gray-500 mt-2">
                                <span className="font-medium">CTA:</span> {idea.call_to_action}
                              </p>
                            </div>
                            <div className="text-right space-y-1">
                              <span className="text-xs bg-gray-100 px-2 py-1 rounded">{idea.content_type}</span>
                              <span className={`block text-xs px-2 py-1 rounded ${
                                idea.estimated_engagement === 'high' ? 'bg-green-100 text-green-700' :
                                idea.estimated_engagement === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                                'bg-gray-100 text-gray-600'
                              }`}>
                                {idea.estimated_engagement}
                              </span>
                            </div>
                          </div>
                          {selectedIdea?.hook === idea.hook && (
                            <div className="mt-3 pt-3 border-t">
                              <button
                                onClick={(e) => { e.stopPropagation(); handleGeneratePost(idea); }}
                                className="w-full py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 flex items-center justify-center gap-1"
                              >
                                <FileText className="w-4 h-4" />
                                Generate Full Post
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                      
                      {!contentIdeas?.ideas?.length && (
                        <div className="text-center py-8 text-gray-500">
                          <Lightbulb className="w-12 h-12 mx-auto mb-3 opacity-50" />
                          <p>Select a trending topic or click "Generate More" to get content ideas</p>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* Generated Post Tab */}
                  {contentCreatorTab === 'post' && (
                    <div className="space-y-4">
                      {generatedPost?.post ? (
                        <>
                          <div className="flex items-center justify-between">
                            <h4 className="font-medium text-gray-800">Your LinkedIn Post</h4>
                            <div className="flex items-center gap-2 text-xs text-gray-500">
                              <span>Best time: {generatedPost.post.best_posting_time}</span>
                              <span>•</span>
                              <span>{generatedPost.post.estimated_reach}</span>
                            </div>
                          </div>
                          
                          {/* Post Preview */}
                          <div className="border rounded-lg p-4 bg-white">
                            <div className="flex items-center gap-3 mb-3">
                              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold">
                                {brand?.name?.charAt(0) || 'B'}
                              </div>
                              <div>
                                <p className="font-semibold text-gray-900">{brand?.name || 'Your Brand'}</p>
                                <p className="text-xs text-gray-500">{brand?.tagline || brand?.industry}</p>
                              </div>
                            </div>
                            <div className="prose prose-sm max-w-none">
                              <pre className="whitespace-pre-wrap font-sans text-gray-800 text-sm leading-relaxed bg-transparent border-0 p-0">
                                {generatedPost.post.content}
                              </pre>
                            </div>
                            <div className="mt-3 flex flex-wrap gap-1">
                              {generatedPost.post.hashtags?.map((tag, i) => (
                                <span key={i} className="text-xs text-blue-600">#{tag}</span>
                              ))}
                            </div>
                          </div>
                          
                          {/* Editing Suggestions */}
                          {generatedPost.editing_suggestions?.length > 0 && (
                            <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                              <p className="text-xs font-medium text-yellow-800 mb-1">💡 Editing Tip</p>
                              <p className="text-sm text-yellow-700">{generatedPost.editing_suggestions[0]}</p>
                            </div>
                          )}
                          
                          {/* Action Buttons */}
                          <div className="flex gap-2">
                            <button
                              onClick={() => {
                                navigator.clipboard.writeText(generatedPost.post.content)
                                setCopied(true)
                                setTimeout(() => setCopied(false), 2000)
                              }}
                              className="flex-1 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center justify-center gap-2"
                            >
                              <Copy className="w-4 h-4" />
                              {copied ? 'Copied!' : 'Copy Post'}
                            </button>
                            <button
                              onClick={() => {
                                const fullText = `${generatedPost.post.content}\n\n${generatedPost.post.hashtags?.map(t => '#' + t).join(' ')}`
                                navigator.clipboard.writeText(fullText)
                                setCopied(true)
                                setTimeout(() => setCopied(false), 2000)
                              }}
                              className="py-2 px-4 border rounded-lg hover:bg-gray-50"
                            >
                              + Hashtags
                            </button>
                            <button
                              onClick={() => handleGeneratePost(selectedIdea)}
                              className="py-2 px-4 border rounded-lg hover:bg-gray-50 flex items-center gap-1"
                            >
                              <Sparkles className="w-4 h-4" />
                              Regenerate
                            </button>
                          </div>
                        </>
                      ) : (
                        <div className="text-center py-8 text-gray-500">
                          <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                          <p>Select an idea and click "Generate Full Post" to create your LinkedIn post</p>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
            
            {/* Footer */}
            <div className="p-4 border-t bg-gray-50 flex justify-between items-center">
              <p className="text-xs text-gray-500">
                {trendingTopics?.search_sources?.length > 0 && (
                  <>Sources: {trendingTopics.search_sources.slice(0, 2).map(s => { try { return new URL(s).hostname } catch { return s } }).join(', ')}</>
                )}
              </p>
              <button
                onClick={() => setShowContentCreator(false)}
                className="py-2 px-4 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* === GENERATION RESULT === */}
      {result && (
        <div id="generation-result" className="mt-8 space-y-6">
          {/* Success Header */}
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-3">
            <Check className="w-6 h-6 text-green-600" />
            <div className="flex-1">
              <h3 className="font-semibold text-green-800">Content Generated!</h3>
              <p className="text-sm text-green-600">Generated in {(result.generation_time_ms / 1000).toFixed(1)}s</p>
            </div>
            <button
              onClick={handleViewDetails}
              className="text-sm text-green-700 hover:text-green-800 font-medium flex items-center gap-1"
            >
              View Full Details <ArrowRight className="w-4 h-4" />
            </button>
          </div>
          
          <div className="space-y-6">
            {/* Generated Image */}
            {result.image_url && (
              <div className="card">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                    <Image className="w-5 h-5 text-primary-600" />
                    Generated Image
                  </h3>
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      onClick={handleDownloadImage}
                      className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
                    >
                      <Download className="w-4 h-4" />
                      Download
                    </button>
                    <button
                      onClick={handleEditInStudio}
                      disabled={generating}
                      className="text-sm bg-primary-600 text-white px-3 py-1 rounded-lg hover:bg-primary-700 flex items-center gap-1 disabled:opacity-50"
                    >
                      {generating ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Uploading...
                        </>
                      ) : (
                        <>
                          <Edit3 className="w-4 h-4" />
                          Edit in Studio
                        </>
                      )}
                    </button>
                    {(result.headline || result.body_copy) && (
                      <button
                        onClick={handleCopyLinkedIn}
                        className="px-3 py-1 bg-[#0077B5] text-white text-sm rounded-lg hover:bg-[#006396] flex items-center gap-2"
                      >
                        {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                        {copied ? 'Copied!' : 'Copy Text'}
                      </button>
                    )}
                  </div>
                </div>
                <div className="max-w-2xl mx-auto">
                  <div className="aspect-square rounded-lg overflow-hidden bg-gray-100 border">
                    <img 
                      src={result.image_url}
                      alt="Generated content"
                      className="w-full h-full object-contain"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
          
          {/* Generate Another Button */}
          <div className="flex justify-center">
            <button
              onClick={() => setResult(null)}
              className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2"
            >
              <Sparkles className="w-4 h-4" />
              Generate Another
            </button>
          </div>
        </div>
      )}
      
      {/* Tips - only show when no result */}
      {!result && (
        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <h4 className="font-medium text-blue-800 mb-2">💡 Tips for better results:</h4>
          <ul className="text-sm text-blue-700 space-y-1">
            <li>• Be specific about what you want (e.g., "summer promotion" vs just "promotion")</li>
            <li>• Mention your products if relevant to the content</li>
            <li>• Describe the mood or feeling you want to convey</li>
          </ul>
        </div>
      )}
    </div>
  )
}
