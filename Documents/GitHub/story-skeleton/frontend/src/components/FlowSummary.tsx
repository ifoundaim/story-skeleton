import React, { useState, useEffect } from 'react';

interface ConsequenceChange {
  type: string;
  key: string;
  value: any;
  npc_id?: string;
  delta?: any;
}

interface ChoiceRecord {
  scene_index: number;
  text: string;
  tags: string[];
  effects: Record<string, any>;
}

interface FlowSummaryData {
  scene_range: [number, number];
  choices: ChoiceRecord[];
  consequences: ConsequenceChange[];
  fogged_branches: number;
  percent_stats: Record<string, number>;
}

interface FlowSummaryProps {
  playerId: string;
  chapter?: number;
}

const FlowSummary: React.FC<FlowSummaryProps> = ({ playerId, chapter = 1 }) => {
  const [summaryData, setSummaryData] = useState<FlowSummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchFlowSummary = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/flow/summary?player_id=${playerId}&chapter=${chapter}`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch flow summary: ${response.statusText}`);
        }
        
        const data = await response.json();
        setSummaryData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchFlowSummary();
  }, [playerId, chapter]);

  if (loading) {
    return (
      <div className="flow-summary">
        <div className="loading">Loading flow summary...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flow-summary">
        <div className="error">Error: {error}</div>
      </div>
    );
  }

  if (!summaryData) {
    return (
      <div className="flow-summary">
        <div className="no-data">No flow summary data available</div>
      </div>
    );
  }

  const getConsequenceBadgeColor = (type: string): string => {
    switch (type) {
      case 'flag': return 'bg-blue-100 text-blue-800';
      case 'promise': return 'bg-green-100 text-green-800';
      case 'reputation': return 'bg-purple-100 text-purple-800';
      case 'resource': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getConsequenceIcon = (type: string): string => {
    switch (type) {
      case 'flag': return '🚩';
      case 'promise': return '🤝';
      case 'reputation': return '⭐';
      case 'resource': return '📦';
      default: return '📋';
    }
  };

  return (
    <div className="flow-summary p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Chapter {chapter} Flow Summary
        </h1>
        <p className="text-gray-600">
          Scenes {summaryData.scene_range[0] + 1} - {summaryData.scene_range[1] + 1}
        </p>
      </div>

      {/* Choices Section */}
      <div className="mb-8">
        <h2 className="text-2xl font-semibold text-gray-800 mb-4">Your Choices</h2>
        <div className="space-y-4">
          {summaryData.choices.map((choice, index) => (
            <div key={index} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-medium text-gray-900 mb-1">
                    Scene {choice.scene_index + 1}
                  </h3>
                  <p className="text-gray-700 mb-2">{choice.text}</p>
                  <div className="flex flex-wrap gap-2">
                    {choice.tags.map((tag, tagIndex) => (
                      <span
                        key={tagIndex}
                        className="px-2 py-1 bg-gray-100 text-gray-700 text-sm rounded"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Consequences Section */}
      <div className="mb-8">
        <h2 className="text-2xl font-semibold text-gray-800 mb-4">Consequences</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {summaryData.consequences.map((consequence, index) => (
            <div key={index} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-lg">{getConsequenceIcon(consequence.type)}</span>
                <span className={`px-2 py-1 text-xs font-medium rounded ${getConsequenceBadgeColor(consequence.type)}`}>
                  {consequence.type}
                </span>
              </div>
              <h3 className="font-medium text-gray-900 mb-1">{consequence.key}</h3>
              <p className="text-gray-700 text-sm mb-1">
                {typeof consequence.value === 'boolean' 
                  ? (consequence.value ? 'Active' : 'Inactive')
                  : String(consequence.value)
                }
              </p>
              {consequence.npc_id && (
                <p className="text-gray-500 text-xs">NPC: {consequence.npc_id}</p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Fogged Branches */}
      <div className="mb-8">
        <h2 className="text-2xl font-semibold text-gray-800 mb-4">Alternative Paths</h2>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-lg">🌫️</span>
            <span className="text-gray-600">Fogged Alternatives</span>
          </div>
          <p className="text-gray-700">
            {summaryData.fogged_branches} alternative story paths remain unexplored
          </p>
        </div>
      </div>

      {/* Statistics */}
      {Object.keys(summaryData.percent_stats).length > 0 && (
        <div className="mb-8">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">Statistics</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(summaryData.percent_stats).map(([key, value]) => (
              <div key={key} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
                <h3 className="font-medium text-gray-900 mb-1 capitalize">
                  {key.replace('_', ' ')}
                </h3>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{ width: `${value * 100}%` }}
                    ></div>
                  </div>
                  <span className="text-sm text-gray-600">
                    {Math.round(value * 100)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default FlowSummary;
