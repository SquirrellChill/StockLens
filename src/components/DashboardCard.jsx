export default function DashboardCard({ icon: Icon, label, value, note, tone = '' }) {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${tone}`}><Icon size={21} /></div>
      <div><p>{label}</p><strong>{value}</strong><small>{note}</small></div>
    </div>
  )
}
