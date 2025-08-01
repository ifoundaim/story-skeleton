import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';

const phases = ['ASK', 'SEEK', 'KNOCK'] as const;
const themes = ['Visionary Dreamer', 'Stoic Guardian', 'Curious Wanderer', 'Ingenious Tactician'] as const;

type Phase = typeof phases[number];

export default function Liminal() {
  const [index, setIndex] = useState(0);
  const [ask, setAsk] = useState('');
  const [seek, setSeek] = useState('');
  const [knock, setKnock] = useState('');
  const [theme, setTheme] = useState<typeof themes[number]>(themes[0]);
  const navigate = useNavigate();

  const next = async () => {
    if (index < phases.length - 1) {
      setIndex((i) => i + 1);
      return;
    }
    const playerId = localStorage.getItem('playerId') || '';
    try {
      const res = await fetch('/ritual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          playerId,
          askText: ask.trim(),
          seekText: seek.trim(),
          knockText: knock.trim(),
          theme,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        window.dispatchEvent(new CustomEvent('ritualCompleted', { detail: data }));
        // optional global hook
        (window as any).proceedToAvatarCreation?.(data.intentVector, data.theme);
      }
    } catch {
      /* ignore network errors */
    }
    navigate('/avatar');
  };

  const phase: Phase = phases[index];
  const value = index === 0 ? ask : index === 1 ? seek : knock;
  const setValue = index === 0 ? setAsk : index === 1 ? setSeek : setKnock;
  const disabled = value.trim().length === 0;

  return (
    <motion.div
      className="flex flex-col items-center justify-center w-screen h-screen bg-gray-100"
      data-phase={phase}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5 }}
    >
      <svg width="200" height="300" viewBox="0 0 200 300">
        <rect x="10" y="10" width="180" height="280" rx="20" fill="#ccc" stroke="#888" strokeWidth="4" />
      </svg>
      <div className="mt-4 text-2xl font-medium">{phase}</div>
      <textarea
        className="mt-6 w-80 h-24 p-2 border rounded"
        maxLength={280}
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      {phase === 'KNOCK' && (
        <select
          className="mt-4 p-2 border rounded"
          value={theme}
          onChange={(e) => setTheme(e.target.value as typeof themes[number])}
        >
          {themes.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
      )}
      <button
        onClick={next}
        disabled={disabled}
        className="mt-4 px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
      >
        {index < phases.length - 1 ? 'Next' : 'Complete'}
      </button>
    </motion.div>
  );
}

