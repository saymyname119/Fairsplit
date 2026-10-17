export const Footer = () => (
  <footer style={{ borderTop: '1px solid var(--color-hairline)', padding: '24px 0', color: 'var(--color-muted)' }}>
    <div className="app-container" style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, fontSize: 13 }}>
      <span style={{ fontFamily: 'var(--font-display)', color: 'var(--color-ink)', fontWeight: 600 }}>FairSplit</span>
      <span>Shared expenses, made simple.</span>
    </div>
  </footer>
);
