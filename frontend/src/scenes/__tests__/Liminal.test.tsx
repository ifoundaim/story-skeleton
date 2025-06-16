import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Liminal from '../Liminal';

it('cycles ASK -> SEEK -> KNOCK', async () => {
  const user = userEvent.setup();
  render(
    <MemoryRouter>
      <Liminal />
    </MemoryRouter>
  );
  const word = () => screen.getByText(/ASK|SEEK|KNOCK/);
  expect(word()).toHaveTextContent('ASK');
  await user.click(word());
  expect(word()).toHaveTextContent('SEEK');
  await user.click(word());
  expect(word()).toHaveTextContent('KNOCK');
});
