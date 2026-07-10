import React, { useState } from 'react'

const LOGIN_URL = (import.meta.env.DEV ? 'http://localhost:8000' : '') + '/api/v1/auth/login'

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('captain')
  const [password, setPassword] = useState('abrarnuha3')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const res = await fetch(LOGIN_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim().toLowerCase(), password }),
      })

      if (res.ok) {
        const data = await res.json()
        localStorage.setItem('jarvis_auth', JSON.stringify({
          user: 'captain',
          at: Date.now(),
          token: data.token || null,
        }))
        onLogin()
      } else {
        setError('Access denied. Verify your credentials.')
      }
    } catch (_) {
      setError('Backend unreachable. Check your connection.')
    }

    setLoading(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="w-full max-w-sm px-4">
        <div className="bg-gray-800 rounded-lg shadow-lg p-8">
          <h1 className="text-2xl font-bold text-white mb-6">JARVIS Login</h1>

          {error && (
            <div className="mb-4 p-3 bg-red-900 text-red-200 rounded text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-4 py-2 bg-gray-700 text-white border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                autoFocus
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2 bg-gray-700 text-white border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded transition disabled:opacity-50"
            >
              {loading ? 'Authenticating...' : 'Login'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
