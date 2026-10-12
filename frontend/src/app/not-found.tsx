export default function NotFound() {
  return (
    <html lang="en">
      <body style={{ background: '#0a0a0a', color: '#fff', fontFamily: 'sans-serif', display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', margin: 0 }}>
        <div style={{ textAlign: 'center' }}>
          <h1 style={{ fontSize: '6rem', margin: 0, color: '#0AD25A' }}>404</h1>
          <p style={{ fontSize: '1.5rem', marginTop: '1rem' }}>Page not found</p>
          <a href="/" style={{ color: '#0AD25A', marginTop: '1rem', display: 'inline-block' }}>Return home</a>
        </div>
      </body>
    </html>
  );
}
