import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import EightDCasesPage from './EightDCasesPage';

describe('EightDCasesPage', () => {
  it('renders the 8D workspace heading', () => {
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <EightDCasesPage token="token" />
      </QueryClientProvider>
    );

    expect(screen.getByRole('heading', { name: /8D Cases/i })).toBeInTheDocument();
  });
});
