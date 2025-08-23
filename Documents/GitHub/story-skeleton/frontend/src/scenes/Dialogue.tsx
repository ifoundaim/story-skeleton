import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface NPCDialogueEntry {
  npc_id: string;
  name: string;
  text: string;
  trust: number;
  avatarUrl?: string;
}

interface DialogueProps {
  // Legacy single NPC props (for backward compatibility)
  avatarUrl?: string;
  npcText?: string;
  trust?: number;
  npcTextDynamic?: string;
  
  // New multi-NPC props
  npcs?: NPCDialogueEntry[];
  groupMode?: boolean;
}

const Dialogue: React.FC<DialogueProps> = ({ 
  // Legacy props
  avatarUrl = '/default-npc.png', 
  npcText = '', 
  trust = 0.5, 
  npcTextDynamic,
  // New props
  npcs = [],
  groupMode = false
}) => {
  // Animation variants for dialogue bubble
  const dialogueVariants = {
    initial: { 
      opacity: 0, 
      scale: 0.8,
      y: 10
    },
    animate: { 
      opacity: 1, 
      scale: 1,
      y: 0,
      transition: {
        type: "spring",
        damping: 20,
        stiffness: 300,
        duration: 0.6
      }
    },
    exit: {
      opacity: 0,
      scale: 0.9,
      transition: { duration: 0.2 }
    }
  }

  const dynamicTextVariants = {
    initial: { 
      opacity: 0, 
      scale: 0.95,
      x: -10
    },
    animate: { 
      opacity: 1, 
      scale: 1,
      x: 0,
      transition: {
        type: "spring",
        damping: 25,
        stiffness: 400,
        duration: 0.5
      }
    }
  }

  // Function to render a single NPC dialogue bubble
  const renderNPCDialogue = (npc: NPCDialogueEntry | null, index: number = 0) => {
    const npcData = npc || {
      npc_id: 'legacy',
      name: 'Companion',
      text: npcText,
      trust: trust,
      avatarUrl: avatarUrl
    };

    const trustColor = npcData.trust >= 0.7 ? '#4f8cff' : npcData.trust >= 0.3 ? '#ffa500' : '#ff6b6b';

    return (
      <motion.div 
        key={`npc-${npcData.npc_id}-${index}`}
        className="dialogue-widget" 
        style={{ 
          padding: 16, 
          background: '#fff', 
          borderRadius: 12, 
          boxShadow: '0 2px 8px #0001', 
          marginBottom: groupMode && index < (npcs.length - 1) ? 12 : 16 
        }}
        variants={dialogueVariants}
        initial="initial"
        animate="animate"
        exit="exit"
        layout
      >
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
          <img
            src={npcData.avatarUrl || '/default-npc.png'}
            alt={`${npcData.name} avatar`}
            style={{ 
              width: groupMode ? 48 : 64, 
              height: groupMode ? 48 : 64, 
              borderRadius: '50%', 
              marginRight: 12, 
              objectFit: 'cover', 
              background: '#eee',
              border: groupMode ? '2px solid #ddd' : 'none'
            }}
          />
          <div style={{ flex: 1 }}>
            <div style={{ 
              fontWeight: 600, 
              marginBottom: 4, 
              fontSize: groupMode ? 14 : 16,
              color: trustColor
            }}>
              {npcData.name}
            </div>
            <div style={{ height: 6, background: '#eee', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{ 
                width: `${Math.min(Math.max(npcData.trust, 0), 1) * 100}%`, 
                height: '100%', 
                background: trustColor,
                transition: 'width 0.3s ease'
              }} />
            </div>
            <div style={{ fontSize: 10, color: '#888', marginTop: 2 }}>
              Trust: {npcData.trust.toFixed(2)}
            </div>
          </div>
        </div>
        <motion.div 
          style={{ 
            fontStyle: 'italic', 
            color: '#333', 
            minHeight: groupMode ? 24 : 32,
            fontSize: groupMode ? 14 : 16,
            lineHeight: 1.4
          }}
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 + (index * 0.1) }}
        >
          {npcData.text || <span style={{ color: '#aaa' }}>[No dialogue]</span>}
        </motion.div>
        
        {/* Dynamic text only shown for legacy mode or first NPC */}
        {(!groupMode || index === 0) && (
          <AnimatePresence mode="wait">
            {npcTextDynamic && (
              <motion.div 
                key={npcTextDynamic}
                variants={dynamicTextVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                style={{ 
                  fontStyle: 'italic', 
                  color: trustColor, 
                  marginTop: 8, 
                  padding: 8, 
                  background: '#f0f8ff', 
                  borderRadius: 6,
                  borderLeft: `3px solid ${trustColor}`,
                  fontSize: groupMode ? 13 : 14
                }}
                layout
              >
                {npcTextDynamic}
              </motion.div>
            )}
          </AnimatePresence>
        )}
      </motion.div>
    );
  };

  // Determine rendering mode
  if (groupMode && npcs.length > 0) {
    // Multi-NPC group mode
    return (
      <div className="group-dialogue-container">
        <AnimatePresence>
          {npcs.map((npc, index) => renderNPCDialogue(npc, index))}
        </AnimatePresence>
      </div>
    );
  } else if (!groupMode && npcs.length === 1) {
    // Single NPC from array
    return renderNPCDialogue(npcs[0], 0);
  } else {
    // Legacy single NPC mode
    return renderNPCDialogue(null, 0);
  }
};

export default Dialogue; 