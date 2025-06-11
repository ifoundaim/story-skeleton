import { useEffect, useState } from "react";
import axios from "axios";

function App() {
  const [phase, setPhase] = useState<"liminal" | "avatar" | "done">("liminal");
  const [liminalMessage, setLiminalMessage] = useState("");
  const [name, setName] = useState("");
  const [archetype, setArchetype] = useState("");
  const [profile, setProfile] = useState<Record<string, string> | null>(null);

  // ――― load liminal prompt ―――
  useEffect(() => {
    axios.get("http://localhost:8000/liminal").then((res) => {
      setLiminalMessage(res.data.message);
    });
  }, []);

  // ――― ritual steps ―――
  const handleRitual = async (step: string) => {
    const res = await axios.post("http://localhost:8000/liminal", { step });
    setLiminalMessage(res.data.message);
    if (res.data.advance) setPhase("avatar");
  };

  // ――― avatar creation ―――
  const handleAvatarCreation = async () => {
    if (!name || !archetype) {
      alert("Enter name and select archetype");
      return;
    }
    const res = await axios.post("http://localhost:8000/avatar", {
      name,
      archetype,
    });
    setProfile(res.data.profile);
    setPhase("done");
  };

  return (
    <div style={{ padding: 24, fontFamily: "sans-serif", maxWidth: 600, margin: "auto" }}>
      <h1>PurposePath Story</h1>

      {phase === "liminal" && (
        <>
          <p>{liminalMessage}</p>
          <div style={{ marginTop: 24 }}>
            {["ASK", "SEEK", "KNOCK"].map((s) => (
              <button key={s} style={{ marginRight: 12, padding: "8px 16px" }} onClick={() => handleRitual(s)}>
                {s}
              </button>
            ))}
          </div>
        </>
      )}

      {phase === "avatar" && (
        <>
          <h3>Avatar Creation</h3>
          <input
            placeholder="Your Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ padding: 6, width: "100%" }}
          />
          <br /><br />
          <select value={archetype} onChange={(e) => setArchetype(e.target.value)} style={{ padding: 6, width: "100%" }}>
            <option value="">Select Archetype</option>
            <option value="Visionary Dreamer">Visionary Dreamer</option>
            <option value="Sacred Union">Sacred Union</option>
            <option value="Builder Path">Builder Path</option>
            <option value="Healer Path">Healer Path</option>
            <option value="Guide Path">Guide Path</option>
          </select>
          <br /><br />
          <button onClick={handleAvatarCreation} style={{ padding: "8px 16px" }}>
            Confirm Avatar
          </button>
        </>
      )}

      {phase === "done" && profile && (
        <>
          <h3>Avatar Created!</h3>
          <pre style={{ background: "#eee", padding: 12 }}>{JSON.stringify(profile, null, 2)}</pre>
          <p>You’re ready to enter the world…</p>
        </>
      )}
    </div>
  );
}

export default App;
