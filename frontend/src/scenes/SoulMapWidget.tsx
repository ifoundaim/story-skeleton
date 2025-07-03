import React, { useEffect, useState } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';

interface SoulMapWidgetProps {
  playerId: string | null;
}

const VECTOR_SIZE = 8; // For demo, show first 8 dims

const SoulMapWidget: React.FC<SoulMapWidgetProps> = ({ playerId }: SoulMapWidgetProps) => {
  const [vector, setVector] = useState<number[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  console.log('SoulMapWidget playerId:', playerId);

  useEffect(() => {
    console.log('SoulMapWidget useEffect, playerId:', playerId);
    if (!playerId) {
      setError('No playerId');
      return;
    }
    fetch(`/soulmap/player/${playerId}`)
      .then(res => res.json())
      .then(data => {
        setVector(data.vector?.slice(0, VECTOR_SIZE) || [0,0,0,0,0,0,0,0]);
        setError(null);
      })
      .catch(() => setError('Could not load soul map.'));
  }, [playerId]);

  const data = (vector || [0,0,0,0,0,0,0,0]).map((v, i) => ({ trait: `T${i+1}`, value: v }));

  return (
    <div style={{ width: 300, height: 300 }}>
      <h3>Soul Map</h3>
      {error && <div style={{ color: 'red' }}>{error}</div>}
      {!error && (
        <>
          <ResponsiveContainer width="100%" height="80%">
            <RadarChart cx="50%" cy="50%" outerRadius="80%" data={data}>
              <PolarGrid />
              <PolarAngleAxis dataKey="trait" />
              <PolarRadiusAxis angle={30} domain={[-1, 1]} />
              <Radar name="Soul" dataKey="value" stroke="#8884d8" fill="#8884d8" fillOpacity={0.6} />
            </RadarChart>
          </ResponsiveContainer>
          {vector && vector.every(v => v === 0) && (
            <div style={{ textAlign: 'center', color: '#888', marginTop: 8 }}>
              No soul map data yet.
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default SoulMapWidget;