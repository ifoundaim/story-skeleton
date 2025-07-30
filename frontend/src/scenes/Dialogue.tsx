import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface DialogueProps {
  avatarUrl?: string;
  npcText: string;
  trust: number;
  npcTextDynamic?: string;
}

const Dialogue: React.FC<DialogueProps> = ({ avatarUrl = '/default-npc.png', npcText, trust, npcTextDynamic }: DialogueProps) => {
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

  return (
    <motion.div 
      className="dialogue-widget" 
      style={{ padding: 16, background: '#fff', borderRadius: 12, boxShadow: '0 2px 8px #0001', marginBottom: 16 }}
      variants={dialogueVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      layout
    >
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
      <motion.div 
        style={{ fontStyle: 'italic', color: '#333', minHeight: 32 }}
        initial={{ opacity: 0, y: 5 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        {npcText || <span style={{ color: '#aaa' }}>[No dialogue]</span>}
      </motion.div>
      
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
              color: '#4f8cff', 
              marginTop: 8, 
              padding: 8, 
              background: '#f0f8ff', 
              borderRadius: 6,
              borderLeft: '3px solid #4f8cff'
            }}
            layout
          >
            {npcTextDynamic}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default Dialogue; 