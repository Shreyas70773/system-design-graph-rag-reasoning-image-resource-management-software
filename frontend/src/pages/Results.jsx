import { useParams, useLocation, Link, useNavigate } from 'react-router-dom'
import { 
  CheckCircle, Download, RefreshCw, 
  Image, Palette, ArrowLeft, Copy, Check,
  ThumbsUp, ThumbsDown, Eye, GitBranch,
  Database, Zap, Clock, ChevronDown, ChevronUp,
  Sparkles, AlertCircle, Brain, Send, Edit3,
  MessageCircle, Network, Circle, ArrowRight,
  Play, Loader2
} from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import { 
  submitFeedback, 
  submitAdvancedFeedback, 
  getLearningSummary,
  generateWithBrandDNA,
  getBrandGraph
} from '../services/api'

export default function Results() {
  const { brandId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { result: initialResult, prompt: initialPrompt, brandName, isAdvanced, pipelineExecutionId } = location.state || {}
  
  const [result, setResult] = useState(initialResult)
  const [prompt, setPrompt] = useState(initialPrompt)
  const [copied, setCopied] = useState(false)
  const [feedbackGiven, setFeedbackGiven] = useState(null)
  const [feedbackLoading, setFeedbackLoading] = useState(false)
  const [showPipeline, setShowPipeline] = useState(true)
  const [showGraph, setShowGraph] = useState(true)
  const [learningSummary, setLearningSummary] = useState(null)
  const [pipelineData, setPipelineData] = useState(null)
  const [loadingPipeline, setLoadingPipeline] = useState(false)
  
  // Editable text fields
  const [editableHeadline, setEditableHeadline] = useState(initialResult?.headline || '')
  const [editableBody, setEditableBody] = useState(initialResult?.body_copy || '')
  const [isEditingText, setIsEditingText] = useState(false)
  
  // Chat interface
  const [chatMessages, setChatMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [isProcessingChat, setIsProcessingChat] = useState(false)
  const chatEndRef = useRef(null)
  
  // Graph visualization data
  const [graphNodes, setGraphNodes] = useState([])
  const [graphEdges, setGraphEdges] = useState([])
  
  // Update editable text when result changes
  useEffect(() => {
    if (result) {
      setEditableHeadline(result.headline || '')
      setEditableBody(result.body_copy || '')
    }
  }, [result])
  
  // Fetch pipeline data and real graph data
  useEffect(() => {
    const execId = result?.pipeline_execution_id || pipelineExecutionId
    if (execId) {
      fetchPipelineData(execId)
    }
    fetchLearningSummary()
    // Fetch real graph data from backend
    fetchRealGraphData()
  }, [result, pipelineExecutionId])
  
  const fetchRealGraphData = async () => {
    try {
      const graphData = await getBrandGraph(brandId)
      if (graphData?.graph) {
        // Convert backend graph format to frontend visualization format
        const nodes = graphData.graph.nodes.map((node, index) => {
          // Calculate positions in a circular layout
          const nodeTypes = ['brand', 'color', 'style', 'composition', 'product', 'character', 'learned']
          const typeIndex = nodeTypes.indexOf(node.type) || 0
          const angle = (index / graphData.graph.nodes.length) * 2 * Math.PI
          const radius = node.type === 'brand' ? 0 : 120
          
          return {
            id: node.id,
            label: node.label || node.type,
            type: node.type,
            x: 250 + radius * Math.cos(angle),
            y: 160 + radius * Math.sin(angle)
          }
        })
        
        const edges = graphData.graph.edges.map(edge => ({
          from: edge.source,
          to: edge.target,
          label: edge.type?.replace(/_/g, ' '),
          color: getEdgeColor(edge.type),
          dashed: false
        }))
        
        setGraphNodes(nodes)
        setGraphEdges(edges)
      }
    } catch (err) {
      console.error('Failed to fetch graph data:', err)
      // Fallback to basic visualization
      buildGraphVisualization(null)
    }
  }
  
  const getEdgeColor = (type) => {
    const colors = {
      'HAS_COLOR': '#f59e0b',
      'HAS_STYLE': '#8b5cf6',
      'HAS_COMPOSITION': '#06b6d4',
      'SELLS': '#ec4899',
      'HAS_CHARACTER': '#6366f1',
      'LEARNED': '#22c55e',
      'GENERATED': '#10b981'
    }
    return colors[type] || '#6b7280'
  }
  
  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])
  
  const fetchPipelineData = async (executionId) => {
    setLoadingPipeline(true)
    try {
      const response = await fetch(`http://localhost:8000/api/advanced/pipeline-logs/${executionId}`)
      const data = await response.json()
      setPipelineData(data)
      buildGraphVisualization(data)
    } catch (err) {
      console.error('Failed to fetch pipeline data:', err)
    } finally {
      setLoadingPipeline(false)
    }
  }
  
  const buildGraphVisualization = (pipeline) => {
    const nodes = []
    const edges = []
    
    // Core nodes
    nodes.push({ id: 'brand', label: brandName || 'Brand', type: 'brand', x: 80, y: 150 })
    nodes.push({ id: 'generation', label: 'Generation', type: 'generation', x: 420, y: 150 })
    
    // Add intermediate nodes
    nodes.push({ id: 'colors', label: 'Colors', type: 'color', x: 180, y: 60 })
    nodes.push({ id: 'products', label: 'Products', type: 'product', x: 180, y: 240 })
    nodes.push({ id: 'scene', label: 'Scene Graph', type: 'scene', x: 320, y: 60 })
    nodes.push({ id: 'constraints', label: 'Constraints', type: 'constraint', x: 320, y: 240 })
    
    // Core edges
    edges.push({ from: 'brand', to: 'colors', label: 'HAS_COLOR', color: '#3b82f6' })
    edges.push({ from: 'brand', to: 'products', label: 'SELLS', color: '#3b82f6' })
    edges.push({ from: 'colors', to: 'scene', label: 'APPLIED_TO', color: '#8b5cf6' })
    edges.push({ from: 'products', to: 'constraints', label: 'CREATES', color: '#8b5cf6' })
    edges.push({ from: 'scene', to: 'generation', label: 'COMPILED', color: '#10b981' })
    edges.push({ from: 'constraints', to: 'generation', label: 'ENFORCED', color: '#10b981' })
    edges.push({ from: 'brand', to: 'generation', label: 'GENERATED', color: '#f59e0b', dashed: true })
    
    // Add relationships from pipeline
    if (pipeline?.steps) {
      pipeline.steps.forEach((step) => {
        if (step.relationships_created) {
          step.relationships_created.forEach((rel) => {
            edges.push({
              from: 'generation',
              to: 'brand',
              label: rel.type || 'LEARNED',
              color: '#ef4444',
              dashed: true,
              isNew: true
            })
          })
        }
      })
    }
    
    setGraphNodes(nodes)
    setGraphEdges(edges)
  }
  
  const fetchLearningSummary = async () => {
    try {
      const summary = await getLearningSummary(brandId)
      setLearningSummary(summary)
    } catch (err) {
      console.error('Failed to fetch learning summary:', err)
    }
  }
  
  const handleChatSubmit = async (e) => {
    e.preventDefault()
    if (!chatInput.trim() || isProcessingChat) return
    
    const userMessage = chatInput.trim()
    setChatInput('')
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsProcessingChat(true)
    
    setChatMessages(prev => [...prev, { role: 'assistant', content: '🤔 Processing your request with GraphRAG...', isThinking: true }])
    
    try {
      const newPrompt = `${prompt}. Additional request: ${userMessage}`
      
      // Use Brand DNA pipeline for better GraphRAG integration
      const newResult = await generateWithBrandDNA(brandId, {
        prompt: newPrompt,
        aspect_ratio: '1:1',
        use_reasoning: true
      })
      
      setResult(newResult)
      setPrompt(newPrompt)
      
      // Refresh real graph data
      fetchRealGraphData()
      
      setChatMessages(prev => {
        const filtered = prev.filter(m => !m.isThinking)
        return [...filtered, { 
          role: 'assistant', 
          content: `✅ Done! I've regenerated the image with your changes: "${userMessage}"`,
          hasAction: true
        }]
      })
      
      if (newResult.pipeline_execution_id) {
        fetchPipelineData(newResult.pipeline_execution_id)
      }
    } catch (err) {
      setChatMessages(prev => {
        const filtered = prev.filter(m => !m.isThinking)
        return [...filtered, { 
          role: 'assistant', 
          content: `❌ Error: ${err.message}`,
          isError: true
        }]
      })
    } finally {
      setIsProcessingChat(false)
    }
  }
  
  const handleRegenerateWithText = async () => {
    setIsProcessingChat(true)
    
    try {
      const textPrompt = `${prompt}. Use this exact headline: "${editableHeadline}" and body text: "${editableBody}"`
      
      // Use Brand DNA pipeline
      const newResult = await generateWithBrandDNA(brandId, {
        prompt: textPrompt,
        headline: editableHeadline,
        body_copy: editableBody,
        aspect_ratio: '1:1',
        use_reasoning: true
      })
      
      setResult(newResult)
      setIsEditingText(false)
      
      // Refresh real graph data
      fetchRealGraphData()
      
      if (newResult.pipeline_execution_id) {
        fetchPipelineData(newResult.pipeline_execution_id)
      }
    } catch (err) {
      console.error('Regeneration failed:', err)
      alert('Regeneration failed: ' + err.message)
    } finally {
      setIsProcessingChat(false)
    }
  }
  
  const handleSimpleFeedback = async (rating) => {
    if (feedbackGiven || !result?.generation_id) return
    
    setFeedbackLoading(true)
    try {
      await submitFeedback(result.generation_id, rating)
      setFeedbackGiven(rating)
      
      // Add feedback relationship to graph
      setGraphEdges(prev => [...prev, {
        from: 'generation',
        to: 'brand',
        label: rating === 'positive' ? 'POSITIVE_FEEDBACK' : 'NEGATIVE_FEEDBACK',
        color: rating === 'positive' ? '#10b981' : '#ef4444',
        dashed: true,
        isNew: true
      }])
      
      // Add new node for the learned preference
      setGraphNodes(prev => [...prev, {
        id: 'learned_' + Date.now(),
        label: rating === 'positive' ? 'Liked!' : 'Disliked',
        type: rating === 'positive' ? 'positive' : 'negative',
        x: 250,
        y: 150,
        isNew: true
      }])
      
      setTimeout(fetchLearningSummary, 1000)
    } catch (err) {
      console.error('Failed to submit feedback:', err)
    } finally {
      setFeedbackLoading(false)
    }
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
  
  const getNodeColor = (type) => {
    const colors = {
      brand: '#6366f1',
      generation: '#10b981',
      color: '#f59e0b',
      product: '#ec4899',
      scene: '#06b6d4',
      constraint: '#8b5cf6',
      positive: '#22c55e',
      negative: '#ef4444',
      default: '#6b7280'
    }
    return colors[type] || colors.default
  }
  
  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link 
          to={`/generate/${brandId}`}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-600" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">Generated Content</h1>
          <p className="text-gray-600 text-sm">For {brandName} • GraphRAG Pipeline Active</p>
        </div>
        <Link 
          to={`/generate/${brandId}`}
          className="btn-outline flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          New Generation
        </Link>
      </div>
      
      {/* GRAPH VISUALIZATION - MOST PROMINENT SECTION */}
      <div className="card mb-6 border-2 border-purple-300 bg-gradient-to-br from-purple-50 via-indigo-50 to-blue-50">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-600 rounded-lg">
              <Network className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-purple-900">Knowledge Graph - Live View</h2>
              <p className="text-sm text-purple-600">Watch relationships being built in real-time</p>
            </div>
            <span className="px-3 py-1 bg-green-500 text-white text-xs font-bold rounded-full animate-pulse">● LIVE</span>
          </div>
          <button
            onClick={() => setShowGraph(!showGraph)}
            className="text-purple-600 hover:text-purple-800 p-2"
          >
            {showGraph ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </button>
        </div>
        
        {showGraph && (
          <div className="space-y-4">
            {/* SVG Graph */}
            <div className="bg-white rounded-xl border-2 border-purple-200 p-4 shadow-inner">
              <svg width="100%" height="320" viewBox="0 0 500 320">
                <defs>
                  <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="#6b7280" />
                  </marker>
                </defs>
                
                {/* Draw edges */}
                {graphEdges.map((edge, i) => {
                  const fromNode = graphNodes.find(n => n.id === edge.from)
                  const toNode = graphNodes.find(n => n.id === edge.to)
                  if (!fromNode || !toNode) return null
                  
                  const midX = (fromNode.x + toNode.x) / 2
                  const midY = (fromNode.y + toNode.y) / 2 - 10
                  
                  return (
                    <g key={`edge-${i}`} className={edge.isNew ? 'animate-pulse' : ''}>
                      <line
                        x1={fromNode.x}
                        y1={fromNode.y}
                        x2={toNode.x}
                        y2={toNode.y}
                        stroke={edge.color}
                        strokeWidth={edge.isNew ? 4 : 2}
                        strokeDasharray={edge.dashed ? "8,4" : "0"}
                        markerEnd="url(#arrowhead)"
                      />
                      <rect
                        x={midX - 35}
                        y={midY - 8}
                        width="70"
                        height="16"
                        fill="white"
                        rx="3"
                      />
                      <text
                        x={midX}
                        y={midY + 3}
                        fill={edge.color}
                        fontSize="8"
                        textAnchor="middle"
                        fontWeight="600"
                      >
                        {edge.label}
                      </text>
                    </g>
                  )
                })}
                
                {/* Draw nodes */}
                {graphNodes.map((node) => (
                  <g key={node.id} className={`cursor-pointer ${node.isNew ? 'animate-bounce' : ''}`}>
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={node.type === 'brand' || node.type === 'generation' ? 40 : 30}
                      fill={getNodeColor(node.type)}
                      className="drop-shadow-lg"
                      stroke="white"
                      strokeWidth="3"
                    />
                    <text
                      x={node.x}
                      y={node.y + 4}
                      fill="white"
                      fontSize={node.type === 'brand' || node.type === 'generation' ? "12" : "10"}
                      textAnchor="middle"
                      fontWeight="bold"
                    >
                      {node.label.length > 12 ? node.label.substring(0, 10) + '..' : node.label}
                    </text>
                  </g>
                ))}
              </svg>
            </div>
            
            {/* Legend & Stats */}
            <div className="grid md:grid-cols-3 gap-4">
              <div className="bg-white rounded-lg p-3 border">
                <h4 className="font-bold text-gray-800 text-sm mb-2">Node Types</h4>
                <div className="space-y-1 text-xs">
                  <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-indigo-500"></div> Brand (source)</div>
                  <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-emerald-500"></div> Generation (output)</div>
                  <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-amber-500"></div> Colors</div>
                  <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-pink-500"></div> Products</div>
                  <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-cyan-500"></div> Scene Graph</div>
                  <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-purple-500"></div> Constraints</div>
                </div>
              </div>
              
              <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
                <h4 className="font-bold text-blue-800 text-sm mb-2 flex items-center gap-1">
                  <Database className="w-4 h-4" /> Read Operations
                </h4>
                <ul className="text-xs space-y-1 text-blue-700">
                  <li>✓ Brand → HAS_COLOR → Colors</li>
                  <li>✓ Brand → SELLS → Products</li>
                  <li>✓ Brand → HAS_STYLE → Preferences</li>
                  <li>✓ Products → HAS_FEATURE → Features</li>
                </ul>
              </div>
              
              <div className="bg-amber-50 rounded-lg p-3 border border-amber-200">
                <h4 className="font-bold text-amber-800 text-sm mb-2 flex items-center gap-1">
                  <GitBranch className="w-4 h-4" /> Write Operations
                </h4>
                <ul className="text-xs space-y-1 text-amber-700">
                  <li>✓ Brand → GENERATED → Content</li>
                  {feedbackGiven && (
                    <li className="text-green-700 font-bold animate-pulse">
                      ✨ NEW: LEARNED_PREFERENCE created!
                    </li>
                  )}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Main Content */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left: Image + Chat */}
        <div className="lg:col-span-2 space-y-6">
          {/* Image */}
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
              
              <div className="aspect-video rounded-lg overflow-hidden bg-gray-100 border">
                <img 
                  src={result.image_url}
                  alt="Generated content"
                  className="w-full h-full object-contain"
                />
              </div>
            </div>
          )}
          
          {/* Chat Interface */}
          <div className="card border-2 border-blue-200">
            <div className="flex items-center gap-2 mb-4">
              <MessageCircle className="w-5 h-5 text-blue-600" />
              <h3 className="font-semibold text-gray-900">Chat for Changes</h3>
              <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">AI-Powered</span>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-3 h-40 overflow-y-auto mb-3 space-y-2">
              {chatMessages.length === 0 ? (
                <div className="text-center text-gray-400 py-6">
                  <MessageCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Ask for changes naturally!</p>
                  <p className="text-xs mt-1">e.g., "Make it more colorful" or "Add a sunset background"</p>
                </div>
              ) : (
                chatMessages.map((msg, i) => (
                  <div
                    key={i}
                    className={`p-2 rounded-lg text-sm ${
                      msg.role === 'user' 
                        ? 'bg-blue-100 text-blue-900 ml-8' 
                        : msg.isError 
                          ? 'bg-red-100 text-red-900 mr-8'
                          : msg.isThinking
                            ? 'bg-gray-200 text-gray-600 mr-8 animate-pulse'
                            : 'bg-white border mr-8'
                    }`}
                  >
                    {msg.content}
                  </div>
                ))
              )}
              <div ref={chatEndRef} />
            </div>
            
            <form onSubmit={handleChatSubmit} className="flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Describe what you want to change..."
                className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                disabled={isProcessingChat}
              />
              <button
                type="submit"
                disabled={isProcessingChat || !chatInput.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
              >
                {isProcessingChat ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </button>
            </form>
          </div>
        </div>
        
        {/* Right: Text Editor + Feedback */}
        <div className="space-y-6">
          {/* Editable Text */}
          <div className="card border-2 border-green-200">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                <Edit3 className="w-5 h-5 text-green-600" />
                Edit Text
              </h3>
              <button
                onClick={() => setIsEditingText(!isEditingText)}
                className={`text-xs px-3 py-1 rounded-full ${isEditingText ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
              >
                {isEditingText ? '✏️ Editing' : 'Click to Edit'}
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="text-xs text-gray-500 font-medium block mb-1">Headline</label>
                {isEditingText ? (
                  <input
                    type="text"
                    value={editableHeadline}
                    onChange={(e) => setEditableHeadline(e.target.value)}
                    className="w-full px-3 py-2 border-2 border-green-400 rounded-lg focus:ring-2 focus:ring-green-500 text-sm"
                  />
                ) : (
                  <p className="font-semibold text-gray-900">{editableHeadline || 'No headline'}</p>
                )}
              </div>
              
              <div>
                <label className="text-xs text-gray-500 font-medium block mb-1">Body Copy</label>
                {isEditingText ? (
                  <textarea
                    value={editableBody}
                    onChange={(e) => setEditableBody(e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 border-2 border-green-400 rounded-lg focus:ring-2 focus:ring-green-500 text-sm"
                  />
                ) : (
                  <p className="text-gray-700 text-sm">{editableBody || 'No body copy'}</p>
                )}
              </div>
              
              {isEditingText && (
                <button
                  onClick={handleRegenerateWithText}
                  disabled={isProcessingChat}
                  className="w-full py-2 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg hover:from-green-700 hover:to-emerald-700 flex items-center justify-center gap-2 disabled:opacity-50 font-medium"
                >
                  {isProcessingChat ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> Regenerating...</>
                  ) : (
                    <><RefreshCw className="w-4 h-4" /> Regenerate with this text</>
                  )}
                </button>
              )}
            </div>
          </div>
          
          {/* Feedback */}
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-2">Rate & Train</h3>
            <p className="text-xs text-gray-500 mb-3">Your feedback creates new graph relationships!</p>
            
            {feedbackGiven ? (
              <div className="flex items-center gap-2 p-3 bg-green-50 rounded-lg border border-green-200">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <div>
                  <span className="text-green-700 font-medium">Feedback saved!</span>
                  <p className="text-xs text-green-600">New LEARNED_PREFERENCE relationship created</p>
                </div>
              </div>
            ) : (
              <div className="flex gap-3">
                <button
                  onClick={() => handleSimpleFeedback('positive')}
                  disabled={feedbackLoading}
                  className="flex-1 py-3 bg-green-50 hover:bg-green-100 border-2 border-green-200 rounded-lg flex items-center justify-center gap-2 text-green-700"
                >
                  <ThumbsUp className="w-5 h-5" /> Good
                </button>
                <button
                  onClick={() => handleSimpleFeedback('negative')}
                  disabled={feedbackLoading}
                  className="flex-1 py-3 bg-red-50 hover:bg-red-100 border-2 border-red-200 rounded-lg flex items-center justify-center gap-2 text-red-700"
                >
                  <ThumbsDown className="w-5 h-5" /> Poor
                </button>
              </div>
            )}
          </div>
          
          {/* Learning Stats */}
          {learningSummary && (
            <div className="card bg-gradient-to-br from-purple-50 to-indigo-50 border-purple-200">
              <div className="flex items-center gap-2 mb-3">
                <Brain className="w-5 h-5 text-purple-600" />
                <h3 className="font-semibold text-purple-900">System Learning</h3>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-white rounded-lg p-2 text-center">
                  <p className="text-2xl font-bold text-purple-600">{learningSummary.total_feedback || 0}</p>
                  <p className="text-xs text-gray-500">Feedback Given</p>
                </div>
                <div className="bg-white rounded-lg p-2 text-center">
                  <p className="text-2xl font-bold text-green-600">{learningSummary.learned_preferences || 0}</p>
                  <p className="text-xs text-gray-500">Preferences Learned</p>
                </div>
              </div>
            </div>
          )}
          
          {/* Brand Score */}
          {result.brand_score !== undefined && (
            <div className="card">
              <h3 className="font-semibold text-gray-900 mb-2">Brand Alignment</h3>
              <div className="flex items-center gap-3">
                <div className="relative w-14 h-14">
                  <svg className="w-14 h-14 transform -rotate-90">
                    <circle cx="28" cy="28" r="24" fill="none" stroke="#e5e7eb" strokeWidth="5" />
                    <circle
                      cx="28" cy="28" r="24" fill="none"
                      stroke={result.brand_score >= 0.7 ? '#22c55e' : result.brand_score >= 0.5 ? '#f59e0b' : '#ef4444'}
                      strokeWidth="5"
                      strokeDasharray={`${result.brand_score * 151} 151`}
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-sm font-bold">{Math.round(result.brand_score * 100)}%</span>
                  </div>
                </div>
                <p className={`text-sm font-medium ${result.brand_score >= 0.7 ? 'text-green-600' : result.brand_score >= 0.5 ? 'text-amber-600' : 'text-red-600'}`}>
                  {result.brand_score >= 0.7 ? 'Excellent match' : result.brand_score >= 0.5 ? 'Good match' : 'Needs improvement'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Pipeline Details */}
      <div className="card mt-6">
        <button onClick={() => setShowPipeline(!showPipeline)} className="w-full flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-amber-500" />
            <h3 className="font-semibold text-gray-900">Pipeline Execution Log</h3>
            {pipelineData?.steps && (
              <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">{pipelineData.steps.length} steps</span>
            )}
          </div>
          {showPipeline ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
        
        {showPipeline && pipelineData?.steps && (
          <div className="mt-4 space-y-2">
            {pipelineData.steps.map((step, i) => (
              <div key={i} className="border rounded-lg p-3 bg-gray-50">
                <div className="flex items-center gap-2">
                  <span>{step.stage === 'completed' ? '✅' : '🔄'}</span>
                  <span className="font-medium capitalize">{step.stage?.replace(/_/g, ' ')}</span>
                  {step.duration_ms && <span className="text-xs text-gray-500 ml-auto">{step.duration_ms.toFixed(0)}ms</span>}
                </div>
                {step.message && <p className="text-sm text-gray-600 mt-1">{step.message}</p>}
              </div>
            ))}
          </div>
        )}
        
        {showPipeline && !pipelineData && (
          <p className="mt-4 text-gray-500 text-sm">No pipeline data yet. Generate content to see execution details.</p>
        )}
      </div>
    </div>
  )
}
