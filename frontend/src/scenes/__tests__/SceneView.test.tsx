import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, BrowserRouter } from 'react-router-dom';
import SceneView from '../SceneView';

// Mock axios
jest.mock('axios', () => ({
  post: jest.fn(),
  get: jest.fn()
}));

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  clear: jest.fn()
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

// Global Audio mock for all tests
const mockPlay = jest.fn(() => Promise.resolve());
const mockPause = jest.fn();
global.Audio = jest.fn().mockImplementation(() => ({
  play: mockPlay,
  pause: mockPause,
  loop: false,
  src: '',
}));

// Global fetch mock for all endpoints
beforeAll(() => {
  global.fetch = jest.fn((url) => {
    // /npc/{player_id}
    if (typeof url === 'string' && url.includes('/npc/')) {
      return Promise.resolve({ json: () => Promise.resolve([{ trust: 0.5 }]) } as unknown as Response);
    }
    // /trust
    if (typeof url === 'string' && url.includes('/trust')) {
      return Promise.resolve({ json: () => Promise.resolve({ trust: 0.5 }) } as unknown as Response);
    }
    // /emotion/{player_id}
    if (typeof url === 'string' && url.includes('/emotion/')) {
      return Promise.resolve({ json: () => Promise.resolve({ vector: [0,0,0,0,0,0,0,0], log: [] }) } as unknown as Response);
    }
    // /soulmap/{player_id}
    if (typeof url === 'string' && url.includes('/soulmap/')) {
      return Promise.resolve({ json: () => Promise.resolve({ vector: [0,0,0,0,0,0,0,0], log: [] }) } as unknown as Response);
    }
    // Default fallback
    return Promise.resolve({ json: () => Promise.resolve({}) } as unknown as Response);
  });
});

const mockSceneWithMedia = {
  sceneTag: 'test_scene',
  text: 'A brave knight enters a dark forest',
  choices: [
    { tag: '1', label: 'Enter the forest' },
    { tag: '2', label: 'Turn back' }
  ],
  media: {
    images: ['s3://test-bucket/scene_image.jpg'],
    audio: ['s3://test-bucket/scene_ost.mp3']
  }
};

const mockSceneWithoutMedia = {
  sceneTag: 'test_scene',
  text: 'A brave knight enters a dark forest',
  choices: [
    { tag: '1', label: 'Enter the forest' },
    { tag: '2', label: 'Turn back' }
  ],
  media: {
    images: [],
    audio: []
  }
};

const renderSceneView = () => {
  return render(
    <BrowserRouter>
      <SceneView />
    </BrowserRouter>
  );
};

// Helper to set up localStorage for SceneView
function setupLocalStorage() {
  localStorageMock.getItem.mockImplementation((key) => {
    switch (key) {
      case 'soulSeedId':
        return 'test-soul-seed';
      case 'playerId':
        return 'test-player';
      case 'avatarUrl':
        return '/test-avatar.jpg';
      case 'initSceneTag':
        return 'intro_001';
      default:
        return null;
    }
  });
}

describe('SceneView', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupLocalStorage();
  });

  it('shows start scene then next scene on choice', async () => {
    // Mock axios for /start and /choose
    const axios = require('axios');
    axios.post
      .mockResolvedValueOnce({ data: { sceneTag: 'intro_001', text: 'Start here', choices: [{ tag: '1', label: 'Go' }] } })
      .mockResolvedValueOnce({ data: { sceneTag: 'dark_forest', text: 'Dark path', choices: [] } });
    axios.get.mockResolvedValue({ data: { trust: 0 } });

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <SceneView />
      </MemoryRouter>
    );

    // Wait for the question to appear
    const startQuestion = await screen.findByText('Start here');
    expect(startQuestion).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Go' }));
    const nextQuestion = await screen.findByText('Dark path');
    expect(nextQuestion).toBeInTheDocument();
  });

  it('renders start scene with trust styling', async () => {
    // Mock axios for /start
    const axios = require('axios');
    axios.post.mockResolvedValueOnce({ data: { sceneTag: 'intro_001', text: 'Start here', choices: [] } });
    axios.get.mockResolvedValue({ data: { trust: 5 } });

    render(
      <MemoryRouter>
        <SceneView />
      </MemoryRouter>
    );
    // Wait for the question to appear
    const card = await screen.findByText('Start here');
    expect(card).toBeInTheDocument();
  });

  it('applies trust bar width correctly', async () => {
    // Mock axios for /start
    const axios = require('axios');
    axios.post.mockResolvedValueOnce({ data: { sceneTag: 'intro_001', text: 'Start here', choices: [] } });
    axios.get.mockResolvedValue({ data: { trust: -5 } });

    render(
      <MemoryRouter>
        <SceneView />
      </MemoryRouter>
    );
    // Wait for the question to appear
    const card = await screen.findByText('Start here');
    expect(card).toBeInTheDocument();
    expect(screen.getByText('Trust:')).toBeInTheDocument();
  });
});

describe('SceneView Media Handling', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupLocalStorage();
  });

  it('renders scene with media assets', async () => {
    const axios = require('axios');
    axios.post.mockResolvedValue({ data: mockSceneWithMedia });
    axios.get.mockResolvedValue({ data: { trust: 0.5 } });

    renderSceneView();

    await waitFor(() => {
      expect(screen.getByText('A brave knight enters a dark forest')).toBeInTheDocument();
    });

    // Check that image is rendered
    const sceneImage = screen.getByAltText('Scene illustration');
    expect(sceneImage).toBeInTheDocument();
    expect(sceneImage).toHaveAttribute('src', 's3://test-bucket/scene_image.jpg');

    // Check that audio controls are rendered
    const audioButton = screen.getByText('▶️ Play OST');
    expect(audioButton).toBeInTheDocument();
  });

  it('renders scene without media assets', async () => {
    const axios = require('axios');
    axios.post.mockResolvedValue({ data: mockSceneWithoutMedia });
    axios.get.mockResolvedValue({ data: { trust: 0.5 } });

    renderSceneView();

    await waitFor(() => {
      expect(screen.getByText('A brave knight enters a dark forest')).toBeInTheDocument();
    });

    // Check that image is not rendered
    const sceneImage = screen.queryByAltText('Scene illustration');
    expect(sceneImage).not.toBeInTheDocument();

    // Check that audio controls are not rendered
    const audioButton = screen.queryByText('▶️ Play OST');
    expect(audioButton).not.toBeInTheDocument();
  });

  it('handles image loading states', async () => {
    const axios = require('axios');
    axios.post.mockResolvedValue({ data: mockSceneWithMedia });
    axios.get.mockResolvedValue({ data: { trust: 0.5 } });

    renderSceneView();

    await waitFor(() => {
      expect(screen.getByText('Loading scene image...')).toBeInTheDocument();
    });

    // Simulate image load
    const sceneImage = screen.getByAltText('Scene illustration');
    fireEvent.load(sceneImage);

    await waitFor(() => {
      expect(screen.queryByText('Loading scene image...')).not.toBeInTheDocument();
    });
  });

  it('handles image loading errors', async () => {
    const axios = require('axios');
    axios.post.mockResolvedValue({ data: mockSceneWithMedia });
    axios.get.mockResolvedValue({ data: { trust: 0.5 } });

    renderSceneView();

    await waitFor(() => {
      expect(screen.getByText('Loading scene image...')).toBeInTheDocument();
    });

    // Simulate image error
    const sceneImage = screen.getByAltText('Scene illustration');
    fireEvent.error(sceneImage);

    await waitFor(() => {
      expect(screen.queryByText('Loading scene image...')).not.toBeInTheDocument();
    });
  });

  it('handles audio playback controls', async () => {
    const axios = require('axios');
    axios.post.mockResolvedValue({ data: mockSceneWithMedia });
    axios.get.mockResolvedValue({ data: { trust: 0.5 } });

    renderSceneView();

    await waitFor(() => {
      expect(screen.getByText('▶️ Play OST')).toBeInTheDocument();
    });

    // Click play button
    const audioButton = screen.getByText('▶️ Play OST');
    fireEvent.click(audioButton);

    await waitFor(() => {
      expect(mockPlay).toHaveBeenCalled();
    });
  });

  it('handles audio playback errors gracefully', async () => {
    const axios = require('axios');
    axios.post.mockResolvedValue({ data: mockSceneWithMedia });
    axios.get.mockResolvedValue({ data: { trust: 0.5 } });

    renderSceneView();

    await waitFor(() => {
      expect(screen.getByText('▶️ Play OST')).toBeInTheDocument();
    });

    // Click play button
    const audioButton = screen.getByText('▶️ Play OST');
    fireEvent.click(audioButton);

    await waitFor(() => {
      expect(mockPlay).toHaveBeenCalled();
    });
  });
});