import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'

export default function PasswordField({ label, labelExtra, value, onChange, autoComplete, placeholder, name }) {
  const [show, setShow] = useState(false)
  return (
    <label>
      <span>{label} {labelExtra}</span>
      <div className="password-input">
        <input
          name={name}
          type={show ? 'text' : 'password'}
          autoComplete={autoComplete}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
        />
        <button type="button" onClick={() => setShow(!show)} aria-label={show ? 'Hide password' : 'Show password'}>
          {show ? <EyeOff /> : <Eye />}
        </button>
      </div>
    </label>
  )
}
