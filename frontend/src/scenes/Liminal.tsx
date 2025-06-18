import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import axios from 'axios';

const phases = ['ASK', 'SEEK', 'KNOCK'] as const;

type Phase = typeof phases[number];

export default function Liminal() {
  const [index, setIndex] = useState(0);
  const navigate = useNavigate();

  const handleClick = async () => {
    if (index < phases.length - 1) {
      setIndex((i) => i + 1);
    } else {
      // placeholder POST then navigate
      await axios.post('/soulseed', { avatarArchetype: 'Test' }).catch(() => {});
      navigate('/avatar');
    }
  };

  const phase: Phase = phases[index];

  return (
    <motion.div
      className="flex flex-col items-center justify-center w-screen h-screen bg-gray-100 cursor-pointer"
      onClick={handleClick}
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
    </motion.div>
  );
}
