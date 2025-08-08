import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SceneView from '../scenes/SceneView';


it('renders start scene with trust styling', async () => {
  const startScene = { sceneTag: 'intro_001', text: 'Start here', choices: [{ tag: '1', label: 'Go' }] };
  (global as any).fetch = jest
    .fn()
    .mockResolvedValueOnce({ json: () => Promise.resolve(startScene) } as any)
    .mockResolvedValueOnce({ json: () => Promise.resolve({ trust: 5 }) } as any);

  render(
    <MemoryRouter>
      <SceneView />
    </MemoryRouter>
  );

  const text = await screen.findByText('Start here');
  expect(text).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Go' })).toBeInTheDocument();
});
