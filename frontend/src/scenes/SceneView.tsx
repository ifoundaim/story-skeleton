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
  let navigate: ReturnType<typeof useNavigate> | null = null;
  try {
    navigate = useNavigate();
  } catch {
    navigate = null;
  }

  /* ───────────────────────── persistent data ───────────────────────── */
  const soulSeedId = localStorage.getItem('soulSeedId') || '';
  const avatarUrl  = localStorage.getItem('avatarUrl')   || '';

  /* ───────────────────────── local state ────────────────────────────── */
  const [scene,  setScene]  = useState<Scene | null>(null);
  const [trust,  setTrust]  = useState<number | null>(null);
  const [error,  setError]  = useState<string>('');

  /* ───────────────────────── helpers ────────────────────────────────── */
  const fetchJson = useCallback(async (url: string, opts?: RequestInit) => {
    const res = await fetch(url, opts);
    const j = await res.json();
    return j;
  }, []);

  const refreshTrust = useCallback(async () => {
    try {
      const data = await fetchJson(`/trust?soulSeedId=${soulSeedId}`);
      setTrust(typeof data.trust === 'number' ? data.trust : 0);
    } catch (e) {
      console.error('Failed to fetch trust', e);
    }
  }, [fetchJson, soulSeedId]);

  /* ───────────────────────── on-mount initial load ──────────────────── */
  useEffect(() => {


    (async () => {
      try {
        const data: Scene = await fetchJson('/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ soulSeedId }),
        });
        setScene(data);
        await refreshTrust();
      } catch (e) {
        console.error(e);
        setError('Could not load the story. Try reload.');
      }
    })();
  }, [soulSeedId, fetchJson, refreshTrust, navigate]);

  /* ───────────────────────── choose handler ─────────────────────────── */
  const handleChoice = async (choiceTag: string) => {
    if (!scene) return;
    try {
      const data: Scene = await fetchJson('/choose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        /** 
         * NOTE: sceneTag is now included – this fixes the 422 error.
         */
        body: JSON.stringify({
          soulSeedId,
          sceneTag: scene.sceneTag,   // ← NEW
          tag: choiceTag,
        }),
      });
      setScene(data);
      await refreshTrust();
      setError('');
    } catch (e) {
      console.error(e);
      setError('Could not advance the story. Try again?');
    }
  };

  /* ───────────────────────── restart handler ────────────────────────── */
  const handleRestart = async () => {
    await fetch('/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ soulSeedId }),
    }).catch(() => {});
    localStorage.removeItem('soulSeedId');
    localStorage.removeItem('avatarUrl');
    navigate?.('/avatar', { replace: true });
  };

  /* ───────────────────────── render helpers ─────────────────────────── */
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

  /* ───────────────────────── main UI ────────────────────────────────── */
  return (
    <motion.div
      key={scene.sceneTag}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.4 }}
      className="max-w-2xl mx-auto flex flex-col items-center justify-center min-h-screen p-6 space-y-6"
    >
      {/* avatar */}
      {avatarUrl && (
        <img
          src={avatarUrl}
          alt="Your avatar"
          className="w-24 h-24 rounded-full mx-auto shadow-lg"
        />
      )}

      {/* trust meter */}
      {trust !== null && (
        <div className="flex items-center justify-center space-x-2">
          <span className="font-medium">Trust:</span>
          <progress value={trust} max={10} className="w-48 h-2 rounded" />
          <span>{trust.toFixed(1)}</span>
        </div>
      )}

      {/* scene text */}
      <p
        className={
          `text-lg text-center ${trust !== null && trust < 0 ? 'bg-forest' : 'bg-meadow'}`
        }
      >
        {scene.text}
      </p>

      {/* choices / end */}
      {scene.choices.length > 0 ? (
        <div className="space-y-4 w-full">
          {scene.choices.map((c) => (
            <button
              key={c.tag}
              onClick={() => handleChoice(c.tag)}
              className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg shadow hover:bg-blue-700"
            >
              {c.label}
            </button>
          ))}
        </div>
      ) : (
        <p className="italic">The End.</p>
      )}

      {/* restart */}
      <button
        onClick={handleRestart}
        className="mt-6 px-5 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
      >
        Restart
      </button>
    </motion.div>
  );
}
