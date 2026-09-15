import { useState, useEffect } from 'react'

/**
 * The frontend fetches from localhost:8000 because, from the user's browser,
 * the API container is exposed on the host's port 8000. Docker internal
 * networking (service names) only works between containers, not from the browser.
 */
const API_URL = 'http://localhost:8000'

function App() {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showRaw, setShowRaw] = useState(false)

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => res.json())
      .then((data) => {
        setHealth(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div className="container">
        <div className="card">
          <div className="spinner" />
          <p className="loading-text">Connecting to backend…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container">
        <div className="card">
          <h1>🔴 Lenny Growth Assistant</h1>
          <p className="error">Could not reach backend: {error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container">
      <div className="card">
        <h1>🚀 Lenny Growth Assistant</h1>
        <p className="subtitle">System Health Dashboard</p>

        <div className="status-grid">
          <div className="status-item">
            <span className="label">Backend</span>
            <span className={`badge ${health.status === 'ok' ? 'badge-ok' : 'badge-warn'}`}>
              {health.status}
            </span>
          </div>
          <div className="status-item">
            <span className="label">Database</span>
            <span className={`badge ${health.database === 'connected' ? 'badge-ok' : 'badge-warn'}`}>
              {health.database}
            </span>
          </div>
          <div className="status-item">
            <span className="label">LLM Provider</span>
            <span className="badge badge-info">{health.provider}</span>
          </div>
        </div>

        {health.error && (
          <div className="error-box">
            <strong>Error:</strong> {health.error}
          </div>
        )}

        <button className="raw-toggle" onClick={() => setShowRaw(!showRaw)}>
          {showRaw ? 'Hide' : 'Show'} Raw Response
        </button>

        {showRaw && (
          <pre className="raw-json">{JSON.stringify(health, null, 2)}</pre>
        )}
      </div>
    </div>
  )
}

export default App
