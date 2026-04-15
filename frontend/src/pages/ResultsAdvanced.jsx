import { useParams, useLocation, Link } from 'react-router-dom'
import { 
  CheckCircle, Download, RefreshCw, 
  Image, Palette, ArrowLeft, Copy, Check,
  ThumbsUp, ThumbsDown, Sparkles, Brain,
  Layout, Zap
} from 'lucide-react'
import { useState } from 'react'
import ElementFeedback from '../components/ElementFeedback'

/**
 * Enhanced Results Page with GraphRAG Visualization
 * 
 * This page displays generation results with:
 * - Scene graph visualization
 * - Constraint satisfaction display
 * - Element-level feedback
 * - Learning progress
 */
export default function Results() {
  const { brandId } = useParams()
  const location = useLocation()
  const { result, prompt, brandName, useAdvanced } = location.state || {}
  
  const [copied, setCopied] = useState(false)
  const [activeTab, setActiveTab] = useState('result')  // 'result', 'analysis', 'feedback'
  
  if (!result) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">No results to display</h2>
        <Link to={`/generate/${brandId}`} className="text-primary-600 hover:underline">
          Generate new content
        </Link>
      </div>
    )
  }
  
  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  
  const downloadImage = () => {
    if (result.image_url) {
      const link = document.createElement('a')
      link.href = result.image_url
      link.download = `${brandName || 'brand'}-content.png`
      link.click()
    }
  }
  
  // Render scene graph visualization
  const renderSceneAnalysis = () => {
    if (!result.scene_graph) {
      return (
        <div className="text-center py-8 text-gray-500">
          <Layout className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>Scene analysis not available</p>
          <p className="text-sm">Use Advanced Generation for scene decomposition</p>
        </div>
      )
    }
    
    const { scene_graph } = result
    
    return (
      <div className="space-y-6">
        {/* Scene Overview */}
        <div className="bg-gray-800 rounded-lg p-4">
          <h4 className="text-white font-medium mb-3 flex items-center gap-2">
            <Layout className="w-4 h-4" />
            Scene Structure
          </h4>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-400">Layout</span>
              <p className="text-white font-medium">{scene_graph.layout_type}</p>
            </div>
            <div>
              <span className="text-gray-400">Mood</span>
              <p className="text-white font-medium">{scene_graph.overall_mood}</p>
            </div>
            <div>
              <span className="text-gray-400">Aspect Ratio</span>
              <p className="text-white font-medium">{scene_graph.aspect_ratio}</p>
            </div>
            <div>
              <span className="text-gray-400">Elements</span>
              <p className="text-white font-medium">{scene_graph.elements?.length || 0}</p>
            </div>
          </div>
        </div>
        
        {/* Scene Elements */}
        <div className="bg-gray-800 rounded-lg p-4">
          <h4 className="text-white font-medium mb-3">Decomposed Elements</h4>
          
          <div className="space-y-2">
            {scene_graph.elements?.map((element, idx) => (
              <div 
                key={element.id || idx}
                className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-1 text-xs rounded ${
                    element.type === 'SUBJECT' ? 'bg-purple-600' :
                    element.type === 'BACKGROUND' ? 'bg-blue-600' :
                    element.type === 'TEXT_AREA' ? 'bg-green-600' :
                    element.type === 'CHARACTER' ? 'bg-orange-600' :
                    'bg-gray-600'
                  } text-white`}>
                    {element.type}
                  </span>
                  <span className="text-white">{element.semantic_label}</span>
                </div>
                <div className="flex items-center gap-4 text-sm text-gray-400">
                  <span>Position: {element.spatial_position}</span>
                  <span>Importance: {(element.importance * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
        
        {/* Focal Point Visualization */}
        {scene_graph.focal_point && (
          <div className="bg-gray-800 rounded-lg p-4">
            <h4 className="text-white font-medium mb-3">Focal Point</h4>
            <div className="relative aspect-square bg-gray-700 rounded-lg max-w-xs">
              <div 
                className="absolute w-4 h-4 bg-yellow-400 rounded-full transform -translate-x-1/2 -translate-y-1/2 animate-pulse"
                style={{ 
                  left: `${scene_graph.focal_point.x * 100}%`, 
                  top: `${scene_graph.focal_point.y * 100}%` 
                }}
              />
              {/* Grid lines */}
              <div className="absolute inset-0 grid grid-cols-3 grid-rows-3">
                {[...Array(9)].map((_, i) => (
                  <div key={i} className="border border-gray-600/30" />
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }
  
  // Render constraint satisfaction
  const renderConstraints = () => {
    if (!result.constraints_applied?.length) {
      return (
        <div className="text-center py-4 text-gray-500">
          <p className="text-sm">No explicit constraints applied</p>
        </div>
      )
    }
    
    return (
      <div className="bg-gray-800 rounded-lg p-4 mt-6">
        <h4 className="text-white font-medium mb-3 flex items-center gap-2">
          <Zap className="w-4 h-4 text-yellow-400" />
          Applied Constraints ({result.constraints_applied.length})
        </h4>
        
        <div className="space-y-2">
          {result.constraints_applied.map((constraint, idx) => (
            <div 
              key={constraint.id || idx}
              className="flex items-center justify-between p-2 bg-gray-700/50 rounded text-sm"
            >
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs ${
                  constraint.type === 'MUST_INCLUDE' ? 'bg-green-600' :
                  constraint.type === 'MUST_AVOID' ? 'bg-red-600' :
                  constraint.type === 'PREFER' ? 'bg-blue-600' :
                  'bg-gray-600'
                } text-white`}>
                  {constraint.type}
                </span>
                <span className="text-gray-300">{constraint.description}</span>
              </div>
              <span className="text-gray-400">
                Strength: {(constraint.strength * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
        
        {result.constraint_satisfaction_score !== undefined && (
          <div className="mt-4 pt-4 border-t border-gray-700">
            <div className="flex items-center justify-between">
              <span className="text-gray-300">Overall Satisfaction</span>
              <span className={`font-bold ${
                result.constraint_satisfaction_score >= 0.8 ? 'text-green-400' :
                result.constraint_satisfaction_score >= 0.6 ? 'text-yellow-400' :
                'text-red-400'
              }`}>
                {(result.constraint_satisfaction_score * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        )}
      </div>
    )
  }
  
  // Render compiled prompt (for transparency)
  const renderCompiledPrompt = () => {
    if (!result.compiled_prompt) return null
    
    return (
      <div className="bg-gray-800 rounded-lg p-4 mt-6">
        <h4 className="text-white font-medium mb-3 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-purple-400" />
          Compiled Prompt
        </h4>
        
        <div className="space-y-4">
          <div>
            <span className="text-xs text-green-400 uppercase">Positive Prompt</span>
            <p className="text-gray-300 text-sm mt-1 p-2 bg-gray-700/50 rounded">
              {result.compiled_prompt.positive_prompt}
            </p>
          </div>
          
          <div>
            <span className="text-xs text-red-400 uppercase">Negative Prompt</span>
            <p className="text-gray-300 text-sm mt-1 p-2 bg-gray-700/50 rounded">
              {result.compiled_prompt.negative_prompt}
            </p>
          </div>
          
          {result.compiled_prompt.style_modifiers?.length > 0 && (
            <div>
              <span className="text-xs text-blue-400 uppercase">Style Modifiers</span>
              <div className="flex flex-wrap gap-2 mt-1">
                {result.compiled_prompt.style_modifiers.map((mod, idx) => (
                  <span key={idx} className="px-2 py-1 bg-blue-600/20 text-blue-300 text-xs rounded">
                    {mod}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }
  
  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link 
          to={`/generate/${brandId}`}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-600" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            Generated Content
            {useAdvanced && (
              <span className="text-sm font-normal px-2 py-1 bg-purple-100 text-purple-700 rounded-full">
                <Brain className="w-3 h-3 inline mr-1" />
                GraphRAG
              </span>
            )}
          </h1>
          <p className="text-gray-600 text-sm">For {brandName}</p>
        </div>
        <Link 
          to={`/generate/${brandId}`}
          className="btn-outline flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Generate Again
        </Link>
      </div>
      
      {/* Tab Navigation */}
      <div className="flex gap-1 p-1 bg-gray-100 rounded-lg mb-6">
        <button
          onClick={() => setActiveTab('result')}
          className={`flex-1 px-4 py-2 rounded-lg transition-colors flex items-center justify-center gap-2 ${
            activeTab === 'result' 
              ? 'bg-white text-gray-900 shadow-sm' 
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <Image className="w-4 h-4" />
          Result
        </button>
        <button
          onClick={() => setActiveTab('analysis')}
          className={`flex-1 px-4 py-2 rounded-lg transition-colors flex items-center justify-center gap-2 ${
            activeTab === 'analysis' 
              ? 'bg-white text-gray-900 shadow-sm' 
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <Brain className="w-4 h-4" />
          Analysis
        </button>
        <button
          onClick={() => setActiveTab('feedback')}
          className={`flex-1 px-4 py-2 rounded-lg transition-colors flex items-center justify-center gap-2 ${
            activeTab === 'feedback' 
              ? 'bg-white text-gray-900 shadow-sm' 
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <ThumbsUp className="w-4 h-4" />
          Feedback
        </button>
      </div>
      
      {/* Prompt Used */}
      <div className="bg-gray-100 rounded-lg p-4 mb-6">
        <p className="text-sm text-gray-500 mb-1">Prompt:</p>
        <p className="text-gray-800">"{prompt}"</p>
      </div>
      
      {/* Tab Content */}
      {activeTab === 'result' && (
        <>
          {/* Results Grid */}
          <div className="grid md:grid-cols-2 gap-6">
            {/* Image Result */}
            {result.image_url && (
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                    <Image className="w-5 h-5 text-primary-600" />
                    Generated Image
                  </h3>
                  <button 
                    onClick={downloadImage}
                    className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
                  >
                    <Download className="w-4 h-4" />
                    Download
                  </button>
                </div>
                
                <div className="aspect-square rounded-lg overflow-hidden bg-gray-100">
                  <img 
                    src={result.image_url}
                    alt="Generated content"
                    className="w-full h-full object-cover"
                  />
                </div>
                
                {/* Colors Extracted */}
                {result.colors_used?.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm text-gray-500 mb-2 flex items-center gap-1">
                      <Palette className="w-4 h-4" />
                      Colors detected:
                    </p>
                    <div className="flex gap-2">
                      {result.colors_used.slice(0, 5).map((color, i) => (
                        <div 
                          key={i}
                          className="w-8 h-8 rounded border shadow-sm"
                          style={{ backgroundColor: color }}
                          title={color}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {/* Text Result */}
            {(result.headline || result.body_copy) && (
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-gray-900">Generated Copy</h3>
                  <button 
                    onClick={() => copyToClipboard(`${result.headline}\n\n${result.body_copy}`)}
                    className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
                  >
                    {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                
                {result.headline && (
                  <div className="mb-4">
                    <p className="text-xs uppercase text-gray-500 mb-1">Headline</p>
                    <p className="text-xl font-bold text-gray-900">{result.headline}</p>
                  </div>
                )}
                
                {result.body_copy && (
                  <div>
                    <p className="text-xs uppercase text-gray-500 mb-1">Body Copy</p>
                    <p className="text-gray-700 leading-relaxed">{result.body_copy}</p>
                  </div>
                )}
              </div>
            )}
          </div>
          
          {/* Brand Score */}
          <div className="card mt-6">
            <h3 className="font-semibold text-gray-900 mb-4">Brand Consistency Score</h3>
            
            <div className="flex items-center gap-4">
              <div className="relative w-24 h-24">
                <svg className="w-full h-full transform -rotate-90">
                  <circle cx="48" cy="48" r="40" fill="none" stroke="#e5e7eb" strokeWidth="8" />
                  <circle
                    cx="48" cy="48" r="40" fill="none"
                    stroke={result.brand_score >= 0.7 ? '#22c55e' : result.brand_score >= 0.5 ? '#f59e0b' : '#ef4444'}
                    strokeWidth="8" strokeLinecap="round"
                    strokeDasharray={`${result.brand_score * 251.2} 251.2`}
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-2xl font-bold text-gray-900">
                    {Math.round(result.brand_score * 100)}%
                  </span>
                </div>
              </div>
              
              <div className="flex-1">
                <p className={`font-medium ${
                  result.brand_score >= 0.7 ? 'text-green-600' : 
                  result.brand_score >= 0.5 ? 'text-amber-600' : 'text-red-600'
                }`}>
                  {result.brand_score >= 0.7 ? '✓ Excellent brand alignment' :
                   result.brand_score >= 0.5 ? '⚠ Moderate brand alignment' :
                   '✗ Low brand alignment'}
                </p>
              </div>
            </div>
            
            {/* Generation metadata */}
            {result.generation_time_ms && (
              <div className="mt-4 pt-4 border-t flex gap-4 text-sm text-gray-500">
                <span>Generation Time: {result.generation_time_ms}ms</span>
                <span>Model: {result.model_used || 'sdxl'}</span>
                {result.identity_preserved && (
                  <span className="text-purple-600">✓ Identity Preserved</span>
                )}
              </div>
            )}
          </div>
        </>
      )}
      
      {activeTab === 'analysis' && (
        <div className="bg-gray-900 rounded-xl p-6">
          <h3 className="text-white text-lg font-semibold mb-4">GraphRAG Analysis</h3>
          {renderSceneAnalysis()}
          {renderConstraints()}
          {renderCompiledPrompt()}
        </div>
      )}
      
      {activeTab === 'feedback' && (
        <div className="bg-gray-900 rounded-xl p-6">
          <h3 className="text-white text-lg font-semibold mb-4 flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-400" />
            Train the AI with Your Feedback
          </h3>
          <p className="text-gray-400 mb-6">
            Your feedback helps the system learn your preferences and improve future generations.
          </p>
          
          <ElementFeedback
            generationId={result.generation_id}
            brandId={brandId}
            imageUrl={result.image_url}
            sceneGraph={result.scene_graph}
            onFeedbackSubmitted={(feedback) => {
              console.log('Feedback submitted:', feedback)
            }}
          />
        </div>
      )}
      
      {/* Actions */}
      <div className="flex justify-center gap-4 mt-8">
        <Link to={`/history/${brandId}`} className="btn-secondary">
          View History
        </Link>
        <Link to={`/dashboard/${brandId}`} className="btn-primary">
          Back to Dashboard
        </Link>
      </div>
    </div>
  )
}
