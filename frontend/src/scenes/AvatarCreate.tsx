// frontend/src/scenes/AvatarCreate.tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function AvatarCreate() {
  const [name, setName] = useState('');
  const [preset, setPreset] = useState('');
  const [customText, setCustomText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState('');
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const slugify = (value: string) =>
    value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
      .replace(/-+/g, '-');

  const handleAvatarCreation = async () => {
    if (!name || !preset) {
      setError('Please enter your name and select an archetype.');
      return;
    }
    setError(null);

    try {
      let avatarUrl: string | null = null;

      // 1) if the user picked a file, upload it first
      if (file) {
        const fd = new FormData();
        const playerId = slugify(name);
        fd.append('playerId', playerId);
        fd.append('file', file);
        const up = await axios.post('/avatar/upload', fd);
        avatarUrl = up.data.url;
        // persist it so our scene view can show it
        localStorage.setItem('avatarUrl', avatarUrl);
      }

      // 2) create the player profile on the server
      const body = {
        playerName: name,
        archetypePreset: preset,
        archetypeCustom: customText || null,
        avatarReferenceUrl: avatarUrl,
      };
      const res = await axios.post('/soulseed', body);

      // store soulSeedId so SceneView can pick up where we left off
      localStorage.setItem('soulSeedId', res.data.soulSeedId);
      navigate('/scene');
    } catch (e: any) {
      console.error(e);
      setError('Failed to create avatar. Please try again.');
    }
  };

  return (
    <div style={{ padding: 24, fontFamily: 'sans-serif', maxWidth: 600, margin: 'auto' }}>
      <h3>Avatar Creation</h3>
      {error && <p style={{ color: 'red' }}>{error}</p>}

      <input
        placeholder="Your Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        style={{ padding: 6, width: '100%' }}
      />
      <br /><br />

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
      <br /><br />

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
      <br /><br />

      <input
        type="file"
        onChange={(e) => {
          const f = e.target.files?.[0] || null;
          setFile(f);
          setPreview(f ? URL.createObjectURL(f) : '');
        }}
      />
      {preview && (
        <div style={{ marginTop: 8 }}>
          <img src={preview} alt="preview" style={{ maxWidth: 80 }} />
        </div>
      )}
      <br /><br />

      <button onClick={handleAvatarCreation} style={{ padding: '10px 20px', background: '#0069d9', color: '#fff', border: 'none', borderRadius: 4 }}>
        Confirm Avatar
      </button>
    </div>
  );
}
