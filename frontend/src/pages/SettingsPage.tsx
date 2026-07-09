/**
 * SettingsPage - read-only view of the active config.toml values.
 * Users must edit the file directly; this page just surfaces what is live.
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { useFontPreference, FONT_OPTIONS } from '../hooks/useFontPreference';

/**
 * Displays current vault and LLM configuration in a read-only format.
 * Directs users to edit `~/.config/mnemonic/config.toml` for changes.
 */
export default function SettingsPage() {
  const { font, setFont } = useFontPreference();
  const { data, isLoading } = useQuery({
    queryKey: ['config'],
    queryFn: api.getConfig,
  });

  if (isLoading || !data) return <div>Loading…</div>;

  return (
    <section>
      <h1>Settings</h1>
      <h2>Vault</h2>
      <dl>
        <dt>Path</dt>
        <dd>{data.vault.path}</dd>
        <dt>Branch</dt>
        <dd>{data.vault.branch}</dd>
        <dt>Watch</dt>
        <dd>{String(data.vault.watch)}</dd>
      </dl>
      <h2>LLM</h2>
      <dl>
        <dt>Default model</dt>
        <dd>{data.llm.model_default}</dd>
        <dt>Rephrase model</dt>
        <dd>{data.llm.model_rephrase}</dd>
        <dt>Daily cap (cents)</dt>
        <dd>{data.llm.budget.daily_cents}</dd>
        <dt>Monthly cap (cents)</dt>
        <dd>{data.llm.budget.monthly_cents}</dd>
      </dl>
      <p>
        To edit, modify <code>~/.config/mnemonic/config.toml</code> and restart the backend.
      </p>
      <h2>Appearance</h2>
      <label htmlFor="font-select">Font</label>
      <select id="font-select" value={font} onChange={(e) => setFont(e.target.value)}>
        {FONT_OPTIONS.map((opt) => (
          <option key={opt.label} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </section>
  );
}
