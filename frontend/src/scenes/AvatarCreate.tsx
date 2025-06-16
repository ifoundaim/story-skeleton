import { useState } from 'react';
import axios from 'axios';

export default function AvatarCreate() {
  const [name, setName] = useState('');
  const [preset, setPreset] = useState('');
  const [customText, setCustomText] = useState('');
  const [profile, setProfile] = useState<Record<string, string> | null>(null);

  const handleAvatarCreation = async () => {
    if (!name || !preset) {
      alert('Enter name and select archetype');
      return;
    }
    const body = {
      playerName: name,
      archetypePreset: preset,
      archetypeCustom: customText || null,
    };
    const res = await axios.post('/avatar', body);
    setProfile(res.data.profile);
  };

  return (
    <div style={{ padding: 24, fontFamily: 'sans-serif', maxWidth: 600, margin: 'auto' }}>
      <h3>Avatar Creation</h3>
      <input
        placeholder="Your Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        style={{ padding: 6, width: '100%' }}
      />
      <br />
      <br />
      <select
        value={preset}
        onChange={(e) => setPreset(e.target.value)}
        style={{ padding: 6, width: '100%' }}
      >
        <option value="">Select Archetype</option>
        <option value="Visionary Dreamer">Visionary Dreamer</option>
        <option value="Sacred Union">Sacred Union</option>
        <option value="Builder Path">Builder Path</option>
        <option value="Healer Path">Healer Path</option>
        <option value="Guide Path">Guide Path</option>
      </select>
      <br />
      <br />
      <label>
        Describe your own archetype (optional)
        <br />
        <textarea
          rows={3}
          value={customText}
          onChange={(e) => setCustomText(e.target.value)}
          style={{ width: '100%', padding: 6 }}
        />
      </label>
      <br />
      <br />
      <button onClick={handleAvatarCreation} style={{ padding: '8px 16px' }}>
        Confirm Avatar
      </button>
      {profile && (
        <>
          <h3>Avatar Created!</h3>
          <pre style={{ background: '#eee', padding: 12 }}>{JSON.stringify(profile, null, 2)}</pre>
          <p>You’re ready to enter the world…</p>
        </>
      )}
    </div>
  );
}
