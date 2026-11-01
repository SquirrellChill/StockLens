import { useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { AlertTriangle, Camera, CheckCircle2, LogOut, Trash2 } from 'lucide-react'
import Button from '../components/Button'
import Modal from '../components/Modal'
import PasswordField from '../components/PasswordField'
import Avatar from '../components/Avatar'
import { useAuth } from '../auth/AuthContext'
import { USE_MOCK } from '../services/api'
import { isEmail, passwordError } from '../utils/validation'

export default function Settings() {
  const { user, updateProfile, uploadAvatar, removeAvatar, forgotPassword, resetPassword, logout } = useAuth()
  const fileRef = useRef(null)
  const navigate = useNavigate()
  const [profile, setProfile] = useState({ name: user?.name || user?.full_name || '', email: user?.email || '' })
  const [pw, setPw] = useState({ code: '', next: '', confirm: '' })
  const [codeSent, setCodeSent] = useState(false)
  const [demoCode, setDemoCode] = useState('')
  const [busy, setBusy] = useState('')
  const [message, setMessage] = useState(null)
  const [confirmLogout, setConfirmLogout] = useState(false)

  const say = (type, text) => setMessage({ type, text })

  const saveProfile = async (e) => {
    e.preventDefault()
    setMessage(null)
    if (!profile.name.trim() || !profile.email.trim()) return say('error', 'Name and email are required.')
    if (!isEmail(profile.email)) return say('error', 'Please enter a valid email address.')
    setBusy('profile')
    try { await updateProfile(profile); say('success', 'Your profile has been updated.') }
    catch (err) { say('error', err.message) }
    finally { setBusy('') }
  }

  const pickPhoto = async (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setMessage(null)
    setBusy('photo')
    try { await uploadAvatar(file); say('success', 'Your profile photo has been updated.') }
    catch (err) { say('error', err.message) }
    finally { setBusy('') }
  }

  const deletePhoto = async () => {
    setMessage(null)
    setBusy('photo')
    try { await removeAvatar(); say('success', 'Your profile photo has been removed.') }
    catch (err) { say('error', err.message) }
    finally { setBusy('') }
  }

  // Changing a password re-uses the forgot-password flow: verify by emailed code first.
  const sendCode = async () => {
    setMessage(null)
    setBusy('code')
    try {
      const res = (await forgotPassword(user.email)) || {}
      setDemoCode(res.demo_reset_code || '')
      setCodeSent(true)
      say('success', `We’ve sent a 6-digit code to ${user.email}.`)
    } catch (err) { say('error', err.message) }
    finally { setBusy('') }
  }

  const savePassword = async (e) => {
    e.preventDefault()
    setMessage(null)
    if (!/^\d{6}$/.test(pw.code.trim())) return say('error', 'Enter the 6-digit code we sent you.')
    const problem = passwordError(pw.next)
    if (problem) return say('error', problem.replace('Password', 'New password'))
    if (pw.next !== pw.confirm) return say('error', 'New passwords do not match.')
    setBusy('password')
    try {
      await resetPassword(user.email, pw.code.trim(), pw.next)
      setPw({ code: '', next: '', confirm: '' })
      setCodeSent(false)
      setDemoCode('')
      say('success', 'Your password has been changed.')
    } catch (err) { say('error', err.message) }
    finally { setBusy('') }
  }

  const doLogout = async () => {
    setBusy('logout')
    await logout()
    navigate('/', { replace: true })
  }

  return (
    <>
      <div className="title-row"><div><h1>Settings</h1><p>Manage your account and security.</p></div></div>
      {message && <div className={`settings-message ${message.type}`} role={message.type === 'error' ? 'alert' : 'status'}>{message.type === 'success' ? <CheckCircle2 /> : <AlertTriangle />}<span>{message.text}</span></div>}
      <div className="settings-grid">
        <section className="panel settings-profile">
          <div className="settings-section-head"><h2>Profile information</h2><p>Update how your account appears in StockLens.</p></div>
          <div className="profile-summary">
            <Avatar user={user} className="profile-avatar" />
            <div>
              <strong>{user?.name || user?.full_name || 'StockLens user'}</strong><small>{user?.email}</small>
              <div className="photo-actions">
                <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp,image/gif" hidden onChange={pickPhoto} />
                <Button type="button" kind="secondary" icon={Camera} disabled={busy === 'photo'} onClick={() => fileRef.current?.click()}>{busy === 'photo' ? 'Saving…' : user?.avatar_url ? 'Change photo' : 'Add photo'}</Button>
                {user?.avatar_url && <Button type="button" kind="secondary" icon={Trash2} disabled={busy === 'photo'} onClick={deletePhoto}>Remove</Button>}
              </div>
            </div>
          </div>
          <form className="settings-form" onSubmit={saveProfile} noValidate>
            <label><span>Full name</span><input name="name" value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} /></label>
            <label><span>Email address</span><input name="email" type="email" value={profile.email} onChange={(e) => setProfile({ ...profile, email: e.target.value })} /></label>
            <Button type="submit" disabled={busy === 'profile'}>{busy === 'profile' ? 'Saving…' : 'Save changes'}</Button>
          </form>
        </section>
        <section className="panel settings-profile">
          <div className="settings-section-head"><h2>Change password</h2><p>For your security we verify it’s you with a code sent to your email.</p></div>
          {!codeSent ? (
            <div className="settings-form">
              <p className="settings-hint">We’ll email a 6-digit code to <b>{user?.email}</b>. Enter it with your new password to finish.</p>
              <Button type="button" disabled={busy === 'code'} onClick={sendCode}>{busy === 'code' ? 'Sending…' : 'Send verification code'}</Button>
            </div>
          ) : (
            <form className="settings-form" onSubmit={savePassword} noValidate>
              {USE_MOCK && demoCode && <div className="demo-hint">Demo mode sends no email. Your code is <b>{demoCode}</b>.</div>}
              <label><span>6-digit code</span><input name="code" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={pw.code} onChange={(e) => setPw({ ...pw, code: e.target.value.replace(/\D/g, '') })} placeholder="123456" /></label>
              <PasswordField name="next" label="New password" autoComplete="new-password" value={pw.next} onChange={(next) => setPw({ ...pw, next })} />
              <PasswordField name="confirm" label="Confirm new password" autoComplete="new-password" value={pw.confirm} onChange={(confirm) => setPw({ ...pw, confirm })} />
              <div className="settings-inline">
                <Button type="submit" disabled={busy === 'password'}>{busy === 'password' ? 'Updating…' : 'Change password'}</Button>
                <Button type="button" kind="secondary" disabled={busy === 'code'} onClick={sendCode}>Resend code</Button>
              </div>
            </form>
          )}
        </section>
      </div>
      <section className="panel logout-panel">
        <div><strong>Log out of StockLens</strong><p>You will need to log in again to access your shop.</p></div>
        <Button kind="danger" icon={LogOut} onClick={() => setConfirmLogout(true)}>Log out</Button>
      </section>
      {confirmLogout && (
        <Modal onClose={() => setConfirmLogout(false)} className="confirm-modal" label="Log out">
          <span className="confirm-icon"><LogOut /></span>
          <h2>Log out of StockLens?</h2>
          <p>You’ll be returned to the public landing page.</p>
          <div className="modal-actions">
            <Button kind="secondary" onClick={() => setConfirmLogout(false)}>Cancel</Button>
            <Button kind="danger" disabled={busy === 'logout'} onClick={doLogout}>{busy === 'logout' ? 'Logging out…' : 'Log out'}</Button>
          </div>
        </Modal>
      )}
    </>
  )
}
