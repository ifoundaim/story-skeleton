import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSettings } from '../contexts/SettingsContext';

export interface ConsequenceToast {
  id: string;
  kind: 'promise_set' | 'promise_fulfilled' | 'promise_breached' | 'reputation_shift' | 'flag_set' | 'flag_cleared' | 'resource_change';
  label: string;
  delta?: number;
  npc_id?: string;
  timestamp: number;
}

interface ConsequenceToasterProps {
  toasts: ConsequenceToast[];
  onToastDismiss: (id: string) => void;
}

const ConsequenceToaster: React.FC<ConsequenceToasterProps> = ({ toasts, onToastDismiss }) => {
  const { settings } = useSettings();
  const prefersReducedMotion = settings.reducedMotion || window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const getToastIcon = (kind: ConsequenceToast['kind']) => {
    switch (kind) {
      case 'promise_set':
        return '🤝';
      case 'promise_fulfilled':
        return '✅';
      case 'promise_breached':
        return '❌';
      case 'reputation_shift':
        return '⭐';
      case 'flag_set':
        return '🚩';
      case 'flag_cleared':
        return '🧹';
      case 'resource_change':
        return '💎';
      default:
        return '📝';
    }
  };

  const getToastColor = (kind: ConsequenceToast['kind'], delta?: number) => {
    switch (kind) {
      case 'promise_fulfilled':
        return 'bg-green-500';
      case 'promise_breached':
        return 'bg-red-500';
      case 'reputation_shift':
        return delta && delta > 0 ? 'bg-blue-500' : 'bg-orange-500';
      case 'flag_set':
        return 'bg-purple-500';
      case 'flag_cleared':
        return 'bg-gray-500';
      case 'resource_change':
        return delta && delta > 0 ? 'bg-emerald-500' : 'bg-amber-500';
      default:
        return 'bg-indigo-500';
    }
  };

  return (
    <div 
      className="fixed top-4 right-4 z-50 space-y-2 pointer-events-none"
      aria-live="polite"
      aria-label="Consequence notifications"
    >
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ 
              opacity: 0, 
              x: 300,
              scale: 0.8 
            }}
            animate={{ 
              opacity: 1, 
              x: 0,
              scale: 1 
            }}
            exit={{ 
              opacity: 0, 
              x: 300,
              scale: 0.8 
            }}
            transition={{ 
              duration: prefersReducedMotion ? 0.1 : 0.3,
              ease: "easeOut"
            }}
            className={`
              pointer-events-auto
              max-w-sm
              p-3
              rounded-lg
              shadow-lg
              text-white
              ${getToastColor(toast.kind, toast.delta)}
              border-l-4
              border-white/20
            `}
            role="alert"
            aria-label={`${toast.kind.replace('_', ' ')}: ${toast.label}`}
          >
            <div className="flex items-start space-x-2">
              <span className="text-lg flex-shrink-0" aria-hidden="true">
                {getToastIcon(toast.kind)}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium leading-tight">
                  {toast.label}
                </p>
                {toast.delta !== undefined && (
                  <p className="text-xs opacity-90 mt-1">
                    {toast.delta > 0 ? '+' : ''}{toast.delta.toFixed(2)}
                  </p>
                )}
              </div>
              <button
                onClick={() => onToastDismiss(toast.id)}
                className="flex-shrink-0 text-white/70 hover:text-white transition-colors"
                aria-label="Dismiss notification"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};

export default ConsequenceToaster;
