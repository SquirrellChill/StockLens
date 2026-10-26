import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { Mic } from 'lucide-react'
import Button from '../components/Button'
import { useVoiceInput } from '../hooks/useVoiceInput'
import { productService } from '../services/productService'
import { salesService } from '../services/salesService'
import { parseSaleCommand } from '../utils/parseSaleCommand'

export default function VoiceSales() {
  const navigate = useNavigate()
  const [products, setProducts] = useState([])
  const [result, setResult] = useState(null)
  const [typed, setTyped] = useState('')

  useEffect(() => { productService.list().then(setProducts).catch(() => {}) }, [])

  const handle = (text) => setResult({ text, ...parseSaleCommand(text, products) })
  const { supported, listening, transcript, error, start } = useVoiceInput({ onResult: handle })

  const addAll = () => {
    result.matched.forEach(({ product, quantity }) => salesService.addToDraft(product, quantity))
    navigate('/app/sales')
  }

  return (
    <>
      <div className="title-row"><div><h1>Record sales by voice</h1><p>Speak naturally, then review before updating stock.</p></div></div>
      <section className="flow-card voice-card">
        <div className="voice-ring"><button type="button" aria-label="Start listening" onClick={start} className={listening ? 'recording' : ''}><Mic size={34} /></button></div>
        <h2>{listening ? 'Listening…' : 'Tap to speak'}</h2>
        <p>Try saying: “Sold three Coca-Cola and two chips.”</p>
        {error && <div className="form-error" role="alert" style={{ marginTop: 14 }}>{error}</div>}
        {transcript && <div className="transcript">“{transcript}”</div>}

        <div className="or"><span>{supported ? 'or type it' : 'type it instead'}</span></div>
        <form className="manual-sale" style={{ gridTemplateColumns: '1fr auto' }} onSubmit={(e) => { e.preventDefault(); if (typed.trim()) handle(typed) }}>
          <label><span>What did you sell?</span><input value={typed} onChange={(e) => setTyped(e.target.value)} placeholder="e.g. sold 2 milk and 1 water" /></label>
          <Button type="submit">Parse</Button>
        </form>

        {result && (
          <div style={{ textAlign: 'left', marginTop: 22 }}>
            {result.matched.length > 0 && (
              <div className="panel">
                {result.matched.map(({ product, quantity }, i) => (
                  <div className="draft-row" key={i}><div><strong>{product.name}</strong><small>{product.quantity} in stock</small></div><b>× {quantity}</b></div>
                ))}
              </div>
            )}
            {result.unmatched.length > 0 && (
              <div className="notice warning" style={{ marginTop: 12 }}>
                <div><strong>Couldn’t match</strong><p>{result.unmatched.map((u) => `“${u}”`).join(', ')}</p></div>
              </div>
            )}
            <div className="flow-actions">
              <Button kind="secondary" onClick={() => setResult(null)}>Clear</Button>
              <Button disabled={!result.matched.length} onClick={addAll}>Add to today’s sales</Button>
            </div>
          </div>
        )}
      </section>
    </>
  )
}
