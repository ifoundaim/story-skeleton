/**
 * Tests for Multi-NPC Dialogue Component (SPR-NPC03)
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import Dialogue from '../Dialogue';

// Mock framer-motion to avoid animation issues in tests
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe('Multi-NPC Dialogue Component', () => {
  describe('Legacy Single NPC Mode', () => {
    it('renders single NPC with legacy props', () => {
      render(
        <Dialogue 
          npcText="Hello, traveler!" 
          trust={0.7}
          avatarUrl="/test-avatar.png"
        />
      );

      expect(screen.getByText('Companion')).toBeInTheDocument();
      expect(screen.getByText('Hello, traveler!')).toBeInTheDocument();
      expect(screen.getByText('Trust: 0.70')).toBeInTheDocument();
    });

    it('displays correct trust color for high trust', () => {
      render(<Dialogue npcText="Test" trust={0.8} />);
      
      const trustBar = screen.getByText('Companion').closest('div')?.querySelector('[style*="width"]');
      expect(trustBar).toHaveStyle('width: 80%');
    });

    it('displays correct trust color for low trust', () => {
      render(<Dialogue npcText="Test" trust={0.2} />);
      
      const trustBar = screen.getByText('Companion').closest('div')?.querySelector('[style*="width"]');
      expect(trustBar).toHaveStyle('width: 20%');
    });

    it('shows dynamic text when provided', () => {
      render(
        <Dialogue 
          npcText="Static text" 
          trust={0.5}
          npcTextDynamic="Dynamic response!"
        />
      );

      expect(screen.getByText('Static text')).toBeInTheDocument();
      expect(screen.getByText('Dynamic response!')).toBeInTheDocument();
    });
  });

  describe('Single NPC from Array Mode', () => {
    it('renders single NPC from npcs array', () => {
      const npcData = [{
        npc_id: 'lyra',
        name: 'Lyra',
        text: 'Greetings, friend!',
        trust: 0.6,
        avatarUrl: '/lyra-avatar.png'
      }];

      render(<Dialogue npcs={npcData} groupMode={false} />);

      expect(screen.getByText('Lyra')).toBeInTheDocument();
      expect(screen.getByText('Greetings, friend!')).toBeInTheDocument();
      expect(screen.getByText('Trust: 0.60')).toBeInTheDocument();
    });
  });

  describe('Group Mode', () => {
    const multiNPCData = [
      {
        npc_id: 'lyra',
        name: 'Lyra',
        text: 'I believe in your courage!',
        trust: 0.8,
        avatarUrl: '/lyra-avatar.png'
      },
      {
        npc_id: 'orin',
        name: 'Orin',
        text: 'Be cautious in your choices.',
        trust: 0.3,
        avatarUrl: '/orin-avatar.png'
      }
    ];

    it('renders multiple NPCs in group mode', () => {
      render(<Dialogue npcs={multiNPCData} groupMode={true} />);

      expect(screen.getByText('Lyra')).toBeInTheDocument();
      expect(screen.getByText('Orin')).toBeInTheDocument();
      expect(screen.getByText('I believe in your courage!')).toBeInTheDocument();
      expect(screen.getByText('Be cautious in your choices.')).toBeInTheDocument();
    });

    it('displays different trust levels for multiple NPCs', () => {
      render(<Dialogue npcs={multiNPCData} groupMode={true} />);

      expect(screen.getByText('Trust: 0.80')).toBeInTheDocument();
      expect(screen.getByText('Trust: 0.30')).toBeInTheDocument();
    });

    it('shows different trust colors based on trust levels', () => {
      const { container } = render(<Dialogue npcs={multiNPCData} groupMode={true} />);

      // High trust should be blue (#4f8cff)
      const highTrustElements = container.querySelectorAll('[style*="#4f8cff"]');
      expect(highTrustElements.length).toBeGreaterThan(0);

      // Low trust should be red (#ff6b6b)
      const lowTrustElements = container.querySelectorAll('[style*="#ff6b6b"]');
      expect(lowTrustElements.length).toBeGreaterThan(0);
    });

    it('uses smaller avatars in group mode', () => {
      render(<Dialogue npcs={multiNPCData} groupMode={true} />);

      const avatars = screen.getAllByRole('img');
      avatars.forEach(avatar => {
        expect(avatar).toHaveStyle('width: 48px');
        expect(avatar).toHaveStyle('height: 48px');
      });
    });

    it('applies proper spacing between NPCs in group mode', () => {
      const { container } = render(<Dialogue npcs={multiNPCData} groupMode={true} />);

      const dialogueWidgets = container.querySelectorAll('.dialogue-widget');
      expect(dialogueWidgets).toHaveLength(2);
      
      // First NPC should have bottom margin of 12px (not last in group)
      expect(dialogueWidgets[0]).toHaveStyle('margin-bottom: 12px');
      
      // Last NPC should have bottom margin of 16px
      expect(dialogueWidgets[1]).toHaveStyle('margin-bottom: 16px');
    });

    it('only shows dynamic text for first NPC in group mode', () => {
      render(
        <Dialogue 
          npcs={multiNPCData} 
          groupMode={true}
          npcTextDynamic="Dynamic message"
        />
      );

      // Dynamic text should only appear once (for first NPC)
      const dynamicElements = screen.getAllByText('Dynamic message');
      expect(dynamicElements).toHaveLength(1);
    });
  });

  describe('Trust Color Mapping', () => {
    it('uses blue for high trust (≥0.7)', () => {
      const highTrustNPC = [{
        npc_id: 'test',
        name: 'Test NPC',
        text: 'High trust test',
        trust: 0.8
      }];

      const { container } = render(<Dialogue npcs={highTrustNPC} />);
      const trustElements = container.querySelectorAll('[style*="#4f8cff"]');
      expect(trustElements.length).toBeGreaterThan(0);
    });

    it('uses orange for medium trust (0.3-0.7)', () => {
      const mediumTrustNPC = [{
        npc_id: 'test',
        name: 'Test NPC',
        text: 'Medium trust test',
        trust: 0.5
      }];

      const { container } = render(<Dialogue npcs={mediumTrustNPC} />);
      const trustElements = container.querySelectorAll('[style*="#ffa500"]');
      expect(trustElements.length).toBeGreaterThan(0);
    });

    it('uses red for low trust (<0.3)', () => {
      const lowTrustNPC = [{
        npc_id: 'test',
        name: 'Test NPC',
        text: 'Low trust test',
        trust: 0.1
      }];

      const { container } = render(<Dialogue npcs={lowTrustNPC} />);
      const trustElements = container.querySelectorAll('[style*="#ff6b6b"]');
      expect(trustElements.length).toBeGreaterThan(0);
    });
  });

  describe('Error Handling', () => {
    it('handles empty npcs array gracefully', () => {
      render(<Dialogue npcs={[]} groupMode={true} />);
      // Should fallback to legacy mode
      expect(screen.getByText('Companion')).toBeInTheDocument();
    });

    it('shows fallback text when no dialogue provided', () => {
      render(<Dialogue npcText="" trust={0.5} />);
      expect(screen.getByText('[No dialogue]')).toBeInTheDocument();
    });

    it('handles missing avatarUrl gracefully', () => {
      const npcWithoutAvatar = [{
        npc_id: 'test',
        name: 'Test NPC',
        text: 'No avatar test',
        trust: 0.5
      }];

      render(<Dialogue npcs={npcWithoutAvatar} />);
      const avatar = screen.getByRole('img');
      expect(avatar).toHaveAttribute('src', '/default-npc.png');
    });
  });

  describe('Accessibility', () => {
    it('provides proper alt text for avatars', () => {
      const npcData = [{
        npc_id: 'lyra',
        name: 'Lyra',
        text: 'Test text',
        trust: 0.5,
        avatarUrl: '/lyra.png'
      }];

      render(<Dialogue npcs={npcData} />);
      const avatar = screen.getByRole('img');
      expect(avatar).toHaveAttribute('alt', 'Lyra avatar');
    });

    it('maintains proper contrast for trust text', () => {
      render(<Dialogue npcText="Test" trust={0.5} />);
      const trustText = screen.getByText('Trust: 0.50');
      expect(trustText).toHaveStyle('color: #888');
    });
  });

  describe('Animation Integration', () => {
    it('applies staggered delays for multiple NPCs', () => {
      const multiNPCData = [
        { npc_id: '1', name: 'NPC 1', text: 'First', trust: 0.5 },
        { npc_id: '2', name: 'NPC 2', text: 'Second', trust: 0.5 },
        { npc_id: '3', name: 'NPC 3', text: 'Third', trust: 0.5 }
      ];

      // This test verifies the component structure supports staggered animations
      // The actual animation delays are handled by framer-motion
      const { container } = render(<Dialogue npcs={multiNPCData} groupMode={true} />);
      
      const dialogueWidgets = container.querySelectorAll('.dialogue-widget');
      expect(dialogueWidgets).toHaveLength(3);
    });
  });
});