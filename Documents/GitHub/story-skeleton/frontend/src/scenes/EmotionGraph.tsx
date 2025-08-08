import React, { useEffect, useState } from "react";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from "recharts";

const EMOTION_DIMENSIONS = [
  "joy", "grief", "awe", "fear", "desire", "disgust", "peace", "rage"
];

export interface EmotionGraphProps {
  playerId: string;
}

interface EmotionLogEntry {
  sceneTag: string;
  delta: number[];
}

interface EmotionState {
  vector: number[];
  log: EmotionLogEntry[];
}

export const EmotionGraph: React.FC<EmotionGraphProps> = ({ playerId }) => {
  const [emotion, setEmotion] = useState<EmotionState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!playerId) return;
    fetch(`/emotion/${playerId}`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch emotion state");
        return res.json();
      })
      .then(setEmotion)
      .catch((e) => setError(e.message));
  }, [playerId]);

  if (error) return <div className="text-red-500">Error: {error}</div>;
  if (!emotion) return <div>Loading emotion...</div>;

  // Prepare data for radar chart
  const data = EMOTION_DIMENSIONS.map((dim, i) => ({
    emotion: dim,
    value: emotion.vector[i] || 0
  }));

  return (
    <div style={{ width: "100%", height: 300 }}>
      <h3 className="font-bold mb-2">Emotional State</h3>
      <ResponsiveContainer width="100%" height="90%">
        <RadarChart data={data} outerRadius={100}>
          <PolarGrid />
          <PolarAngleAxis dataKey="emotion" />
          <PolarRadiusAxis domain={[-1, 1]} tickCount={5} />
          <Radar name="Emotion" dataKey="value" stroke="#8884d8" fill="#8884d8" fillOpacity={0.6} />
          <Tooltip formatter={(v: number) => v.toFixed(2)} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default EmotionGraph; 