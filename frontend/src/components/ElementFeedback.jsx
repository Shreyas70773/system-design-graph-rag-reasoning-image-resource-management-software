import { useState, useEffect } from 'react';
import api from '../services/api';

/**
 * Element-Level Feedback Component
 * 
 * This component provides an interactive interface for users to give
 * feedback on specific elements of a generated image. It supports:
 * - Whole image feedback (like/dislike)
 * - Element-specific feedback (click on regions)
 * - Attribute-level feedback (lighting, color, composition)
 * - Learning progress visualization
 */

const ElementFeedback = ({ 
  generationId, 
  brandId, 
  imageUrl, 
  sceneGraph,
  onFeedbackSubmitted 
}) => {
  const [feedbackMode, setFeedbackMode] = useState('whole'); // 'whole', 'element', 'attribute'
  const [selectedElement, setSelectedElement] = useState(null);
  const [hoveredElement, setHoveredElement] = useState(null);
  const [learningSummary, setLearningSummary] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [feedbackHistory, setFeedbackHistory] = useState([]);

  // Attribute options for detailed feedback
  const attributeOptions = [
    { id: 'lighting', name: 'Lighting', options: ['too_dark', 'too_bright', 'good', 'excellent'] },
    { id: 'color_saturation', name: 'Color Saturation', options: ['too_dull', 'too_vibrant', 'good', 'excellent'] },
    { id: 'composition', name: 'Composition', options: ['unbalanced', 'cramped', 'good', 'excellent'] },
    { id: 'mood', name: 'Mood/Atmosphere', options: ['wrong_mood', 'close', 'good', 'perfect'] },
    { id: 'brand_alignment', name: 'Brand Fit', options: ['off_brand', 'somewhat', 'good', 'perfect'] }
  ];

  // Load learning summary on mount
  useEffect(() => {
    loadLearningSummary();
  }, [brandId]);

  const loadLearningSummary = async () => {
    try {
      const response = await api.get(`/api/learning-summary/${brandId}`);
      setLearningSummary(response.data);
    } catch (error) {
      console.error('Failed to load learning summary:', error);
    }
  };

  // Submit whole image feedback
  const submitWholeFeedback = async (type) => {
    setSubmitting(true);
    try {
      await api.post('/api/feedback', {
        generation_id: generationId,
        brand_id: brandId,
        feedback_type: type,
        level: 'whole'
      });
      
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 2000);
      
      // Refresh learning summary
      await loadLearningSummary();
      
      if (onFeedbackSubmitted) {
        onFeedbackSubmitted({ type, level: 'whole' });
      }
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    } finally {
      setSubmitting(false);
    }
  };

  // Submit element-level feedback
  const submitElementFeedback = async (elementId, elementType, type) => {
    setSubmitting(true);
    try {
      await api.post('/api/feedback', {
        generation_id: generationId,
        brand_id: brandId,
        feedback_type: type === 'like' ? 'element_like' : 'element_dislike',
        level: 'element',
        element_type: elementType,
        element_id: elementId
      });
      
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 2000);
      
      await loadLearningSummary();
      
      if (onFeedbackSubmitted) {
        onFeedbackSubmitted({ type, level: 'element', elementId, elementType });
      }
    } catch (error) {
      console.error('Failed to submit element feedback:', error);
    } finally {
      setSubmitting(false);
      setSelectedElement(null);
    }
  };

  // Submit attribute-level feedback
  const submitAttributeFeedback = async (attribute, oldValue, newValue) => {
    setSubmitting(true);
    try {
      await api.post('/api/feedback', {
        generation_id: generationId,
        brand_id: brandId,
        feedback_type: 'edit',
        level: 'attribute',
        attribute: attribute,
        old_value: oldValue,
        new_value: newValue,
        element_type: selectedElement?.type || null
      });
      
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 2000);
      
      await loadLearningSummary();
      
      if (onFeedbackSubmitted) {
        onFeedbackSubmitted({ 
          type: 'edit', 
          level: 'attribute', 
          attribute, 
          oldValue, 
          newValue 
        });
      }
    } catch (error) {
      console.error('Failed to submit attribute feedback:', error);
    } finally {
      setSubmitting(false);
    }
  };

  // Render element overlay for interactive regions
  const renderElementOverlay = () => {
    if (!sceneGraph?.elements || feedbackMode !== 'element') return null;

    return (
      <div className="absolute inset-0 pointer-events-none">
        {sceneGraph.elements.map((element) => {
          const box = element.bounding_box;
          const isHovered = hoveredElement?.id === element.id;
          const isSelected = selectedElement?.id === element.id;

          return (
            <div
              key={element.id}
              className={`absolute border-2 rounded transition-all cursor-pointer pointer-events-auto
                ${isSelected ? 'border-blue-500 bg-blue-500/30' : 
                  isHovered ? 'border-yellow-400 bg-yellow-400/20' : 
                  'border-transparent hover:border-white/50'}`}
              style={{
                left: `${box.x * 100}%`,
                top: `${box.y * 100}%`,
                width: `${box.width * 100}%`,
                height: `${box.height * 100}%`
              }}
              onMouseEnter={() => setHoveredElement(element)}
              onMouseLeave={() => setHoveredElement(null)}
              onClick={() => setSelectedElement(element)}
            >
              {(isHovered || isSelected) && (
                <div className="absolute -top-6 left-0 bg-gray-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap">
                  {element.type}: {element.semantic_label}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  // Render element feedback panel
  const renderElementFeedbackPanel = () => {
    if (!selectedElement) return null;

    return (
      <div className="mt-4 p-4 bg-gray-800 rounded-lg">
        <h4 className="text-white font-medium mb-3">
          Feedback for: {selectedElement.type} - {selectedElement.semantic_label}
        </h4>
        
        <div className="flex gap-4">
          <button
            onClick={() => submitElementFeedback(selectedElement.id, selectedElement.type, 'like')}
            disabled={submitting}
            className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg 
                       disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <span>👍</span> This looks good
          </button>
          <button
            onClick={() => submitElementFeedback(selectedElement.id, selectedElement.type, 'dislike')}
            disabled={submitting}
            className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg
                       disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <span>👎</span> Needs improvement
          </button>
        </div>
        
        <button
          onClick={() => setSelectedElement(null)}
          className="mt-2 text-sm text-gray-400 hover:text-white"
        >
          Cancel selection
        </button>
      </div>
    );
  };

  // Render attribute feedback panel
  const renderAttributeFeedbackPanel = () => {
    if (feedbackMode !== 'attribute') return null;

    return (
      <div className="mt-4 p-4 bg-gray-800 rounded-lg">
        <h4 className="text-white font-medium mb-3">Rate specific attributes:</h4>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {attributeOptions.map((attr) => (
            <div key={attr.id} className="space-y-2">
              <label className="text-sm text-gray-300">{attr.name}</label>
              <div className="flex flex-wrap gap-2">
                {attr.options.map((option) => (
                  <button
                    key={option}
                    onClick={() => submitAttributeFeedback(attr.id, 'unknown', option)}
                    disabled={submitting}
                    className={`px-3 py-1 text-sm rounded-full border transition-colors
                      ${option === 'good' || option === 'excellent' || option === 'perfect'
                        ? 'border-green-600 text-green-400 hover:bg-green-600 hover:text-white'
                        : 'border-gray-600 text-gray-400 hover:bg-gray-600 hover:text-white'}
                      disabled:opacity-50`}
                  >
                    {option.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // Render learning progress
  const renderLearningProgress = () => {
    if (!learningSummary) return null;

    const progressPercent = Math.min(100, (learningSummary.total_feedback / 20) * 100);

    return (
      <div className="mt-6 p-4 bg-gray-800/50 rounded-lg">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-white font-medium">Learning Progress</h4>
          <span className="text-sm text-gray-400">
            {learningSummary.total_feedback} feedback samples
          </span>
        </div>
        
        <div className="w-full bg-gray-700 rounded-full h-2 mb-4">
          <div 
            className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-green-400">{learningSummary.positive_feedback}</div>
            <div className="text-xs text-gray-400">Positive</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-red-400">{learningSummary.negative_feedback}</div>
            <div className="text-xs text-gray-400">Negative</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-purple-400">{learningSummary.learned_preferences}</div>
            <div className="text-xs text-gray-400">Learned</div>
          </div>
        </div>
        
        {learningSummary.top_preferences?.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-700">
            <h5 className="text-sm text-gray-300 mb-2">What I've learned:</h5>
            <div className="flex flex-wrap gap-2">
              {learningSummary.top_preferences.slice(0, 3).map((pref, idx) => (
                <span 
                  key={idx}
                  className="px-2 py-1 bg-purple-600/30 border border-purple-500/50 text-purple-300 text-xs rounded-full"
                >
                  {pref.attribute}: {pref.value}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Success notification */}
      {showSuccess && (
        <div className="fixed top-4 right-4 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg z-50 animate-pulse">
          ✓ Feedback recorded! Learning your preferences...
        </div>
      )}
      
      {/* Feedback mode selector */}
      <div className="flex gap-2 p-1 bg-gray-800 rounded-lg">
        <button
          onClick={() => setFeedbackMode('whole')}
          className={`flex-1 px-4 py-2 rounded-lg transition-colors ${
            feedbackMode === 'whole' 
              ? 'bg-blue-600 text-white' 
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Overall
        </button>
        <button
          onClick={() => setFeedbackMode('element')}
          className={`flex-1 px-4 py-2 rounded-lg transition-colors ${
            feedbackMode === 'element' 
              ? 'bg-blue-600 text-white' 
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Elements
        </button>
        <button
          onClick={() => setFeedbackMode('attribute')}
          className={`flex-1 px-4 py-2 rounded-lg transition-colors ${
            feedbackMode === 'attribute' 
              ? 'bg-blue-600 text-white' 
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Attributes
        </button>
      </div>
      
      {/* Image with overlay */}
      <div className="relative rounded-lg overflow-hidden">
        <img 
          src={imageUrl} 
          alt="Generated content" 
          className="w-full"
        />
        {renderElementOverlay()}
        
        {feedbackMode === 'element' && (
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
            <p className="text-white text-sm text-center">
              Click on any element to give specific feedback
            </p>
          </div>
        )}
      </div>
      
      {/* Whole image feedback buttons */}
      {feedbackMode === 'whole' && (
        <div className="flex gap-4">
          <button
            onClick={() => submitWholeFeedback('like')}
            disabled={submitting}
            className="flex-1 px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg
                       disabled:opacity-50 flex items-center justify-center gap-2 transition-colors"
          >
            <span className="text-xl">👍</span> Love it
          </button>
          <button
            onClick={() => submitWholeFeedback('dislike')}
            disabled={submitting}
            className="flex-1 px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg
                       disabled:opacity-50 flex items-center justify-center gap-2 transition-colors"
          >
            <span className="text-xl">👎</span> Not quite
          </button>
          <button
            onClick={() => submitWholeFeedback('accept')}
            disabled={submitting}
            className="flex-1 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg
                       disabled:opacity-50 flex items-center justify-center gap-2 transition-colors"
          >
            <span className="text-xl">✓</span> Use this
          </button>
        </div>
      )}
      
      {/* Element feedback panel */}
      {feedbackMode === 'element' && renderElementFeedbackPanel()}
      
      {/* Attribute feedback panel */}
      {renderAttributeFeedbackPanel()}
      
      {/* Learning progress */}
      {renderLearningProgress()}
    </div>
  );
};

export default ElementFeedback;
