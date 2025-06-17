// frontend/src/scenes/SceneView.tsx
import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';

interface Choice {
  tag: string;
  label: string;
}

interface Scene {
  sceneTag: string;
  text: string;
  choices: Choice[];
}

export default function SceneView() {
  const navigate = useNavigate();
  const soulSeedId = localStorage.getItem('soulSeedId');
  const avatarUrl = localStorage.getItem('avatarUrl') || '';

  const [scene, setScene] = useState<Scene | null>(null);
  const [trust, setTrust] = useState<number | null>(null);
  const [error, setError] = useState<string>('');

  // Generic JSON fetch
  const fetchJson = useCallback(async (url: string, opts?: RequestInit) => {
    const res = await fetch(url, opts);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
  }, []);

  const fetchTrust = useCallback(async () => {
    try {
      const trustData = await fetchJson(`/trust?soulSeedId=${soulSeedId}`);
      setTrust(typeof trustData.trust === 'number' ? trustData.trust : 0);
    } catch (err) {
      console.error('Failed to fetch trust', err);
      setTrust(0);
    }
  }, [fetchJson, soulSeedId]);

  useEffect(() => {
    if (!soulSeedId) {
      navigate('/avatar', { replace: true });
      return;
    }

    (async () => {
      try {
        const sceneData: Scene = await fetchJson('/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ soulSeedId }),
        });
        setScene(sceneData);
        await fetchTrust();
      } catch (err) {
        console.error('Failed to fetch start scene', err);
        setError('Could not load the story. Try reload.');
      }
    })();
  }, [soulSeedId, navigate, fetchJson, fetchTrust]);

  const choose = async (choiceTag: string) => {
    if (!scene) return;
    try {
      const nextScene: Scene = await fetchJson('/choose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ soulSeedId, tag: choiceTag }),
      });
      setScene(nextScene);
      await fetchTrust();
      setError('');
    } catch (err) {
      console.error('Failed to submit choice', err);
      setError('Could not advance the story. Try again?');
    }
  };

  const restart = async () => {
    await fetchJson('/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ soulSeedId }),
    });
    localStorage.removeItem('soulSeedId');
    localStorage.removeItem('avatarUrl');
    navigate('/avatar', { replace: true });
  };

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-screen space-y-4">
        <p className="text-red-600 text-lg">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg shadow hover:bg-blue-700"
        >
          Reload
        </button>
      </div>
    );
  }

  if (!scene) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-gray-500">Loading…</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.4 }}
      className="max-w-2xl mx-auto p-6 space-y-6"
    >
      {avatarUrl && (
        <img
          src={avatarUrl}
          alt="Your avatar"
          className="w-24 h-24 rounded-full mx-auto shadow-lg"
        />
      )}

      {trust !== null && (
        <div className="flex items-center justify-center space-x-2">
          <span className="font-medium">Trust:</span>
          <progress value={trust} max={10} className="w-48 h-2 rounded" />
          <span>{trust.toFixed(1)}</span>
        </div>
      )}

      <p className="text-lg">{scene.text}</p>

      {scene.choices.length > 0 ? (
        <div className="space-y-4">
          {scene.choices.map((c) => (
            <button
              key={c.tag}
              onClick={() => choose(c.tag)}
              className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg shadow hover:bg-blue-700"
            >
              {c.label}
            </button>
          ))}
        </div>
      ) : (
        <p className="italic">The End.</p>
      )}

      <div className="flex justify-center">
        <button
          onClick={restart}
          className="mt-6 px-5 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
        >
          Restart
        </button>
      </div>
    </motion.div>
  );
}
