/**
 * API Service for Brand-Aligned Content Generation Platform
 * Handles all communication with the FastAPI backend
 */
import axios from 'axios';

// API base URL - change for production
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with defaults
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 2 minutes for AI generation
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred';
    console.error('API Error:', message);
    return Promise.reject(new Error(message));
  }
);

// ============== Health ==============

export const checkHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

// ============== Brands ==============

/**
 * Scrape a website for brand information
 * @param {string} websiteUrl - The URL to scrape
 * @returns {Promise<Object>} Brand data including name, tagline, logo, colors
 */
export const scrapeBrand = async (websiteUrl) => {
  const response = await api.post('/api/brands/scrape', {
    website_url: websiteUrl,
  });
  return response.data;
};

/**
 * Get brand by ID
 * @param {string} brandId - The brand ID
 * @returns {Promise<Object>} Brand data
 */
export const getBrand = async (brandId) => {
  const response = await api.get(`/api/brands/${brandId}`);
  return response.data;
};

/**
 * Check logo quality
 * @param {string} brandId - The brand ID
 * @returns {Promise<Object>} Quality assessment with score and recommendations
 */
export const checkLogoQuality = async (brandId) => {
  const response = await api.post(`/api/brands/${brandId}/logo/check-quality`);
  return response.data;
};

/**
 * Generate AI logo for brand
 * @param {string} brandId - The brand ID
 * @param {Object} options - Generation options
 * @returns {Promise<Object>} Generated logo data
 */
export const generateAILogo = async (brandId, options = {}) => {
  const response = await api.post(`/api/brands/${brandId}/logo/generate-ai`, {
    style: options.style || 'modern minimalist',
    include_text: options.includeText !== false,
  });
  return response.data;
};

// ============== Products ==============

/**
 * Parse products from text description
 * @param {string} brandId - The brand ID
 * @param {string} text - Text containing product info
 * @returns {Promise<Object>} Parsed products
 */
export const parseProductsFromText = async (brandId, text) => {
  const response = await api.post(`/api/brands/${brandId}/products/parse-text`, {
    text,
  });
  return response.data;
};

/**
 * Scrape products from URL
 * @param {string} brandId - The brand ID
 * @param {string} url - Product page URL
 * @returns {Promise<Object>} Scraped products
 */
export const scrapeProductsFromUrl = async (brandId, url) => {
  const response = await api.post(`/api/brands/${brandId}/products/scrape-url`, {
    url,
  });
  return response.data;
};

/**
 * Smart scrape a single product URL with AI extraction
 * @param {string} brandId - The brand ID
 * @param {string} url - Product page URL
 * @returns {Promise<Object>} Detailed product data (name, summary, price, image, etc.)
 */
export const smartScrapeProduct = async (brandId, url) => {
  const response = await api.post(`/api/brands/${brandId}/products/smart-scrape`, {
    url,
  });
  return response.data;
};

/**
 * Get products for a brand
 * @param {string} brandId - The brand ID
 * @returns {Promise<Object>} Products list
 */
export const getBrandProducts = async (brandId) => {
  const response = await api.get(`/api/brands/${brandId}/products`);
  return response.data;
};

// ============== Generation ==============

/**
 * Generate marketing content
 * @param {Object} params - Generation parameters
 * @param {string} params.brandId - The brand ID
 * @param {string} params.prompt - Content request/prompt
 * @param {string} params.type - 'image', 'text', or 'both'
 * @param {string} params.style - Optional style override
 * @param {Array<string>} params.productIds - Optional product IDs for context
 * @param {string} params.textLayout - Text overlay layout ('bottom_centered', 'top_centered', etc.)
 * @param {boolean} params.includeTextOverlay - Whether to overlay text on image
 * @returns {Promise<Object>} Generated content with image, headline, body, brand_score
 */
export const generateContent = async ({ 
  brandId, 
  prompt, 
  type = 'both', 
  style, 
  productIds,
  textLayout = 'bottom_centered',
  includeTextOverlay = true
}) => {
  const response = await api.post('/api/generate', {
    brand_id: brandId,
    prompt,
    type,
    style,
    product_ids: productIds,
    text_layout: textLayout,
    include_text_overlay: includeTextOverlay,
  });
  return response.data;
};

/**
 * Get available fonts for text overlay
 * @returns {Promise<Array>} List of font options
 */
export const getAvailableFonts = async () => {
  const response = await api.get('/api/fonts');
  return response.data;
};

/**
 * Get available text layout options
 * @returns {Promise<Array>} List of layout options
 */
export const getTextLayouts = async () => {
  const response = await api.get('/api/text-layouts');
  return response.data;
};

/**
 * Get generation history for a brand
 * @param {string} brandId - The brand ID
 * @param {number} limit - Max items to return
 * @returns {Promise<Array>} Generation history
 */
export const getGenerationHistory = async (brandId, limit = 10) => {
  const response = await api.get(`/api/generations/${brandId}`, {
    params: { limit },
  });
  return response.data;
};

// ============== Feedback ==============

/**
 * Submit feedback on generated content
 * @param {string} generationId - The generation ID
 * @param {string} rating - 'positive' or 'negative'
 * @param {string} comment - Optional comment
 * @returns {Promise<Object>} Feedback response
 */
export const submitFeedback = async (generationId, rating, comment = null) => {
  const response = await api.post('/api/feedback', {
    generation_id: generationId,
    rating,
    comment,
  });
  return response.data;
};

/**
 * Get feedback statistics for a brand
 * @param {string} brandId - The brand ID
 * @returns {Promise<Object>} Feedback stats
 */
export const getFeedbackStats = async (brandId) => {
  const response = await api.get(`/api/feedback/${brandId}/stats`);
  return response.data;
};

/**
 * Get all feedback for a brand
 * @param {string} brandId - The brand ID
 * @param {number} limit - Max items to return
 * @returns {Promise<Object>} Feedback list
 */
export const getBrandFeedback = async (brandId, limit = 20) => {
  const response = await api.get(`/api/feedback/${brandId}`, {
    params: { limit },
  });
  return response.data;
};

// ============== Advanced Generation (GraphRAG) ==============

/**
 * Generate content using advanced GraphRAG pipeline
 * @param {Object} params - Generation parameters
 * @param {string} params.brandId - The brand ID
 * @param {string} params.prompt - Content request/prompt
 * @param {string} params.type - 'image', 'text', or 'both'
 * @param {string} params.aspectRatio - Image aspect ratio
 * @param {boolean} params.useSceneDecomposition - Enable scene decomposition
 * @param {boolean} params.useConstraintResolution - Enable constraint resolution
 * @param {boolean} params.useLearnedPreferences - Use learned preferences
 * @param {string} params.characterId - Character ID for consistency
 * @param {boolean} params.preserveIdentity - Enable identity preservation
 * @returns {Promise<Object>} Generated content with full GraphRAG context
 */
export const generateAdvancedContent = async ({
  brandId,
  prompt,
  type = 'both',
  aspectRatio = '1:1',
  layoutType = null,
  textLayout = 'bottom_centered',
  includeTextOverlay = true,
  productIds = [],
  characterId = null,
  preserveIdentity = false,
  useSceneDecomposition = true,
  useConstraintResolution = true,
  useLearnedPreferences = true,
  qualityLevel = 'high_quality'
}) => {
  const response = await api.post('/api/advanced/generate', {
    brand_id: brandId,
    prompt,
    type,
    aspect_ratio: aspectRatio,
    layout_type: layoutType,
    text_layout: textLayout,
    include_text_overlay: includeTextOverlay,
    product_ids: productIds,
    character_id: characterId,
    preserve_identity: preserveIdentity,
    use_scene_decomposition: useSceneDecomposition,
    use_constraint_resolution: useConstraintResolution,
    use_learned_preferences: useLearnedPreferences,
    quality_level: qualityLevel
  });
  return response.data;
};

/**
 * Submit element-level feedback for learning
 * @param {Object} params - Feedback parameters
 * @param {string} params.generationId - The generation ID
 * @param {string} params.brandId - The brand ID
 * @param {string} params.feedbackType - 'WHOLE', 'ELEMENT', or 'ATTRIBUTE'
 * @param {boolean} params.isPositive - Positive or negative feedback
 * @param {string} params.elementId - Element ID (for element/attribute feedback)
 * @param {string} params.attributeKey - Attribute name (for attribute feedback)
 * @param {string} params.attributeValue - Attribute value (for attribute feedback)
 * @returns {Promise<Object>} Feedback response with learning update
 */
export const submitAdvancedFeedback = async ({
  generationId,
  brandId,
  feedbackType,
  isPositive,
  elementId = null,
  attributeKey = null,
  attributeValue = null
}) => {
  const response = await api.post('/api/advanced/feedback', {
    generation_id: generationId,
    brand_id: brandId,
    feedback_type: feedbackType,
    is_positive: isPositive,
    element_id: elementId,
    attribute_key: attributeKey,
    attribute_value: attributeValue
  });
  return response.data;
};

/**
 * Get learned preferences for a brand
 * @param {string} brandId - The brand ID
 * @returns {Promise<Object>} Learned preferences and negative patterns
 */
export const getLearnedPreferences = async (brandId) => {
  const response = await api.get(`/api/advanced/preferences/${brandId}`);
  return response.data;
};

/**
 * Get learning summary for a brand
 * @param {string} brandId - The brand ID
 * @returns {Promise<Object>} Learning progress summary
 */
export const getLearningSummary = async (brandId) => {
  const response = await api.get(`/api/advanced/learning-summary/${brandId}`);
  return response.data;
};

/**
 * Register a character for consistency
 * @param {Object} params - Character parameters
 * @param {string} params.brandId - The brand ID
 * @param {string} params.referenceImageUrl - Reference image URL
 * @param {string} params.name - Character name
 * @param {string} params.description - Character description
 * @returns {Promise<Object>} Registered character data
 */
export const registerCharacter = async ({ brandId, referenceImageUrl, name, description }) => {
  const response = await api.post('/api/advanced/characters', {
    brand_id: brandId,
    reference_image_url: referenceImageUrl,
    name,
    description
  });
  return response.data;
};

/**
 * Get characters for a brand
 * @param {string} brandId - The brand ID
 * @returns {Promise<Object>} List of characters
 */
export const getCharacters = async (brandId) => {
  const response = await api.get(`/api/advanced/characters/${brandId}`);
  return response.data;
};

/**
 * Analyze a prompt without generating
 * @param {string} prompt - The prompt to analyze
 * @param {string} aspectRatio - Aspect ratio for layout
 * @returns {Promise<Object>} Scene graph analysis
 */
export const analyzeScene = async (prompt, aspectRatio = '1:1') => {
  const response = await api.post('/api/advanced/analyze-scene', {
    prompt,
    aspect_ratio: aspectRatio
  });
  return response.data;
};

/**
 * Evaluate a generation
 * @param {Object} params - Evaluation parameters
 * @returns {Promise<Object>} Evaluation results
 */
export const evaluateGeneration = async ({ generationId, brandId, generationResult, brandContext, constraintsApplied }) => {
  const response = await api.post('/api/advanced/evaluate', {
    generation_id: generationId,
    brand_id: brandId,
    generation_result: generationResult,
    brand_context: brandContext,
    constraints_applied: constraintsApplied
  });
  return response.data;
};

/**
 * Get evaluation report for a brand
 * @param {string} brandId - The brand ID
 * @param {number} days - Days to analyze
 * @returns {Promise<Object>} Evaluation report
 */
export const getEvaluationReport = async (brandId, days = 7) => {
  const response = await api.get(`/api/advanced/evaluation-report/${brandId}`, {
    params: { days }
  });
  return response.data;
};

/**
 * Get metrics summary for a brand
 * @param {string} brandId - The brand ID
 * @returns {Promise<Object>} Metrics summary
 */
export const getMetricsSummary = async (brandId) => {
  const response = await api.get(`/api/advanced/metrics-summary/${brandId}`);
  return response.data;
};

// ========================================
// BRAND DNA v2 API - Real GraphRAG System
// ========================================

/**
 * Get complete Brand DNA with all nodes and relationships
 * @param {string} brandId - The brand ID
 * @returns {Promise<Object>} Complete Brand DNA
 */
export const getBrandDNA = async (brandId) => {
  const response = await api.get(`/api/brand-dna/${brandId}`);
  return response.data;
};

/**
 * Get Brand DNA graph structure for visualization
 * @param {string} brandId - The brand ID
 * @returns {Promise<Object>} Graph with nodes and edges
 */
export const getBrandGraph = async (brandId) => {
  const response = await api.get(`/api/brand-dna/${brandId}/graph`);
  return response.data;
};

/**
 * Generate content using real GraphRAG pipeline
 * @param {string} brandId - The brand ID
 * @param {Object} request - Generation request
 * @returns {Promise<Object>} Generation result with graph trace
 */
export const generateWithBrandDNA = async (brandId, request) => {
  const response = await api.post(`/api/brand-dna/${brandId}/generate`, request);
  return response.data;
};

/**
 * Stream generation with real-time graph trace updates
 * @param {string} brandId - The brand ID
 * @param {Object} request - Generation request
 * @param {Function} onUpdate - Callback for streaming updates
 * @returns {Promise<void>}
 */
export const streamGenerationWithBrandDNA = async (brandId, request, onUpdate) => {
  const response = await fetch(`${API_BASE_URL}/api/brand-dna/${brandId}/generate/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const lines = decoder.decode(value).split('\n');
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          onUpdate(data);
        } catch (e) {
          // Skip invalid JSON
        }
      }
    }
  }
};

/**
 * Submit semantic feedback - LLM analyzes and maps to node updates
 * @param {string} brandId - The brand ID
 * @param {Object} feedback - Semantic feedback
 * @returns {Promise<Object>} Node updates applied
 */
export const submitSemanticFeedback = async (brandId, feedback) => {
  const response = await api.post(`/api/brand-dna/${brandId}/feedback`, feedback);
  return response.data;
};

/**
 * Add a color node to Brand DNA
 * @param {string} brandId - The brand ID
 * @param {Object} color - Color data { hex, name, role, weight }
 * @returns {Promise<Object>} Created color node
 */
export const addBrandColor = async (brandId, color) => {
  const response = await api.post(`/api/brand-dna/${brandId}/colors`, color);
  return response.data;
};

/**
 * Add a style property to Brand DNA
 * @param {string} brandId - The brand ID
 * @param {Object} style - Style data { name, value, category }
 * @returns {Promise<Object>} Created style node
 */
export const addBrandStyle = async (brandId, style) => {
  const response = await api.post(`/api/brand-dna/${brandId}/styles`, style);
  return response.data;
};

/**
 * Add a product to Brand DNA
 * @param {string} brandId - The brand ID
 * @param {Object} product - Product data { name, category, referenceImageUrl, keywords }
 * @returns {Promise<Object>} Created product node
 */
export const addBrandProduct = async (brandId, product) => {
  const response = await api.post(`/api/brand-dna/${brandId}/products`, product);
  return response.data;
};

/**
 * Add a character/mascot to Brand DNA with PuLID support
 * @param {string} brandId - The brand ID
 * @param {Object} character - Character data { name, role, referenceImageUrl, features }
 * @returns {Promise<Object>} Created character node
 */
export const addBrandCharacter = async (brandId, character) => {
  const response = await api.post(`/api/brand-dna/${brandId}/characters`, character);
  return response.data;
};

/**
 * Update composition preferences
 * @param {string} brandId - The brand ID
 * @param {Object} composition - Composition rules { layoutStyle, aspectRatios, margins, textPlacement }
 * @returns {Promise<Object>} Updated composition node
 */
export const updateBrandComposition = async (brandId, composition) => {
  const response = await api.put(`/api/brand-dna/${brandId}/composition`, composition);
  return response.data;
};

/**
 * Get learning summary - all LearnedPreference nodes and their usage stats (Brand DNA v2)
 * @param {string} brandId - The brand ID
 * @returns {Promise<Object>} Learning summary with preference nodes
 */
export const getBrandDNALearningSummary = async (brandId) => {
  const response = await api.get(`/api/brand-dna/${brandId}/learning-summary`);
  return response.data;
};

/**
 * Initialize Brand DNA from website scan
 * @param {string} brandId - The brand ID
 * @param {string} websiteUrl - Website URL to scan
 * @returns {Promise<Object>} Initialized Brand DNA
 */
export const initializeBrandDNA = async (brandId, websiteUrl) => {
  const response = await api.post(`/api/brand-dna/${brandId}/initialize`, { 
    website_url: websiteUrl 
  });
  return response.data;
};

/**
 * Delete a color from Brand DNA
 * @param {string} brandId - The brand ID
 * @param {string} colorHex - The hex code to delete
 * @returns {Promise<Object>} Deletion result
 */
export const deleteBrandColor = async (brandId, colorHex) => {
  const response = await api.delete(`/api/brand-dna/${brandId}/colors/${encodeURIComponent(colorHex)}`);
  return response.data;
};

/**
 * Update brand logo URL
 * @param {string} brandId - The brand ID
 * @param {string} logoUrl - New logo URL
 * @returns {Promise<Object>} Update result
 */
export const updateBrandLogo = async (brandId, logoUrl) => {
  const response = await api.put(`/api/brand-dna/${brandId}/logo`, { logo_url: logoUrl });
  return response.data;
};

// ============== LinkedIn ==============

/**
 * Get industry news for LinkedIn posts
 * @param {string} industry - Industry sector
 * @param {string} brandName - Optional brand name for context
 * @param {number} maxItems - Maximum news items to return
 * @returns {Promise<Array>} List of news items
 */
export const getIndustryNews = async (industry, brandName = null, maxItems = 5) => {
  const response = await api.post('/api/linkedin/news', {
    industry,
    brand_name: brandName,
    max_items: maxItems
  });
  return response.data;
};

/**
 * Generate a LinkedIn post
 * @param {Object} params - Post generation parameters
 * @returns {Promise<Object>} Generated LinkedIn post
 */
export const generateLinkedInPost = async (params) => {
  const response = await api.post('/api/linkedin/generate', params);
  return response.data;
};

/**
 * Generate batch posts from industry news
 * @param {Object} params - Batch generation parameters
 * @returns {Promise<Object>} News items and generated posts
 */
export const generateLinkedInBatch = async (params) => {
  const response = await api.post('/api/linkedin/generate-batch', params);
  return response.data;
};

/**
 * Check LinkedIn module health
 * @returns {Promise<Object>} Module status
 */
export const checkLinkedInHealth = async () => {
  const response = await api.get('/api/linkedin/health');
  return response.data;
};

// ============== AI Content Creator ==============

/**
 * Discover trending topics in your industry using Perplexity AI
 * @param {Object} params - Discovery parameters
 * @returns {Promise<Object>} Trending topics and personalized angles
 */
export const discoverTrendingTopics = async (params) => {
  const response = await api.post('/api/content/discover-topics', params);
  return response.data;
};

/**
 * Generate LinkedIn content ideas
 * @param {Object} params - Generation parameters
 * @returns {Promise<Object>} Content ideas with hooks and outlines
 */
export const generateContentIdeas = async (params) => {
  const response = await api.post('/api/content/generate-ideas', params);
  return response.data;
};

/**
 * Generate a full LinkedIn post
 * @param {Object} params - Post generation parameters
 * @returns {Promise<Object>} Complete LinkedIn post with hashtags
 */
export const generateLinkedInPostAI = async (params) => {
  const response = await api.post('/api/content/generate-post', params);
  return response.data;
};

/**
 * Generate a multi-day content plan
 * @param {Object} params - Plan parameters
 * @returns {Promise<Object>} Daily content plan with themes
 */
export const generateDailyContentPlan = async (params) => {
  const response = await api.post('/api/content/daily-plan', params);
  return response.data;
};

/**
 * Check AI content creator health
 * @returns {Promise<Object>} Module status
 */
export const checkContentCreatorHealth = async () => {
  const response = await api.get('/api/content/health');
  return response.data;
};

export default api;
