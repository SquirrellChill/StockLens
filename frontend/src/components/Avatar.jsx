export const initialsOf = (name) =>
  String(name || 'U').trim().split(/\s+/).map((x) => x[0]).join('').slice(0, 2).toUpperCase() || 'U'

/** Profile photo when the user has one, otherwise their initials. */
export default function Avatar({ user, className = 'avatar' }) {
  const name = user?.name || user?.full_name || user?.email || 'Account'
  if (user?.avatar_url) return <img className={className} src={user.avatar_url} alt="" />
  return <span className={className}>{initialsOf(name)}</span>
}
