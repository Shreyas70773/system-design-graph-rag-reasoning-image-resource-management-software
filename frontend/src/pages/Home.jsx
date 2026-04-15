import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Globe, ArrowRight, Sparkles, Palette, ShoppingBag, Image, Linkedin, Newspaper, Building2 } from 'lucide-react'
import { getActiveBrandId } from '../services/brandSession'

export default function Home() {
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  const [industry, setIndustry] = useState('')
  const [businessBrief, setBusinessBrief] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const activeBrandId = getActiveBrandId()
  
  const handleSubmit = (e) => {
    e.preventDefault()
    if (url.trim()) {
      // Navigate to onboarding with the URL and industry info
      navigate('/onboarding', { 
        state: { 
          websiteUrl: url,
          industry: industry,
          businessBrief: businessBrief
        } 
      })
    }
  }
  
  return (
    <div className="space-y-16">
      {/* Hero Section */}
      <section className="text-center py-12">
        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
          Generate <span className="text-primary-600">Brand-Aligned</span> Content
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto mb-8">
          Enter your website URL and let AI create marketing content that perfectly matches your brand identity.
        </p>
        
        {/* URL Input Form */}
        <form onSubmit={handleSubmit} className="max-w-xl mx-auto space-y-4">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Globe className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://www.yourcompany.com"
                className="input pl-10 py-3 text-lg"
                required
              />
            </div>
            <button type="submit" className="btn-primary px-6 py-3 flex items-center gap-2">
              Get Started
              <ArrowRight className="w-5 h-5" />
            </button>
          </div>
          
          {/* Toggle Advanced Options */}
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1 mx-auto"
          >
            <Building2 className="w-4 h-4" />
            {showAdvanced ? 'Hide' : 'Add'} business details (recommended)
          </button>
          
          {/* Advanced Options */}
          {showAdvanced && (
            <div className="bg-gray-50 rounded-lg p-4 space-y-4 text-left">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Your Industry
                </label>
                <select
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  className="input"
                >
                  <option value="">Select industry (optional)</option>
                  <option value="Technology">Technology</option>
                  <option value="Finance">Finance</option>
                  <option value="Healthcare">Healthcare</option>
                  <option value="Retail">Retail / E-commerce</option>
                  <option value="Manufacturing">Manufacturing</option>
                  <option value="Education">Education</option>
                  <option value="Marketing">Marketing / Agency</option>
                  <option value="Real Estate">Real Estate</option>
                  <option value="Hospitality">Hospitality / Travel</option>
                  <option value="Energy">Energy</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Brief Description
                </label>
                <textarea
                  value={businessBrief}
                  onChange={(e) => setBusinessBrief(e.target.value)}
                  placeholder="Tell us about your business in 1-2 sentences. E.g., 'We're a SaaS company providing HR automation tools for mid-size enterprises.'"
                  className="input"
                  rows={3}
                />
                <p className="text-xs text-gray-500 mt-1">
                  This helps generate more relevant industry news and content suggestions.
                </p>
              </div>
            </div>
          )}

          {activeBrandId && (
            <button
              type="button"
              onClick={() => navigate(`/dashboard/${activeBrandId}`)}
              className="text-sm text-gray-600 hover:text-gray-900 underline"
            >
              Continue with your last onboarded brand
            </button>
          )}
        </form>
      </section>
      
      {/* How It Works */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 text-center mb-8">How It Works</h2>
        <div className="grid md:grid-cols-4 gap-6">
          <StepCard 
            number={1}
            icon={<Globe className="w-6 h-6" />}
            title="Enter URL"
            description="Paste your website URL and we'll automatically extract your brand DNA and classify your industry"
          />
          <StepCard 
            number={2}
            icon={<Palette className="w-6 h-6" />}
            title="Review Brand"
            description="Check your logo, colors, and industry. Add products and brand characters."
          />
          <StepCard 
            number={3}
            icon={<Image className="w-6 h-6" />}
            title="Generate Images"
            description="Create brand-consistent marketing visuals with AI image generation"
          />
          <StepCard 
            number={4}
            icon={<Linkedin className="w-6 h-6" />}
            title="Create Posts"
            description="Get industry news and generate LinkedIn posts with your brand voice"
          />
        </div>
      </section>
      
      {/* Features */}
      <section className="bg-white rounded-2xl p-8 shadow-sm">
        <h2 className="text-2xl font-bold text-gray-900 text-center mb-8">Key Features</h2>
        <div className="grid md:grid-cols-3 gap-8">
          <FeatureCard 
            icon={<Sparkles className="w-8 h-8 text-primary-600" />}
            title="AI-Powered Generation"
            description="Using GraphRAG for brand context retrieval and multi-provider image generation for visual content."
          />
          <FeatureCard 
            icon={<Newspaper className="w-8 h-8 text-primary-600" />}
            title="Industry Intelligence"
            description="Real-time industry news via Perplexity API to create timely, relevant LinkedIn content."
          />
          <FeatureCard 
            icon={<Globe className="w-8 h-8 text-primary-600" />}
            title="Graph-Powered Context"
            description="Neo4j knowledge graph stores your brand relationships and learns from feedback."
          />
        </div>
      </section>
    </div>
  )
}

function StepCard({ number, icon, title, description }) {
  return (
    <div className="text-center">
      <div className="relative inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-full mb-4">
        <span className="text-primary-600">{icon}</span>
        <span className="absolute -top-1 -right-1 w-6 h-6 bg-primary-600 text-white text-sm font-bold rounded-full flex items-center justify-center">
          {number}
        </span>
      </div>
      <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-600 text-sm">{description}</p>
    </div>
  )
}

function FeatureCard({ icon, title, description }) {
  return (
    <div className="text-center">
      <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-50 rounded-xl mb-4">
        {icon}
      </div>
      <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-600 text-sm">{description}</p>
    </div>
  )
}
