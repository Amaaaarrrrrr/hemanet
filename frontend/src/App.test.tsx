import { render, screen } from '@testing-library/react';

import { App } from './App.tsx';

describe('App (E0 placeholder)', () => {
  it('renders the product name', () => {
    render(<App />);
    expect(screen.getByRole('heading', { level: 1, name: 'HemaNet' })).toBeInTheDocument();
  });

  it('shows the prototype disclaimer', () => {
    render(<App />);
    expect(screen.getByRole('note')).toHaveTextContent(/not clinically validated/i);
  });
});
