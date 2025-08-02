import { motion } from "framer-motion";

interface DeltaBadgeProps {
  trait: string;
  value: number;
}

export function DeltaBadge({ trait, value }: DeltaBadgeProps) {
  const isPositive = value > 0;
  const formattedValue = isPositive ? `+${value.toFixed(2)}` : value.toFixed(2);
  const displayText = `${formattedValue} ${trait}`;
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 0, scale: 0.8 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -20, scale: 0.8 }}
      whileHover={{ scale: 1.05, y: -2 }}
      transition={{ 
        duration: 0.8,
        ease: [0.25, 0.46, 0.45, 0.94]
      }}
      className={`px-3 py-2 m-1 rounded-xl text-white text-sm font-medium shadow-lg cursor-default ${
        isPositive 
          ? 'bg-emerald-600/90 border border-emerald-500/50' 
          : 'bg-rose-600/90 border border-rose-500/50'
      }`}
      style={{ 
        willChange: 'transform, opacity',
        zIndex: 1000
      }}
    >
      {displayText}
    </motion.div>
  );
} 