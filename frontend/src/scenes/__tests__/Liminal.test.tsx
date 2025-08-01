import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Liminal from '../Liminal';

it('collects inputs through the ritual phases', async () => {
  const user = userEvent.setup();
  render(
    <MemoryRouter>
      <Liminal />
    </MemoryRouter>
  );
  const phase = () => screen.getByText(/ASK|SEEK|KNOCK/);
  const input = () => screen.getByRole('textbox');
  const button = () => screen.getByRole('button');

  expect(phase()).toHaveTextContent('ASK');
  await user.type(input(), 'a');
  await user.click(button());

  expect(phase()).toHaveTextContent('SEEK');
  await user.type(input(), 'b');
  await user.click(button());

  expect(phase()).toHaveTextContent('KNOCK');
});
