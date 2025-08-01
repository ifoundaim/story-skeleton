import { render, screen } from '@testing-library/react';
import Dialogue from '../Dialogue';

// Mock framer-motion for testing
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, variants, layout, ...props }: any) => (
      <div data-testid="motion-div" data-variants={JSON.stringify(variants)} {...props}>
        {children}
      </div>
    ),
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe('Dialogue Animations', () => {
  const defaultProps = {
    avatarUrl: '/test-npc.png',
    npcText: 'Hello there!',
    trust: 0.75,
    npcTextDynamic: undefined
  };

  test('renders dialogue with animation structure', () => {
    render(<Dialogue {...defaultProps} />);

    // Check that motion divs are created
    const motionDivs = screen.getAllByTestId('motion-div');
    expect(motionDivs.length).toBeGreaterThan(0);

    // Check that NPC text is displayed
    expect(screen.getByText('Hello there!')).toBeInTheDocument();

    // Check that trust value is displayed
    expect(screen.getByText('Trust: 0.75')).toBeInTheDocument();
  });

  test('renders dynamic text with proper animation structure', () => {
    const propsWithDynamic = {
      ...defaultProps,
      npcTextDynamic: 'This is dynamic text!'
    };

    render(<Dialogue {...propsWithDynamic} />);

    // Check that dynamic text is displayed
    expect(screen.getByText('This is dynamic text!')).toBeInTheDocument();

    // Check that it has the proper styling for dynamic text
    const dynamicTextElement = screen.getByText('This is dynamic text!');
    expect(dynamicTextElement.closest('div')).toHaveStyle({
      fontStyle: 'italic',
      color: '#4f8cff',
      background: '#f0f8ff',
      borderLeft: '3px solid #4f8cff'
    });
  });

  test('handles empty npc text gracefully', () => {
    const propsWithEmptyText = {
      ...defaultProps,
      npcText: ''
    };

    render(<Dialogue {...propsWithEmptyText} />);

    // Should show fallback text
    expect(screen.getByText('[No dialogue]')).toBeInTheDocument();
  });

  test('avatar image has correct attributes', () => {
    render(<Dialogue {...defaultProps} />);

    const avatar = screen.getByAltText('NPC avatar');
    expect(avatar).toHaveAttribute('src', '/test-npc.png');
    expect(avatar).toHaveStyle({
      width: '64px',
      height: '64px',
      borderRadius: '50%'
    });
  });

  test('trust bar displays correct width', () => {
    render(<Dialogue {...defaultProps} />);

    // Find the trust bar (the colored div inside the progress container)
    const trustBars = document.querySelectorAll('div[style*="background: rgb(79, 140, 255)"]');
    expect(trustBars.length).toBeGreaterThan(0);
    
    const trustBar = trustBars[0] as HTMLElement;
    expect(trustBar).toHaveStyle({
      width: '75%', // 0.75 * 100%
      height: '100%'
    });
  });

  test('handles trust values outside 0-1 range', () => {
    const propsWithHighTrust = {
      ...defaultProps,
      trust: 1.5 // Above 1
    };

    render(<Dialogue {...propsWithHighTrust} />);

    // Trust should be clamped to 100%
    const trustBars = document.querySelectorAll('div[style*="background: rgb(79, 140, 255)"]');
    expect(trustBars.length).toBeGreaterThan(0);
    
    const trustBar = trustBars[0] as HTMLElement;
    expect(trustBar).toHaveStyle({
      width: '100%'
    });
  });

  test('uses default avatar when none provided', () => {
    const propsWithoutAvatar = {
      npcText: 'Hello',
      trust: 0.5
    };

    render(<Dialogue {...propsWithoutAvatar} />);

    const avatar = screen.getByAltText('NPC avatar');
    expect(avatar).toHaveAttribute('src', '/default-npc.png');
  });
});