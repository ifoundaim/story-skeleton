import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './Liminal.css';

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
    <div className="liminal" onClick={handleClick} data-phase={phase}>
      <svg width="200" height="300" viewBox="0 0 200 300" className="door">
        <rect x="10" y="10" width="180" height="280" rx="20" fill="#ccc" stroke="#888" strokeWidth="4" />
      </svg>
      <div className="word">{phase}</div>
    </div>
  );
}
