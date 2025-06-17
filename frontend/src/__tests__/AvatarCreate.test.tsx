import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import axios from 'axios';
import AvatarCreate from '../scenes/AvatarCreate';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

it('submits avatar form and shows profile', async () => {
  mockedAxios.post.mockResolvedValueOnce({
    data: { playerId: 'alice', soulSeedId: 'abc123def456', initSceneTag: 'intro_001' },
  });

  const user = userEvent.setup();
  render(
    <MemoryRouter>
      <AvatarCreate />
    </MemoryRouter>
  );

  await user.type(screen.getByPlaceholderText('Your Name'), 'Alice');
  await user.selectOptions(screen.getByRole('combobox'), 'Visionary Dreamer');
  await user.click(screen.getByRole('button', { name: /confirm avatar/i }));

  expect(mockedAxios.post).toHaveBeenCalledWith('/soulseed', {
    playerName: 'Alice',
    archetypePreset: 'Visionary Dreamer',
    archetypeCustom: null,
    avatarReferenceUrl: null,
  });

  expect(await screen.findByText(/Avatar Created!/)).toBeInTheDocument();
});
