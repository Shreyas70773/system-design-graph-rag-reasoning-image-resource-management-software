import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { 
  Loader2, Sparkles, Search, Copy, Check, 
  RefreshCw, Newspaper, Linkedin, ArrowLeft,
  Building2, TrendingUp, MessageSquare, Hash,
  ChevronDown, ChevronUp, ExternalLink
} from 'lucide-react'
import { getBrand, getIndustryNews, generateLinkedInPost } from '../services/api'

const INDUSTRIES = [
  'Technology',
  'Finance',
  'Healthcare',
  'Retail',
  'Manufacturing',
  'Education',
  'Marketing',
  'Real Estate',
  'Hospitality',
  'Energy',
  'Other'
]

const POST_TYPES = [
  { id: 'news_commentary', label: 'News Commentary', desc: 'Share insights on industry news' },
  { id: 'thought_leadership', label: 'Thought Leadership', desc: 'Establish expertise with original insights' },
  { id: 'educational', label: 'Educational', desc: 'Teach your audience something valuable' },
  { id: 'engagement', label: 'Engagement', desc: 'Ask questions and spark discussion' },
]

const TONES = [
  { id: 'professional', label: 'Professional' },
  { id: 'casual', label: 'Casual & Friendly' },
  { id: 'inspirational', label: 'Inspirational' },
  { id: 'educational', label: 'Educational' },
]

export default function LinkedIn() {
  const { brandId } = useParams()
  const [brand, setBrand] = useState(null)
  const [loading, setLoading] = useState(true)
  
  // Industry & News
  const [industry, setIndustry] = useState('')
  const [customIndustry, setCustomIndustry] = useState('')
  const [newsItems, setNewsItems] = useState([])
  const [loadingNews, setLoadingNews] = useState(false)
  const [selectedNews, setSelectedNews] = useState(null)
  
  // Post Generation
  const [topic, setTopic] = useState('')
  const [postType, setPostType] = useState('news_commentary')
  const [tone, setTone] = useState('professional')
  const [brandValues, setBrandValues] = useState('')
  const [generatedPost, setGeneratedPost] = useState(null)
  const [loadingPost, setLoadingPost] = useState(false)
  const [copied, setCopied] = useState(false)
  
  // UI State
  const [expandedNews, setExpandedNews] = useState(null)
  
  useEffect(() => {
    loadBrandData()
  }, [brandId])
  
  const loadBrandData = async () => {
    try {
      const brandData = await getBrand(brandId)
      setBrand(brandData)
      // Try to infer industry from tagline or set default
      if (brandData.industry) {
        setIndustry(brandData.industry)
      }
    } catch (err) {
      console.error('Failed to load brand:', err)
    } finally {
      setLoading(false)
    }
  }
  
  const handleFetchNews = async () => {
    const selectedIndustry = industry === 'Other' ? customIndustry : industry
    if (!selectedIndustry) return
    
    setLoadingNews(true)
    try {
      const news = await getIndustryNews(selectedIndustry, brand?.name, 5)
      setNewsItems(news)
    } catch (err) {
      console.error('Failed to fetch news:', err)
    } finally {
      setLoadingNews(false)
    }
  }
  
  const handleSelectNews = (news) => {
    setSelectedNews(news)
    setTopic('') // Clear custom topic when selecting news
  }
  
  const handleGeneratePost = async () => {
    if (!selectedNews && !topic.trim()) return
    
    setLoadingPost(true)
    try {
      const post = await generateLinkedInPost({
        brand_name: brand?.name || 'Brand',
        industry: industry === 'Other' ? customIndustry : industry,
        topic: selectedNews ? null : topic,
        news_title: selectedNews?.title,
        news_summary: selectedNews?.summary,
        tone: tone,
        values: brandValues.split(',').map(v => v.trim()).filter(Boolean),
        tagline: brand?.tagline,
        post_type: postType
      })
      setGeneratedPost(post)
    } catch (err) {
      console.error('Failed to generate post:', err)
    } finally {
      setLoadingPost(false)
    }
  }
  
  const handleCopy = () => {
    if (generatedPost?.full_post) {
      navigator.clipboard.writeText(generatedPost.full_post)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
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
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to={`/dashboard/${brandId}`} className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Linkedin className="w-7 h-7 text-[#0077B5]" />
            LinkedIn Content Studio
          </h1>
          <p className="text-gray-600">Generate brand-aligned LinkedIn posts with industry insights</p>
        </div>
        {brand?.logo_url && (
          <img src={brand.logo_url} alt="" className="w-12 h-12 object-contain rounded-lg border p-1" />
        )}
      </div>
      
      <div className="grid lg:grid-cols-2 gap-8">
        {/* Left Column - Industry & News */}
        <div className="space-y-6">
          {/* Industry Selection */}
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Building2 className="w-5 h-5 text-primary-600" />
              Your Industry
            </h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select your industry for relevant news
                </label>
                <select
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  className="input"
                >
                  <option value="">Select industry...</option>
                  {INDUSTRIES.map(ind => (
                    <option key={ind} value={ind}>{ind}</option>
                  ))}
                </select>
              </div>
              
              {industry === 'Other' && (
                <input
                  type="text"
                  value={customIndustry}
                  onChange={(e) => setCustomIndustry(e.target.value)}
                  placeholder="Enter your industry (e.g., Renewable Energy, SaaS)"
                  className="input"
                />
              )}
              
              <button
                onClick={handleFetchNews}
                disabled={loadingNews || (!industry || (industry === 'Other' && !customIndustry))}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                {loadingNews ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Search className="w-4 h-4" />
                )}
                Search Industry News
              </button>
            </div>
          </div>
          
          {/* News Results */}
          {newsItems.length > 0 && (
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Newspaper className="w-5 h-5 text-primary-600" />
                Recent News
                <span className="text-sm font-normal text-gray-500">
                  (Click to use for post)
                </span>
              </h2>
              
              <div className="space-y-3">
                {newsItems.map((news, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleSelectNews(news)}
                    className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                      selectedNews === news 
                        ? 'border-primary-500 bg-primary-50' 
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-medium text-gray-900 text-sm">{news.title}</h3>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setExpandedNews(expandedNews === idx ? null : idx)
                        }}
                        className="p-1 hover:bg-gray-200 rounded"
                      >
                        {expandedNews === idx ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                    {expandedNews === idx && (
                      <p className="text-sm text-gray-600 mt-2">{news.summary}</p>
                    )}
                    {selectedNews === news && (
                      <div className="mt-2 flex items-center gap-1 text-primary-600 text-xs">
                        <Check className="w-3 h-3" />
                        Selected for post
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Custom Topic */}
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-primary-600" />
              Or Write About a Custom Topic
            </h2>
            
            <textarea
              value={topic}
              onChange={(e) => {
                setTopic(e.target.value)
                if (e.target.value) setSelectedNews(null)
              }}
              placeholder="What would you like to share insights about? E.g., 'The future of AI in customer service' or 'Tips for remote team productivity'"
              className="input min-h-[100px]"
              rows={4}
            />
          </div>
        </div>
        
        {/* Right Column - Post Generation */}
        <div className="space-y-6">
          {/* Post Settings */}
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Settings className="w-5 h-5 text-primary-600" />
              Post Settings
            </h2>
            
            <div className="space-y-4">
              {/* Post Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Post Type
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {POST_TYPES.map(type => (
                    <button
                      key={type.id}
                      onClick={() => setPostType(type.id)}
                      className={`p-3 rounded-lg border-2 text-left transition-all ${
                        postType === type.id 
                          ? 'border-primary-500 bg-primary-50' 
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="font-medium text-sm">{type.label}</div>
                      <div className="text-xs text-gray-500">{type.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Tone */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Voice & Tone
                </label>
                <div className="flex flex-wrap gap-2">
                  {TONES.map(t => (
                    <button
                      key={t.id}
                      onClick={() => setTone(t.id)}
                      className={`px-4 py-2 rounded-full text-sm transition-all ${
                        tone === t.id 
                          ? 'bg-primary-600 text-white' 
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Brand Values */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Brand Values (comma-separated)
                </label>
                <input
                  type="text"
                  value={brandValues}
                  onChange={(e) => setBrandValues(e.target.value)}
                  placeholder="innovation, quality, customer-first"
                  className="input"
                />
              </div>
              
              {/* Generate Button */}
              <button
                onClick={handleGeneratePost}
                disabled={loadingPost || (!selectedNews && !topic.trim())}
                className="btn-primary w-full flex items-center justify-center gap-2 py-3"
              >
                {loadingPost ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Sparkles className="w-5 h-5" />
                )}
                Generate LinkedIn Post
              </button>
            </div>
          </div>
          
          {/* Generated Post */}
          {generatedPost && (
            <div className="card border-2 border-primary-200">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <Linkedin className="w-5 h-5 text-[#0077B5]" />
                  Your Post
                </h2>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-500">
                    {generatedPost.character_count} chars
                  </span>
                  <button
                    onClick={handleCopy}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    title="Copy to clipboard"
                  >
                    {copied ? (
                      <Check className="w-5 h-5 text-green-600" />
                    ) : (
                      <Copy className="w-5 h-5 text-gray-600" />
                    )}
                  </button>
                  <button
                    onClick={handleGeneratePost}
                    disabled={loadingPost}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    title="Regenerate"
                  >
                    <RefreshCw className={`w-5 h-5 text-gray-600 ${loadingPost ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              </div>
              
              {/* Post Preview */}
              <div className="bg-white border rounded-lg p-4 space-y-4">
                {/* Fake LinkedIn header */}
                <div className="flex items-center gap-3">
                  {brand?.logo_url ? (
                    <img src={brand.logo_url} alt="" className="w-12 h-12 rounded-full object-contain border" />
                  ) : (
                    <div className="w-12 h-12 rounded-full bg-gray-200 flex items-center justify-center">
                      <Building2 className="w-6 h-6 text-gray-400" />
                    </div>
                  )}
                  <div>
                    <div className="font-semibold text-gray-900">{brand?.name || 'Your Brand'}</div>
                    <div className="text-xs text-gray-500">Just now • 🌐</div>
                  </div>
                </div>
                
                {/* Post content */}
                <div className="whitespace-pre-wrap text-sm text-gray-800 leading-relaxed">
                  {generatedPost.full_post}
                </div>
                
                {/* Engagement buttons (fake) */}
                <div className="flex items-center gap-6 pt-4 border-t text-gray-500 text-sm">
                  <span className="flex items-center gap-1">👍 Like</span>
                  <span className="flex items-center gap-1">💬 Comment</span>
                  <span className="flex items-center gap-1">🔄 Repost</span>
                  <span className="flex items-center gap-1">📤 Send</span>
                </div>
              </div>
              
              {/* Hashtags */}
              {generatedPost.hashtags?.length > 0 && (
                <div className="mt-4 flex items-center gap-2 flex-wrap">
                  <Hash className="w-4 h-4 text-gray-400" />
                  {generatedPost.hashtags.map((tag, i) => (
                    <span key={i} className="text-sm text-primary-600">{tag}</span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Settings icon component (if not imported)
function Settings({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  )
}
