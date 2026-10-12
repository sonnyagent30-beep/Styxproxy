'use client';

// Renders markdown legal text as plain text — no HTML injection risk
// Strips markdown syntax but preserves readable formatting with line breaks and spacing
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export default function LegalContent({ content }: { content: string }) {
  // Process markdown to readable HTML-safe text
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const nextLine = lines[i + 1];

    // Skip module.exports lines
    if (line.includes('module.exports') || line.includes('const content')) {
      i++;
      continue;
    }

    // Horizontal rule
    if (line.match(/^[-*_]{3,}$/)) {
      elements.push(<hr key={i} style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '1.5rem 0' }} />);
      i++;
      continue;
    }

    // Heading 1
    if (line.startsWith('# ')) {
      elements.push(
        <h1 key={i} style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.75rem', color: 'var(--foreground)' }}>
          {escapeHtml(line.slice(2))}
        </h1>
      );
      i++;
      continue;
    }

    // Heading 2
    if (line.startsWith('## ')) {
      elements.push(
        <h2 key={i} style={{ fontSize: '1.125rem', fontWeight: 700, marginTop: '1.5rem', marginBottom: '0.5rem', color: 'var(--foreground)' }}>
          {escapeHtml(line.slice(3))}
        </h2>
      );
      i++;
      continue;
    }

    // Heading 3
    if (line.startsWith('### ')) {
      elements.push(
        <h3 key={i} style={{ fontSize: '0.95rem', fontWeight: 600, marginTop: '1.25rem', marginBottom: '0.4rem', color: 'var(--foreground)' }}>
          {escapeHtml(line.slice(4))}
        </h3>
      );
      i++;
      continue;
    }

    // Heading 4
    if (line.startsWith('#### ')) {
      elements.push(
        <h4 key={i} style={{ fontSize: '0.9rem', fontWeight: 600, marginTop: '1rem', marginBottom: '0.3rem', color: 'var(--foreground)' }}>
          {escapeHtml(line.slice(5))}
        </h4>
      );
      i++;
      continue;
    }

    // Unordered list item
    if (line.match(/^[-*] /)) {
      const items: React.ReactNode[] = [];
      while (i < lines.length && lines[i].match(/^[-*] /)) {
        const text = lines[i].slice(2);
        // Handle bold text
        const rendered = text.split(/(\*\*[^*]+\*\*)/).map((part, j) =>
          part.startsWith('**') && part.endsWith('**')
            ? <strong key={j}>{part.slice(2, -2)}</strong>
            : escapeHtml(part)
        );
        items.push(<li key={i} style={{ marginLeft: '1.25rem', marginBottom: '0.25rem' }}>{rendered}</li>);
        i++;
      }
      elements.push(<ul key={`ul-${i}`} style={{ margin: '0.75rem 0 0.75rem 0', paddingLeft: '0.5rem', listStyle: 'disc' }}>{items}</ul>);
      continue;
    }

    // Paragraph (non-empty line)
    if (line.trim()) {
      // Skip italic version lines that follow bold headings (e.g., *Effective Date:...*)
      if (line.startsWith('*') && line.endsWith('*') && line.slice(1, -1).includes('Effective Date')) {
        elements.push(
          <p key={i} style={{ color: 'var(--muted)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
            {line.slice(1, -1)}
          </p>
        );
        i++;
        continue;
      }

      // Skip lines that are just bolded italic dates (after h1)
      if (line.match(/^\*[^*]+\*Effective Date[^*]+\*$/)) {
        elements.push(
          <p key={i} style={{ color: 'var(--muted)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
            {escapeHtml(line.replace(/\*/g, ''))}
          </p>
        );
        i++;
        continue;
      }

      // Regular paragraph with bold/italic inline rendering
      const rendered = line.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/).map((part, j) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={j} style={{ fontWeight: 600 }}>{part.slice(2, -2)}</strong>;
        }
        if (part.startsWith('*') && part.endsWith('*')) {
          return <em key={j}>{part.slice(1, -1)}</em>;
        }
        return escapeHtml(part);
      });

      elements.push(
        <p key={i} style={{ margin: '0.6rem 0', lineHeight: 1.7 }}>
          {rendered}
        </p>
      );
      i++;
      continue;
    }

    // Empty line
    i++;
  }

  return <>{elements}</>;
}
