// frontend/src/scenes/AvatarCreate.tsx
import { useState } from 'react';
<<<<<<< HEAD
<<<<<<< HEAD
import { useNavigate } from 'react-router-dom';
=======
import { useAvatar } from '../AvatarContext';
>>>>>>> 21591e2d54e369f7ecd73f9b9dec1f71d79d7af7
=======
import { motion } from 'framer-motion';
>>>>>>> 84dcd5d (Enhance scenes with motion transitions and Tailwind)
import axios from 'axios';

export default function AvatarCreate() {
  const [name, setName] = useState('');
  const [preset, setPreset] = useState('');
  const [customText, setCustomText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState('');
<<<<<<< HEAD
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
=======
  const [profile, setProfile] = useState<Record<string, string> | null>(null);
  const { setAvatarUrl } = useAvatar();
>>>>>>> 21591e2d54e369f7ecd73f9b9dec1f71d79d7af7

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
<<<<<<< HEAD
=======
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
>>>>>>> 21591e2d54e369f7ecd73f9b9dec1f71d79d7af7
  };

  return (
<<<<<<< HEAD
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
=======
    <motion.div
      className="flex items-center justify-center min-h-screen p-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="w-full max-w-md space-y-4 text-xl font-medium">
        <h3 className="text-2xl font-bold text-center">Avatar Creation</h3>
        <input
          className="w-full p-2 border rounded-md"
          placeholder="Your Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <select
          className="w-full p-2 border rounded-md"
          value={preset}
          onChange={(e) => setPreset(e.target.value)}
        >
          <option value="">Select Archetype</option>
          <option value="Visionary Dreamer">Visionary Dreamer</option>
          <option value="Sacred Union">Sacred Union</option>
          <option value="Builder Path">Builder Path</option>
          <option value="Healer Path">Healer Path</option>
          <option value="Guide Path">Guide Path</option>
        </select>
        <label className="block">
          <span>Describe your own archetype (optional)</span>
          <textarea
            className="w-full p-2 border rounded-md mt-1"
            rows={3}
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
          />
        </label>
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
            <img src={preview} alt="preview" className="max-w-[80px]" />
          </div>
        )}
        <button
          onClick={handleAvatarCreation}
          className="px-4 py-2 text-white bg-blue-600 rounded-lg shadow hover:bg-blue-700"
        >
          Confirm Avatar
        </button>
        {profile && (
          <>
            <h3 className="text-2xl font-bold">Avatar Created!</h3>
            <pre className="p-3 bg-gray-200 whitespace-pre-wrap">
              {JSON.stringify(profile, null, 2)}
            </pre>
            <p>You’re ready to enter the world…</p>
          </>
        )}
      </div>
    </motion.div>
>>>>>>> 84dcd5d (Enhance scenes with motion transitions and Tailwind)
  );
}
