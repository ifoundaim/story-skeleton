// import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { EmotionGraph } from '../EmotionGraph';

const EMOTION_DIMENSIONS = [
  'joy', 'grief', 'awe', 'fear', 'desire', 'disgust', 'peace', 'rage'
];

describe('EmotionGraph', () => {
  beforeEach(() => {
    // @ts-ignore
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          vector: [0.5, -0.2, 0.1, 0, 0.3, -0.1, 0.2, 0],
          log: [
            { sceneTag: 'sceneA', delta: [0.5, -0.2, 0.1, 0, 0.3, -0.1, 0.2, 0] }
          ]
        })
      })
    );
  });

  afterEach(() => {
    // @ts-ignore
    global.fetch.mockClear();
  });

  it('renders radar chart with correct axes and values', async () => {
    render(<EmotionGraph playerId="testplayer" />);
    // Wait for loading to finish
    await waitFor(() => expect(screen.queryByText(/Loading emotion/i)).not.toBeInTheDocument());
    // Check axis labels
    EMOTION_DIMENSIONS.forEach(dim => {
      expect(screen.getByText(new RegExp(dim, 'i'))).toBeInTheDocument();
    });
    // Check chart title
    expect(screen.getByText(/Emotional State/i)).toBeInTheDocument();
  });

  it('shows error if fetch fails', async () => {
    // @ts-ignore
    global.fetch = jest.fn(() => Promise.resolve({ ok: false }));
    render(<EmotionGraph playerId="failcase" />);
    await waitFor(() => expect(screen.getByText(/Error/i)).toBeInTheDocument());
  });

  it('renders with different playerId prop', async () => {
    render(<EmotionGraph playerId="anotherplayer" />);
    await waitFor(() => expect(screen.queryByText(/Loading emotion/i)).not.toBeInTheDocument());
    expect(screen.getByText(/Emotional State/i)).toBeInTheDocument();
  });
}); 