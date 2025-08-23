import React, { useState } from 'react';
import { useSettings } from '../contexts/SettingsContext';

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const SettingsPanel: React.FC<SettingsPanelProps> = ({ isOpen, onClose }) => {
  const { settings, updateSettings, resetSettings } = useSettings();
  const [isResetting, setIsResetting] = useState(false);

  const handleReset = () => {
    setIsResetting(true);
    resetSettings();
    setTimeout(() => setIsResetting(false), 1000);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900">Settings</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              aria-label="Close settings"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-6">
            {/* Consequence Toasts Section */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Consequence Feedback</h3>
              
              <div className="space-y-4">
                {/* Enable/Disable Toasts */}
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Show consequence toasts
                    </label>
                    <p className="text-xs text-gray-500 mt-1">
                      Display real-time feedback when choices have consequences
                    </p>
                  </div>
                  <button
                    onClick={() => updateSettings({ toastsEnabled: !settings.toastsEnabled })}
                    className={`
                      relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                      ${settings.toastsEnabled ? 'bg-blue-600' : 'bg-gray-200'}
                    `}
                    role="switch"
                    aria-checked={settings.toastsEnabled}
                    aria-label="Toggle consequence toasts"
                  >
                    <span
                      className={`
                        inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                        ${settings.toastsEnabled ? 'translate-x-6' : 'translate-x-1'}
                      `}
                    />
                  </button>
                </div>

                {/* Toast Severity Filter */}
                {settings.toastsEnabled && (
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      Minimum severity
                    </label>
                    <select
                      value={settings.toastsMinSeverity}
                      onChange={(e) => updateSettings({ toastsMinSeverity: e.target.value as 'info' | 'important' })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="info">All consequences</option>
                      <option value="important">Important only (promises)</option>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      {settings.toastsMinSeverity === 'info' 
                        ? 'Show all consequence types' 
                        : 'Only show promise fulfillment/breach notifications'
                      }
                    </p>
                  </div>
                )}

                {/* Reduced Motion */}
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Reduced motion
                    </label>
                    <p className="text-xs text-gray-500 mt-1">
                      Minimize animations for accessibility
                    </p>
                  </div>
                  <button
                    onClick={() => updateSettings({ reducedMotion: !settings.reducedMotion })}
                    className={`
                      relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                      ${settings.reducedMotion ? 'bg-blue-600' : 'bg-gray-200'}
                    `}
                    role="switch"
                    aria-checked={settings.reducedMotion}
                    aria-label="Toggle reduced motion"
                  >
                    <span
                      className={`
                        inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                        ${settings.reducedMotion ? 'translate-x-6' : 'translate-x-1'}
                      `}
                    />
                  </button>
                </div>
              </div>
            </div>

            {/* Reset Button */}
            <div className="pt-4 border-t border-gray-200">
              <button
                onClick={handleReset}
                disabled={isResetting}
                className="w-full px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isResetting ? 'Resetting...' : 'Reset to defaults'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;
