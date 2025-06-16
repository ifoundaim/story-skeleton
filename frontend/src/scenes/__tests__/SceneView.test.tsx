import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SceneView from '../SceneView';

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
    render(<SceneView />);

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

    render(<SceneView />);

    const card = await screen.findByText('Start here');
    expect(card).toHaveClass('bg-forest');
  });
});
