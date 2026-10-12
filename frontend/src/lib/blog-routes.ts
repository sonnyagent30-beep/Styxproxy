/**
 * Route colour resolution for the blog.
 *
 * The DATABASE is the source of truth for a route's dark-mode colour
 * (`categories.color`), so recolouring a route in the dashboard recolours the
 * blog with no deploy.
 *
 * Light mode needs a DARKER variant of each colour. Measured on #fafafa, every
 * live route colour fails as text and four of five fail the 3:1 non-text
 * threshold even as a fill:
 *
 *   Guides         #0AD25A  1.94:1
 *   Comparisons    #3B9DFF  2.70:1
 *   Proxy Types    #A855F7  3.79:1
 *   Best Practices #F59E0B  2.06:1
 *   Nigeria        #10B981  2.43:1
 *
 * So light mode substitutes a darkened variant (same idea as `--primary-text`).
 * The map is keyed by slug because that is the stable identifier — the display
 * name is editable in the dashboard and the colour already varies per route.
 *
 * A slug with no entry falls back to the DB colour rather than to nothing: a
 * route added later must never render invisible. The hairline ring keeps it
 * defined even when the fill is faint.
 */

/** Darkened light-mode fill per route slug. Verified >=4.8:1 on #fafafa. */
export const ROUTE_LIGHT_FILL: Record<string, string> = {
  guides: '#0b7a34',        // 5.23:1
  comparisons: '#1d4ed8',   // 6.42:1
  'proxy-types': '#7e22ce', // 6.69:1
  'best-practices': '#b45309', // 4.81:1
  nigeria: '#047857',       // 5.25:1
};

/** Ring colour for a node/dot in light mode. Subtle but present on #fafafa. */
export const ROUTE_RING_LIGHT = '#d1d5db';

/**
 * CSS custom properties for a route marker.
 *
 * Both variants are emitted and CSS picks by theme, because a server component
 * cannot branch on `prefers-color-scheme` — and light mode arrives by two
 * routes (the media query AND the `.light` admin class), so the choice has to
 * live in CSS, not in JS.
 */
export function routeColorVars(slug: string, apiColor?: string): React.CSSProperties {
  const dark = apiColor || 'var(--muted)';
  const light = ROUTE_LIGHT_FILL[slug] || dark;
  return {
    ['--route-dark' as string]: dark,
    ['--route-light' as string]: light,
    ['--route-ring' as string]: ROUTE_RING_LIGHT,
  };
}
