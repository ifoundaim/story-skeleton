import { useState } from 'react';
import { useAvatar } from '../AvatarContext';
import axios from 'axios';

export default function AvatarCreate() {
  const [name, setName] = useState('');
  const [preset, setPreset] = useState('');
  const [customText, setCustomText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState('');
  const [profile, setProfile] = useState<Record<string, string> | null>(null);
  const { setAvatarUrl } = useAvatar();

  const slugify = (value: string) =>
    value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
      .replace(/-+/g, '-');

  const handleAvatarCreation = async () => {
    if (!name || !preset) {
      alert('Enter name and select archetype');
      return;
    }
    let avatarUrl: string | null = null;
    if (file) {
      const fd = new FormData();
      fd.append('playerId', slugify(name));
      fd.append('file', file);
      const up = await axios.post('/avatar/upload', fd);
      avatarUrl = up.data.url;
    }
    const body = {
      playerName: name,
      archetypePreset: preset,
      archetypeCustom: customText || null,
      avatarReferenceUrl: avatarUrl,
    };
    const res = await axios.post('/soulseed', body);
    setProfile(res.data);
    const returnedUrl = (res.data && res.data.avatarReferenceUrl) || avatarUrl;
    if (returnedUrl) {
      localStorage.setItem('avatarUrl', returnedUrl);
      setAvatarUrl(returnedUrl);
    }
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
      <input
        type="file"
        onChange={(e) => {
          const f = e.target.files?.[0] || null;
          setFile(f);
          setPreview(f ? URL.createObjectURL(f) : '');
        }}
      />
      {preview && (
        <div>
          <img src={preview} alt="preview" style={{ maxWidth: 80 }} />
        </div>
      )}
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
