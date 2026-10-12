/**
 * Unit tests for detectReceiptTheme() — the REAL function, not a copy.
 *
 * Strategy: read the TypeScript source, extract the function body, evaluate it
 * in a Node vm context with mocked window/document. This tests the actual
 * shipped code path.
 *
 * Run: node src/lib/__tests__/pdf-receipt-theme.test.mjs
 */

import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import vm from 'vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(resolve(__dirname, '../pdf-receipt.ts'), 'utf8');

// Extract the detectReceiptTheme function from the source.
// Find the specific JSDoc comment, then capture the function body up to its
// closing brace at column 0.
const commentStart = source.indexOf('/** Effective-site-theme detection');
if (commentStart === -1) {
  console.error('FAIL: could not find detectReceiptTheme JSDoc in pdf-receipt.ts');
  process.exit(1);
}
const fnStart = source.indexOf('export function detectReceiptTheme()', commentStart);
if (fnStart === -1) {
  console.error('FAIL: could not find detectReceiptTheme function in pdf-receipt.ts');
  process.exit(1);
}
// Find the closing brace: the first line that is exactly "}" after the function start.
const afterFn = source.indexOf('{', fnStart);
let braceDepth = 0;
let fnEnd = afterFn;
for (let i = afterFn; i < source.length; i++) {
  if (source[i] === '{') braceDepth++;
  if (source[i] === '}') {
    braceDepth--;
    if (braceDepth === 0) { fnEnd = i + 1; break; }
  }
}
// Strip TypeScript return type annotation so the function is valid JS.
const fnSource = source
  .slice(commentStart, fnEnd)
  .replace('export function', 'function')
  .replace('): ReceiptTheme {', ') {');
console.log('Extracted function:\n', fnSource, '\n');

/**
 * Build a fresh sandbox with the given DOM state, then run the extracted
 * detectReceiptTheme and return its result.
 */
function detectInSandbox({ htmlClass, osScheme }) {
  const lightMQ = { matches: osScheme === 'light' };
  const darkMQ = { matches: osScheme === 'dark' };
  const classList = {
    _set: new Set(htmlClass ? [htmlClass] : []),
    contains(c) { return this._set.has(c); },
    add(c) { this._set.add(c); },
    remove(...cs) { cs.forEach(c => this._set.delete(c)); },
  };
  const sandbox = {
    window: {
      matchMedia(query) {
        if (query === '(prefers-color-scheme: light)') return lightMQ;
        if (query === '(prefers-color-scheme: dark)') return darkMQ;
        throw new Error('unexpected query: ' + query);
      },
    },
    document: {
      documentElement: { classList },
    },
  };
  vm.createContext(sandbox);
  const result = vm.runInContext(
    `${fnSource}\ndetectReceiptTheme();`,
    sandbox,
  );
  return result;
}

// ── Test cases ──────────────────────────────────────────────
let passed = 0;
let failed = 0;

function assert(name, actual, expected) {
  if (actual === expected) {
    console.log(`  PASS  ${name} → ${actual}`);
    passed++;
  } else {
    console.error(`  FAIL  ${name} → expected ${expected}, got ${actual}`);
    failed++;
  }
}

console.log('── Four combinations (html class + OS scheme) ──');

// 1. html.light + OS dark → light
assert(
  'html.light + OS dark → light',
  detectInSandbox({ htmlClass: 'light', osScheme: 'dark' }),
  'light',
);

// 2. html.dark + OS light → dark
assert(
  'html.dark + OS light → dark',
  detectInSandbox({ htmlClass: 'dark', osScheme: 'light' }),
  'dark',
);

// 3. html.light + OS light → light
assert(
  'html.light + OS light → light',
  detectInSandbox({ htmlClass: 'light', osScheme: 'light' }),
  'light',
);

// 4. html.dark + OS dark → dark
assert(
  'html.dark + OS dark → dark',
  detectInSandbox({ htmlClass: 'dark', osScheme: 'dark' }),
  'dark',
);

console.log('\n── Fallback (no html class) ──');

// 5. no class + OS light → light
assert(
  'no class + OS light → light',
  detectInSandbox({ htmlClass: null, osScheme: 'light' }),
  'light',
);

// 6. no class + OS dark → dark
assert(
  'no class + OS dark → dark',
  detectInSandbox({ htmlClass: null, osScheme: 'dark' }),
  'dark',
);

console.log('\n── SSR safety ──');

// 7. window undefined → dark
const sandboxNoWindow = {
  window: undefined,
  document: undefined,
};
vm.createContext(sandboxNoWindow);
const ssrResult = vm.runInContext(
  `${fnSource}\ndetectReceiptTheme();`,
  sandboxNoWindow,
);
assert('window undefined → dark', ssrResult, 'dark');

// ── Summary ─────────────────────────────────────────────────
console.log(`\n${'─'.repeat(40)}`);
console.log(`  ${passed} passed, ${failed} failed`);
console.log(`${'─'.repeat(40)}`);
process.exit(failed > 0 ? 1 : 0);