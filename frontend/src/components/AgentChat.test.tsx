import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AgentChat from './AgentChat';

describe('AgentChat', () => {
  it('renders the ADK mode in the toolbar', () => {
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <AgentChat token="token" sessionId="session" documentIds={[1]} />
      </QueryClientProvider>
    );

    expect(screen.getByRole('button', { name: /ADK/i })).toBeInTheDocument();
  });
});
