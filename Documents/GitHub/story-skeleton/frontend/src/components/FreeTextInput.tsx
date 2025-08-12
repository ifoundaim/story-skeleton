// frontend/src/components/FreeTextInput.tsx

import React, { useState } from 'react';

interface FreeTextInputProps {
  playerId: string;
  sceneIndex: number;
  onChoiceGenerated: (choiceText: string) => void;
  disabled?: boolean;
}

interface FreeTextResponse {
  success: boolean;
  choice_text: string;
  mapped_text: string | null;
  error: string | null;
}

export const FreeTextInput: React.FC<FreeTextInputProps> = ({
  playerId,
  sceneIndex,
  onChoiceGenerated,
  disabled = false
}) => {
  const [userText, setUserText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!userText.trim() || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch('/choices/free', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          playerId,
          sceneIndex,
          userText: userText.trim()
        }),
      });

      const result: FreeTextResponse = await response.json();

      if (result.success) {
        onChoiceGenerated(result.choice_text);
        setUserText('');
        setIsExpanded(false);
      } else {
        setError(result.error || 'Failed to process your input');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (disabled) {
    return null;
  }

  return (
    <div className="free-text-container mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
      {!isExpanded ? (
        <button
          onClick={() => setIsExpanded(true)}
          className="w-full text-left text-blue-600 hover:text-blue-800 font-medium"
          disabled={disabled}
        >
          💭 Have a different idea? Type your own choice...
        </button>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label htmlFor="free-text" className="block text-sm font-medium text-gray-700 mb-2">
              What would you like to do?
            </label>
            <textarea
              id="free-text"
              value={userText}
              onChange={(e) => setUserText(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Describe what you want to do in this situation..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              rows={3}
              maxLength={500}
              disabled={isSubmitting}
            />
            <div className="text-xs text-gray-500 mt-1">
              {userText.length}/500 characters
            </div>
          </div>

          {error && (
            <div className="text-red-600 text-sm bg-red-50 p-2 rounded">
              {error}
            </div>
          )}

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={!userText.trim() || isSubmitting}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Processing...' : 'Submit Choice'}
            </button>
            <button
              type="button"
              onClick={() => {
                setIsExpanded(false);
                setUserText('');
                setError(null);
              }}
              className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
            >
              Cancel
            </button>
          </div>

          <div className="text-xs text-gray-600">
            <p>💡 Tip: Be specific about what you want to do. For example:</p>
            <ul className="list-disc list-inside mt-1 space-y-1">
              <li>"Ask the merchant about the ancient map"</li>
              <li>"Search the room for hidden passages"</li>
              <li>"Offer to help the villagers with their problem"</li>
            </ul>
          </div>
        </form>
      )}
    </div>
  );
};

export default FreeTextInput;

