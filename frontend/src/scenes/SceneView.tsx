import { useEffect, useState } from 'react';

type Choice = { tag: string; label: string };
type Scene = { sceneTag: string; text: string; choices: Choice[] };

export default function SceneView() {
  const [scene, setScene] = useState<Scene | null>(null);
  const soulSeedId = 'demo';

  useEffect(() => {
    fetch('/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ soulSeedId }),
    })
      .then((r) => r.json())
      .then(setScene)
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
      .then(setScene)
      .catch(() => {});
  };

  if (!scene) {
    return <div>Loading...</div>;
  }

  return (
    <div style={{ padding: 24, fontFamily: 'sans-serif' }}>
      <div style={{ background: '#eee', padding: 12, borderRadius: 8 }}>
        {scene.text}
      </div>
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
