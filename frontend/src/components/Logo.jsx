export default function Logo({ compact = false }) {
  return (
    <div className="logo-wrap" aria-label="StockLens">
      <span className="logo-mark"><span /><span /><span /></span>
      {!compact && <span className="logo-text">Stock<span>Lens</span></span>}
    </div>
  )
}
