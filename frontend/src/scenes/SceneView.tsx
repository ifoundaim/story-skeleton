import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

type Choice = { tag: string; label: string };
type Scene = { sceneTag: string; text: string; choices: Choice[] };

export default function SceneView() {
  const [scene, setScene] = useState<Scene | null>(null);
  const [trust, setTrust] = useState(0);
  const soulSeedId = 'demo';

  const fetchTrust = () => {
    fetch(`/trust?soulSeedId=${soulSeedId}`)
      .then((r) => r.json())
      .then((d) => setTrust(Number(d.trust) || 0))
      .catch(() => {});
  };

  useEffect(() => {
    fetch('/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ soulSeedId }),
    })
      .then((r) => r.json())
      .then((data) => {
        setScene(data);
        fetchTrust();
      })
      .catch(() => {});
  }, []);

  const handleChoice = (choiceTag: string) => {
    if (!scene) return;
    fetch('/choice', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ soulSeedId, sceneTag: scene.sceneTag, choiceTag }),
    })
      .then((r) => r.json())
      .then((data) => {
        setScene(data);
        fetchTrust();
      })
      .catch(() => {});
  };

  if (!scene) {
    return <div>Loading...</div>;
  }

  const bgClass = trust > 0 ? 'bg-meadow' : 'bg-forest';
  const bgColor = trust > 0 ? '#ccff99' : '#006600';

  return (
    <div style={{ padding: 24, fontFamily: 'sans-serif' }}>
      <motion.div
        key={scene.sceneTag}
        className={`${bgClass} p-3 rounded`}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1, backgroundColor: bgColor }}
        transition={{ duration: 0.5 }}
      >
        {scene.text}
      </motion.div>
      <div style={{ marginTop: 16 }}>
        {scene.choices.map((c) => (
          <button key={c.tag} onClick={() => handleChoice(c.tag)} style={{ marginRight: 8 }}>
            {c.label}
          </button>
        ))}
      </div>
    </div>
  );
}
