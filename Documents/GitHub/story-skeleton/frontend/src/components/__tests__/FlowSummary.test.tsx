import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import FlowSummary from '../FlowSummary';

// Mock fetch
global.fetch = jest.fn();

const mockFlowSummaryData = {
  scene_range: [0, 9],
  choices: [
    {
      scene_index: 5,
      text: "Promised to help",
      tags: ["bond"],
      effects: { promise_added: "help_friend" }
    }
  ],
  consequences: [
    {
      type: "promise",
      key: "help_friend",
      value: "Help your friend escape",
      npc_id: "companion"
    }
  ],
  fogged_branches: 3,
  percent_stats: { choice_popularity: 0.75 }
};

describe('FlowSummary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    (fetch as jest.Mock).mockImplementation(() => new Promise(() => {}));
    
    render(<FlowSummary playerId="test-player" />);
    
    expect(screen.getByText('Loading flow summary...')).toBeInTheDocument();
  });

  it('renders flow summary data when loaded', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockFlowSummaryData
    });

    render(<FlowSummary playerId="test-player" chapter={1} />);

    await waitFor(() => {
      expect(screen.getByText('Chapter 1 Flow Summary')).toBeInTheDocument();
    });

    expect(screen.getByText('Scenes 1 - 10')).toBeInTheDocument();
    expect(screen.getByText('Your Choices')).toBeInTheDocument();
    expect(screen.getByText('Consequences')).toBeInTheDocument();
    expect(screen.getByText('Alternative Paths')).toBeInTheDocument();
    expect(screen.getByText('Statistics')).toBeInTheDocument();
  });

  it('renders choice data correctly', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockFlowSummaryData
    });

    render(<FlowSummary playerId="test-player" />);

    await waitFor(() => {
      expect(screen.getByText('Scene 6')).toBeInTheDocument();
      expect(screen.getByText('Promised to help')).toBeInTheDocument();
      expect(screen.getByText('bond')).toBeInTheDocument();
    });
  });

  it('renders consequence data correctly', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockFlowSummaryData
    });

    render(<FlowSummary playerId="test-player" />);

    await waitFor(() => {
      expect(screen.getByText('promise')).toBeInTheDocument();
      expect(screen.getByText('help_friend')).toBeInTheDocument();
      expect(screen.getByText('Help your friend escape')).toBeInTheDocument();
      expect(screen.getByText('NPC: companion')).toBeInTheDocument();
    });
  });

  it('renders fogged branches correctly', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockFlowSummaryData
    });

    render(<FlowSummary playerId="test-player" />);

    await waitFor(() => {
      expect(screen.getByText('3 alternative story paths remain unexplored')).toBeInTheDocument();
    });
  });

  it('renders statistics correctly', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockFlowSummaryData
    });

    render(<FlowSummary playerId="test-player" />);

    await waitFor(() => {
      expect(screen.getByText('choice popularity')).toBeInTheDocument();
      expect(screen.getByText('75%')).toBeInTheDocument();
    });
  });

  it('handles fetch error', async () => {
    (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

    render(<FlowSummary playerId="test-player" />);

    await waitFor(() => {
      expect(screen.getByText('Error: Network error')).toBeInTheDocument();
    });
  });

  it('handles non-ok response', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      statusText: 'Not Found'
    });

    render(<FlowSummary playerId="test-player" />);

    await waitFor(() => {
      expect(screen.getByText('Error: Failed to fetch flow summary: Not Found')).toBeInTheDocument();
    });
  });

  it('calls fetch with correct parameters', async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockFlowSummaryData
    });

    render(<FlowSummary playerId="test-player" chapter={2} />);

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/flow/summary?player_id=test-player&chapter=2');
    });
  });
});
