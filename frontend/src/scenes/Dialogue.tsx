import React from 'react';

interface DialogueProps {
  avatarUrl?: string;
  npcText: string;
  trust: number;
}

const Dialogue: React.FC<DialogueProps> = ({ avatarUrl = '/default-npc.png', npcText, trust }: DialogueProps) => {
  return (
    <div className="dialogue-widget" style={{ padding: 16, background: '#fff', borderRadius: 12, boxShadow: '0 2px 8px #0001', marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
        <img
          src={avatarUrl}
          alt="NPC avatar"
          style={{ width: 64, height: 64, borderRadius: '50%', marginRight: 16, objectFit: 'cover', background: '#eee' }}
        />
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Companion</div>
          <div style={{ height: 8, background: '#eee', borderRadius: 4, overflow: 'hidden' }}>
            <div style={{ width: `${Math.min(Math.max(trust, 0), 1) * 100}%`, height: '100%', background: '#4f8cff' }} />
          </div>
          <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>Trust: {trust.toFixed(2)}</div>
        </div>
      </div>
      <div style={{ fontStyle: 'italic', color: '#333', minHeight: 32 }}>{npcText || <span style={{ color: '#aaa' }}>[No dialogue]</span>}</div>
    </div>
  );
};

export default Dialogue; 