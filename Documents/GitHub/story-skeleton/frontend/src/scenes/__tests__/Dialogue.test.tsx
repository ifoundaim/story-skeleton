import { render, screen } from '@testing-library/react';
import Dialogue from '../Dialogue';

describe('Dialogue', () => {
  it('renders avatar, npcText, and trust bar', () => {
    render(<Dialogue avatarUrl="/test-avatar.png" npcText="Hello, hero!" trust={0.7} />);
    expect(screen.getByAltText('NPC avatar')).toBeInTheDocument();
    expect(screen.getByText('Hello, hero!')).toBeInTheDocument();
    expect(screen.getByText(/Trust:/)).toHaveTextContent('Trust: 0.70');
  });
}); 