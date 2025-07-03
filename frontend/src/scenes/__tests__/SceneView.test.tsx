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

// Mock fetch
global.fetch = jest.fn();

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

describe('SceneView', () => {
  it('shows start scene then next scene on choice', async () => {
    const startScene = { sceneTag: 'intro_001', text: 'Start here', choices: [{ tag: '1', label: 'Go' }] };
    const nextScene = { sceneTag: 'dark_forest', text: 'Dark path', choices: [] };
    const fetchMock = jest
      .fn()
      .mockResolvedValueOnce({ json: () => Promise.resolve(startScene) } as any)
      .mockResolvedValueOnce({ json: () => Promise.resolve({ trust: 0 }) } as any)
      .mockResolvedValueOnce({ json: () => Promise.resolve(nextScene) } as any)
      .mockResolvedValueOnce({ json: () => Promise.resolve({ trust: 0 }) } as any);
    (global as any).fetch = fetchMock;

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <SceneView />
      </MemoryRouter>
    );

    expect(await screen.findByText('Start here')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Go' }));
    expect(await screen.findByText('Dark path')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it('applies forest theme when trust negative', async () => {
    const startScene = { sceneTag: 'intro_001', text: 'Start here', choices: [] };
    const fetchMock = jest
      .fn()
      .mockResolvedValueOnce({ json: () => Promise.resolve(startScene) } as any)
      .mockResolvedValueOnce({ json: () => Promise.resolve({ trust: -5 }) } as any);
    (global as any).fetch = fetchMock;

    render(
      <MemoryRouter>
        <SceneView />
      </MemoryRouter>
    );

    const card = await screen.findByText('Start here');
    expect(card).toHaveClass('bg-forest');
  });

  it('renders start scene with trust styling', async () => {
    render(
      <MemoryRouter>
        <SceneView />
      </MemoryRouter>
    );
    // ... existing test code ...
  });
});

describe('SceneView Media Handling', () => {
  beforeEach(() => {
    jest.clearAllMocks();
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
  });

  it('renders scene with media assets', async () => {
    const axios = require('axios');
    axios.post.mockResolvedValue({ data: mockSceneWithMedia });
    axios.get.mockResolvedValue({ data: { trust: 0.5 } });
    ;(global.fetch as jest.Mock).mockResolvedValue({
      json: () => Promise.resolve([{ trust: 0.5 }])
    });

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
    ;(global.fetch as jest.Mock).mockResolvedValue({
      json: () => Promise.resolve([{ trust: 0.5 }])
    });

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
    ;(global.fetch as jest.Mock).mockResolvedValue({
      json: () => Promise.resolve([{ trust: 0.5 }])
    });

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
    ;(global.fetch as jest.Mock).mockResolvedValue({
      json: () => Promise.resolve([{ trust: 0.5 }])
    });

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
    ;(global.fetch as jest.Mock).mockResolvedValue({
      json: () => Promise.resolve([{ trust: 0.5 }])
    });

    // Mock Audio constructor
    const mockPlay = jest.fn().mockResolvedValue(undefined);
    const mockPause = jest.fn();
    global.Audio = jest.fn().mockImplementation(() => ({
      play: mockPlay,
      pause: mockPause,
      loop: false
    }));

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

    // Check button text changed to pause
    await waitFor(() => {
      expect(screen.getByText('⏸️ Pause OST')).toBeInTheDocument();
    });

    // Click pause button
    fireEvent.click(screen.getByText('⏸️ Pause OST'));

    await waitFor(() => {
      expect(mockPause).toHaveBeenCalled();
    });
  });

  it('handles audio playback errors gracefully', async () => {
    const axios = require('axios');
    axios.post.mockResolvedValue({ data: mockSceneWithMedia });
    axios.get.mockResolvedValue({ data: { trust: 0.5 } });
    ;(global.fetch as jest.Mock).mockResolvedValue({
      json: () => Promise.resolve([{ trust: 0.5 }])
    });

    // Mock Audio constructor with play error
    const mockPlay = jest.fn().mockRejectedValue(new Error('Audio error'));
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    
    global.Audio = jest.fn().mockImplementation(() => ({
      play: mockPlay,
      pause: jest.fn(),
      loop: false
    }));

    renderSceneView();

    await waitFor(() => {
      expect(screen.getByText('▶️ Play OST')).toBeInTheDocument();
    });

    // Click play button
    const audioButton = screen.getByText('▶️ Play OST');
    fireEvent.click(audioButton);

    await waitFor(() => {
      expect(mockPlay).toHaveBeenCalled();
      expect(consoleSpy).toHaveBeenCalledWith('Failed to play audio:', expect.any(Error));
    });

    consoleSpy.mockRestore();
  });
});