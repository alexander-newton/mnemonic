/**
 * Navigation component - Header navigation bar.
 * Single-user vault model: always shows Decks link, no auth UI.
 */

import { NavLink } from 'react-router-dom';

/**
 * Navigation displays the header with the app logo and primary links.
 *
 * @example
 * ```tsx
 * <Navigation />
 * ```
 */
export const Navigation: React.FC = () => {
  return (
    <nav className="app-nav">
      <NavLink to="/decks">Decks</NavLink>
      <NavLink to="/usage">Usage</NavLink>
      <NavLink to="/settings">Settings</NavLink>
    </nav>
  );
};
