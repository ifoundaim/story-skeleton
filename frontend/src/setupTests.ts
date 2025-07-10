import '@testing-library/jest-dom';

// Mock ResizeObserver for Recharts and other components
if (typeof window !== 'undefined' && !window.ResizeObserver) {
  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

// Mock HTMLMediaElement.prototype.pause/play for audio tests
Object.defineProperty(window.HTMLMediaElement.prototype, 'pause', {
  configurable: true,
  value: jest.fn(),
});
Object.defineProperty(window.HTMLMediaElement.prototype, 'play', {
  configurable: true,
  value: jest.fn(() => Promise.resolve()),
});
