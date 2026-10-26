export default function Button({ children, kind = 'primary', icon: Icon, className = '', type = 'button', ...props }) {
  return (
    <button type={type} className={`button ${kind} ${className}`.trim()} {...props}>
      {Icon && <Icon size={18} />}
      {children}
    </button>
  )
}
