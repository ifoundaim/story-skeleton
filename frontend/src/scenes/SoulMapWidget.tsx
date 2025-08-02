import React, { useEffect, useState } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';

interface SoulMapWidgetProps {
  playerId: string | null;
}

interface SoulMapData {
  player_id: string;
  traits: Record<string, number>;
  vector_size: number;
}

// Define the 64 SoulTraits organized by category
const SOUL_TRAIT_CATEGORIES = {
  'Core Virtues': ['COURAGE', 'COMPASSION', 'WISDOM', 'CREATIVITY', 'JUSTICE', 'TEMPERANCE', 'RESILIENCE', 'EMPATHY'],
  'Shadow Traits': ['FEAR', 'PRIDE', 'APATHY', 'SHADOW_BLEND_1', 'SHADOW_BLEND_2', 'SHADOW_BLEND_3', 'SHADOW_BLEND_4', 'SHADOW_BLEND_5'],
  'Motivations': ['SELFACTUALIZATION', 'EXTERNALVALIDATION', 'COLLECTIVE', 'MOTIVATION_BLEND_1', 'MOTIVATION_BLEND_2', 'MOTIVATION_BLEND_3', 'MOTIVATION_BLEND_4', 'MOTIVATION_BLEND_5'],
  'Archetypes': ['HERO', 'REBEL', 'SAGE', 'CAREGIVER', 'MAGICIAN', 'LOVER', 'SOVEREIGN', 'EXPLORER'],
  'Archetype Blends': ['ARCHETYPE_BLEND_1', 'ARCHETYPE_BLEND_2', 'ARCHETYPE_BLEND_3', 'ARCHETYPE_BLEND_4', 'ARCHETYPE_BLEND_5', 'ARCHETYPE_BLEND_6', 'ARCHETYPE_BLEND_7', 'ARCHETYPE_BLEND_8'],
  'Cognitive Functions': ['INTROVERTEDTHINKING', 'EXTRAVERTEDTHINKING', 'INTROVERTEDFEELING', 'EXTRAVERTEDFEELING', 'INTROVERTEDSENSING', 'EXTRAVERTEDSENSING', 'INTROVERTEDINTUITING', 'EXTRAVERTEDINTUITING'],
  'Attachment Styles': ['SECUREATTACHMENT', 'ANXIOUSATTACHMENT', 'AVOIDANTATTACHMENT', 'DISORGANIZEDATTACHMENT'],
  'Psychological Needs': ['AUTONOMY', 'COMPETENCE', 'RELATEDNESS', 'SELFCONTROL', 'MINDFULNESS', 'GRIT', 'CURIOSITY', 'PLAYFULNESS'],
  'Social Traits': ['OPTIMISM', 'VIGILANCE', 'SOCIALDOMINANCE', 'HUMILITY']
};

// Convert vector to traits dictionary
const vectorToTraits = (vector: number[]): Record<string, number> => {
  const traits: Record<string, number> = {};
  Object.values(SOUL_TRAIT_CATEGORIES).flat().forEach((trait, index) => {
    if (index < vector.length) {
      traits[trait] = vector[index];
    }
  });
  return traits;
};

const SoulMapWidget: React.FC<SoulMapWidgetProps> = ({ playerId }: SoulMapWidgetProps) => {
  const [soulMapData, setSoulMapData] = useState<SoulMapData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('Core Virtues');
  const [viewMode, setViewMode] = useState<'radar' | 'summary'>('radar');

  console.log('SoulMapWidget playerId:', playerId);

  useEffect(() => {
    console.log('SoulMapWidget useEffect, playerId:', playerId);
    if (!playerId) {
      setError('No playerId');
      return;
    }
    // Use the working endpoint for now
    fetch(`/soulmap/player/${playerId}`)
      .then(res => res.json())
      .then(data => {
        // Convert vector to traits format
        const traits = vectorToTraits(data.vector || []);
        setSoulMapData({
          player_id: data.player_id,
          traits,
          vector_size: data.vector?.length || 64
        });
        setError(null);
      })
      .catch(() => setError('Could not load soul map.'));
  }, [playerId]);

  // Prepare radar chart data for selected category
  const getRadarData = () => {
    if (!soulMapData?.traits) return [];
    
    const categoryTraits = SOUL_TRAIT_CATEGORIES[selectedCategory as keyof typeof SOUL_TRAIT_CATEGORIES] || [];
    return categoryTraits.map(trait => ({
      trait: trait.replace(/_/g, ' '),
      value: soulMapData.traits[trait] || 0
    }));
  };

  // Get top traits for summary view
  const getTopTraits = (count: number = 8) => {
    if (!soulMapData?.traits) return [];
    
    return Object.entries(soulMapData.traits)
      .sort(([,a], [,b]) => Math.abs(b) - Math.abs(a))
      .slice(0, count)
      .map(([trait, value]) => ({
        trait: trait.replace(/_/g, ' '),
        value,
        category: Object.entries(SOUL_TRAIT_CATEGORIES).find(([, traits]) => 
          traits.includes(trait)
        )?.[0] || 'Other'
      }));
  };

  // Get category summary
  const getCategorySummary = () => {
    if (!soulMapData?.traits) return [];
    
    return Object.entries(SOUL_TRAIT_CATEGORIES).map(([category, traits]) => {
      const values = traits.map(trait => soulMapData.traits[trait] || 0);
      const avgValue = values.reduce((sum, val) => sum + val, 0) / values.length;
      const maxValue = Math.max(...values.map(Math.abs));
      
      return {
        category,
        average: avgValue,
        max: maxValue,
        dominant: traits[values.indexOf(Math.max(...values))] || traits[0]
      };
    });
  };

  const radarData = getRadarData();
  const topTraits = getTopTraits();
  const categorySummary = getCategorySummary();

  return (
    <div style={{ width: '100%', maxWidth: 400, height: 500 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 'bold' }}>Soul Map</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => setViewMode('radar')}
            style={{
              padding: '4px 8px',
              fontSize: '0.8rem',
              backgroundColor: viewMode === 'radar' ? '#8884d8' : '#f0f0f0',
              color: viewMode === 'radar' ? 'white' : '#333',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer'
            }}
          >
            Radar
          </button>
          <button
            onClick={() => setViewMode('summary')}
            style={{
              padding: '4px 8px',
              fontSize: '0.8rem',
              backgroundColor: viewMode === 'summary' ? '#8884d8' : '#f0f0f0',
              color: viewMode === 'summary' ? 'white' : '#333',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer'
            }}
          >
            Summary
          </button>
        </div>
      </div>

      {error && <div style={{ color: 'red', marginBottom: 16 }}>{error}</div>}
      
      {!error && soulMapData && (
        <>
          {viewMode === 'radar' && (
            <>
              <div style={{ marginBottom: 16 }}>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px',
                    borderRadius: 4,
                    border: '1px solid #ccc',
                    fontSize: '0.9rem'
                  }}
                >
                  {Object.keys(SOUL_TRAIT_CATEGORIES).map(category => (
                    <option key={category} value={category}>{category}</option>
                  ))}
                </select>
              </div>
              
              <div style={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                    <PolarGrid />
                    <PolarAngleAxis 
                      dataKey="trait" 
                      tick={{ fontSize: 10 }}
                      tickLine={false}
                    />
                    <PolarRadiusAxis 
                      angle={30} 
                      domain={[-1, 1]} 
                      tickCount={5}
                      tick={{ fontSize: 10 }}
                    />
                    <Radar 
                      name="Soul" 
                      dataKey="value" 
                      stroke="#8884d8" 
                      fill="#8884d8" 
                      fillOpacity={0.6} 
                    />
                    <Tooltip 
                      formatter={(value: number) => value.toFixed(2)}
                      labelFormatter={(label: string) => label}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          {viewMode === 'summary' && (
            <div style={{ height: 400, overflowY: 'auto' }}>
              <div style={{ marginBottom: 16 }}>
                <h4 style={{ margin: '0 0 8px 0', fontSize: '1rem' }}>Top Traits</h4>
                {topTraits.map((trait, index) => (
                  <div key={trait.trait} style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    padding: '4px 0',
                    borderBottom: index < topTraits.length - 1 ? '1px solid #eee' : 'none'
                  }}>
                    <span style={{ fontSize: '0.9rem' }}>{trait.trait}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ 
                        fontSize: '0.8rem', 
                        color: '#666',
                        backgroundColor: '#f0f0f0',
                        padding: '2px 6px',
                        borderRadius: 8
                      }}>
                        {trait.category}
                      </span>
                      <span style={{ 
                        fontSize: '0.9rem',
                        fontWeight: 'bold',
                        color: trait.value > 0 ? '#4caf50' : trait.value < 0 ? '#f44336' : '#666'
                      }}>
                        {trait.value > 0 ? '+' : ''}{trait.value.toFixed(2)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              <div>
                <h4 style={{ margin: '0 0 8px 0', fontSize: '1rem' }}>Category Overview</h4>
                {categorySummary.map((category) => (
                  <div key={category.category} style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    padding: '6px 0',
                    borderBottom: '1px solid #eee'
                  }}>
                    <span style={{ fontSize: '0.9rem' }}>{category.category}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ 
                        fontSize: '0.8rem',
                        color: category.average > 0 ? '#4caf50' : category.average < 0 ? '#f44336' : '#666'
                      }}>
                        {category.average > 0 ? '+' : ''}{category.average.toFixed(2)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {soulMapData.traits && Object.values(soulMapData.traits).every(v => v === 0) && (
            <div style={{ textAlign: 'center', color: '#888', marginTop: 16, padding: 16, backgroundColor: '#f9f9f9', borderRadius: 8 }}>
              <div style={{ fontSize: '0.9rem', marginBottom: 8 }}>No soul map data yet.</div>
              <div style={{ fontSize: '0.8rem', color: '#666' }}>
                Make choices in the story to see your soul traits evolve.
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default SoulMapWidget;
