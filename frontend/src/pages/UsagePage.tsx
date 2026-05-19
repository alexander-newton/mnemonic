/**
 * UsagePage - shows LLM token/cost usage statistics.
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

/**
 * Displays daily and monthly LLM cost figures plus today's cache hit rate.
 * Fails loudly if the backend request fails — no silent empty states.
 */
export default function UsagePage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['usage'],
    queryFn: api.usage,
  });

  if (isLoading) return <div>Loading usage…</div>;
  if (error) return <div role="alert">Failed to load usage: {String(error)}</div>;

  return (
    <section>
      <h1>LLM Usage</h1>
      <dl>
        <dt>Today</dt>
        <dd>${data.daily_cents.toFixed(3)}</dd>
        <dt>Last 30 days</dt>
        <dd>${data.monthly_cents.toFixed(2)}</dd>
        <dt>Cache hit rate (today)</dt>
        <dd>{(data.cache_hit_rate * 100).toFixed(1)}%</dd>
      </dl>
    </section>
  );
}
