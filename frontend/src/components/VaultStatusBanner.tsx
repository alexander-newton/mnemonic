/**
 * VaultStatusBanner - shows git vault health at the top of every page.
 * Polls every 30 s so stale-commit warnings appear without a page refresh.
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

/**
 * Displays a dismissible banner with vault git status.
 * Shows a warning style when the vault has uncommitted changes or unpushed commits.
 */
export default function VaultStatusBanner() {
  const { data, isError } = useQuery({
    queryKey: ['vault-status'],
    queryFn: api.vaultStatus,
    refetchInterval: 30_000,
  });

  if (isError) return <div role="alert">Vault status unavailable.</div>;
  if (!data) return null;

  const warn = data.dirty || data.has_unpushed_commits;
  return (
    <div className={`vault-status ${warn ? 'vault-status--warn' : ''}`}>
      <span>Vault @ {data.head}</span>
      {data.dirty && <span> · uncommitted changes</span>}
      {data.has_unpushed_commits && <span> · unpushed commits</span>}
    </div>
  );
}
