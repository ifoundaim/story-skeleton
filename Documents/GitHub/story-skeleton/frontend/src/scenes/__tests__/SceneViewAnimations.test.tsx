import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import SceneView from '../SceneView';

// Mock axios
jest.mock('axios', () => ({
  post: jest.fn(),
  get: jest.fn(),
}));

// Mock framer-motion for testing
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    img: ({ children, ...props }: any) => <img {...props}>{children}</img>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

// Mock components
jest.mock('../SoulMapWidget', () => {
  return function MockSoulMapWidget() {
    return <div data-testid="soul-map-widget">SoulMap Widget</div>;
  };
});

jest.mock('../Dialogue', () => {
  return function MockDialogue() {
    return <div data-testid="dialogue">Dialogue Component</div>;
  };
});

jest.mock('../EmotionGraph', () => {
  return function MockEmotionGraph() {
    return <div data-testid="emotion-graph">Emotion Graph</div>;
  };
});

const mockAxios = require('axios');

describe('SceneView Animations', () => {
  beforeEach(() => {
    // Set up localStorage
    Storage.prototype.getItem = jest.fn((key) => {
      const values: Record<string, string> = {
        soulSeedId: 'test-seed-id',
        playerId: 'test-player-id',
        avatarUrl: '/test-avatar.png',
        initSceneTag: 'test-scene'
      };
      return values[key] || null;
    });

    // Mock successful API responses
    mockAxios.post.mockResolvedValue({
      data: {
        sceneTag: 'test-scene',
        text: 'Test scene text',
        choices: [
          { tag: 'choice1', label: 'Choice 1' },
          { tag: 'choice2', label: 'Choice 2' }
        ],
        trust: 0.5,
        media: { images: ['/test-image.jpg'], audio: [] }
      }
    });

    mockAxios.get.mockResolvedValue({
      data: { trust: 0.6 }
    });

    global.fetch = jest.fn().mockResolvedValue({
      json: () => Promise.resolve([{ trust: 0.5 }])
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  const renderSceneView = () => {
    return render(
      <BrowserRouter>
        <SceneView />
      </BrowserRouter>
    );
  };

  test('renders scene content with proper structure for animations', async () => {
    renderSceneView();

    await waitFor(() => {
      expect(screen.getByText('Test scene text')).toBeInTheDocument();
    });

    // Check that choice buttons are rendered
    expect(screen.getByText('Choice 1')).toBeInTheDocument();
    expect(screen.getByText('Choice 2')).toBeInTheDocument();

    // Check that sidebar components are rendered
    expect(screen.getByTestId('soul-map-widget')).toBeInTheDocument();
    expect(screen.getByTestId('dialogue')).toBeInTheDocument();
    expect(screen.getByTestId('emotion-graph')).toBeInTheDocument();
  });

  test('choice buttons are disabled during transitions', async () => {
    renderSceneView();

    await waitFor(() => {
      expect(screen.getByText('Choice 1')).toBeInTheDocument();
    });

    const choiceButton = screen.getByText('Choice 1');
    
    // Click the choice button
    fireEvent.click(choiceButton);

    // Button should become disabled during transition
    await waitFor(() => {
      expect(choiceButton).toBeDisabled();
    });
  });

  test('scene image has proper loading states', async () => {
    renderSceneView();

    await waitFor(() => {
      expect(screen.getByAltText('Scene illustration')).toBeInTheDocument();
    });

    const image = screen.getByAltText('Scene illustration');
    expect(image).toHaveAttribute('src', '/test-image.jpg');
  });

  test('responsive classes are applied correctly', async () => {
    renderSceneView();

    await waitFor(() => {
      const container = document.querySelector('.scene-view-container');
      expect(container).toHaveClass('min-h-screen', 'bg-gradient-to-br', 'flex', 'flex-col', 'lg:flex-row');
    });

    const mainContent = document.querySelector('.scene-main');
    expect(mainContent).toHaveClass('flex-1', 'min-h-0');

    const sidebar = document.querySelector('.scene-sidebar');
    expect(sidebar).toHaveClass('w-full', 'lg:w-80', 'lg:max-w-sm');
  });

  test('avatar has responsive sizing classes', async () => {
    renderSceneView();

    await waitFor(() => {
      const avatar = screen.getByAltText('Your avatar');
      expect(avatar).toHaveClass('w-24', 'h-24', 'md:w-32', 'md:h-32');
    });
  });

  test('background gradient is applied', async () => {
    renderSceneView();

    await waitFor(() => {
      const container = document.querySelector('.scene-view-container');
      expect(container).toHaveClass('bg-gradient-to-br', 'from-slate-50', 'via-blue-50', 'to-indigo-100');
    });
  });
});