import React, { useEffect, useState } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts';

interface SoulMapWidgetProps {
  playerId: string | null;
  refreshKey?: number; // Add this to trigger refreshes
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

const SoulMapWidget: React.FC<SoulMapWidgetProps> = ({ playerId, refreshKey }: SoulMapWidgetProps) => {
  const [soulMapData, setSoulMapData] = useState<SoulMapData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'radar' | 'summary'>('radar');

  useEffect(() => {
    if (!playerId) return;
    setLoading(true);
    setError(null);

    fetch(`/v1/soulmap/player/${playerId}`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch soul map');
        return res.json();
      })
      .then((data) => {
        setSoulMapData(data);
      })
      .catch((err) => {
        setError(err.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [playerId, refreshKey]);

  const getRadarData = () => {
    if (!soulMapData?.traits) return [];

    // Select key traits for visualization (core virtues + archetypes)
    const keyTraits = [
      'COURAGE', 'COMPASSION', 'WISDOM', 'CREATIVITY',
      'HERO', 'SAGE', 'MAGICIAN', 'EXPLORER'
    ];

    return keyTraits.map(trait => ({
      trait: trait.toLowerCase(),
      value: soulMapData.traits[trait] || 0
    }));
  };

  const getTopTraits = () => {
    if (!soulMapData?.traits) return [];

    return Object.entries(soulMapData.traits)
      .map(([trait, value]) => ({ trait, value }))
      .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
      .slice(0, 8);
  };

  const getCategorySummary = () => {
    if (!soulMapData?.traits) return [];

    return Object.entries(SOUL_TRAIT_CATEGORIES).map(([category, traits]) => {
      const values = traits.map(trait => soulMapData.traits[trait] || 0);
      const average = values.reduce((sum, val) => sum + val, 0) / values.length;

      return {
        category,
        average,
        traits: traits.length
      };
    });
  };

  if (!playerId) {
    return <div style={{ padding: 16, color: '#666' }}>No player selected</div>;
  }

  if (loading) {
    return <div style={{ padding: 16, color: '#666' }}>Loading soul map...</div>;
  }

  if (error) {
    return <div style={{ padding: 16, color: '#f44336' }}>Error: {error}</div>;
  }

  if (!soulMapData) {
    return <div style={{ padding: 16, color: '#666' }}>No soul map data available</div>;
  }

  const radarData = getRadarData();
  const topTraits = getTopTraits();
  const categorySummary = getCategorySummary();

  return (
    <div data-testid="soul-map-widget" style={{ width: '100%', maxWidth: 400, height: 500 }}>
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

      {viewMode === 'radar' && (
        <>
          <div style={{ width: '100%', height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData} outerRadius={80}>
                <PolarGrid />
                <PolarAngleAxis dataKey="trait" />
                <PolarRadiusAxis domain={[-1, 1]} tickCount={5} />
                <Radar name="Soul" dataKey="value" stroke="#8884d8" fill="#8884d8" fillOpacity={0.6} />
                <Tooltip formatter={(v: number) => v.toFixed(2)} />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          <div style={{ marginTop: 16 }}>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '1rem' }}>Strongest Traits</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {topTraits.map((trait) => (
                <div
                  key={trait.trait}
                  style={{
                    padding: 8,
                    border: '1px solid #eee',
                    borderRadius: 6,
                    backgroundColor: '#fafafa'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 500 }}>{trait.trait.replace(/_/g, ' ')}</span>
                    <span style={{
                      fontSize: '0.8rem',
                      fontWeight: 'bold',
                      color: trait.value > 0 ? '#4caf50' : trait.value < 0 ? '#f44336' : '#666'
                    }}>
                      {trait.value > 0 ? '+' : ''}{trait.value.toFixed(2)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {viewMode === 'summary' && (
        <>
          {soulMapData.traits && (
            <div style={{ display: 'grid', gap: 16 }}>
              <div>
                <h4 style={{ margin: '0 0 8px 0', fontSize: '1rem' }}>Category Overview</h4>
                {categorySummary.map((category) => (
                  <div
                    key={category.category}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '6px 0',
                      borderBottom: '1px solid #eee'
                    }}
                  >
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
