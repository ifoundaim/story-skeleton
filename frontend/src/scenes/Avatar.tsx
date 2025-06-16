import { useState } from 'react';
import axios from 'axios';

export default function Avatar() {
  const [name, setName] = useState('');
  const [archetype, setArchetype] = useState('');
  const [profile, setProfile] = useState<Record<string, string> | null>(null);
  const [uploadUrl, setUploadUrl] = useState('');

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    const res = await axios.post(`/avatar/upload?playerId=${encodeURIComponent(name || 'tmp')}`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    setUploadUrl(res.data.url);
  };

  const handleAvatarCreation = async () => {
    if (!name || !archetype) {
      alert('Enter name and select archetype');
      return;
    }
    const res = await axios.post('/avatar', {
      name,
      archetype,
      avatarReferenceUrl: uploadUrl,
    });
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
      <select value={archetype} onChange={(e) => setArchetype(e.target.value)} style={{ padding: 6, width: '100%' }}>
        <option value="">Select Archetype</option>
        <option value="Visionary Dreamer">Visionary Dreamer</option>
        <option value="Sacred Union">Sacred Union</option>
        <option value="Builder Path">Builder Path</option>
        <option value="Healer Path">Healer Path</option>
        <option value="Guide Path">Guide Path</option>
      </select>
      <br />
      <br />
      <input type="file" accept="image/*" onChange={handleFileChange} />
      {uploadUrl && (
        <div>
          <br />
          <img src={uploadUrl} alt="avatar" style={{ maxWidth: 150 }} />
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
