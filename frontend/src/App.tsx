import { useState, useEffect } from 'react'
import { TrendingUp, Wallet, BarChart3, Settings, LogOut, Power, Plus, Trash2, Zap, Activity, DollarSign, Bitcoin } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'
import './index.css'

const API = 'http://localhost:8000/api'

// ─── API Helper ───
async function api(path, options = {}) {
  const token = localStorage.getItem('token')
  const res = await fetch(API + path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(token && { Authorization: `Bearer ${token}` }), ...options.headers },
  })
  if (res.status === 401) { localStorage.removeItem('token'); window.location.reload() }
  return res.json()
}

// ─── App ───
export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [user, setUser] = useState(null)
  const [page, setPage] = useState('dashboard')
  const [dashboard, setDashboard] = useState(null)
  const [exchanges, setExchanges] = useState([])
  const [trades, setTrades] = useState([])

  useEffect(() => { if (token) fetchUser() }, [token])

  async function fetchUser() {
    const u = await api('/auth/me')
    if (u.id) { setUser(u); fetchDashboard(); fetchExchanges(); fetchTrades() }
  }

  async function fetchDashboard() { setDashboard(await api('/trading/dashboard')) }
  async function fetchExchanges() { setExchanges(await api('/exchanges/')) }
  async function fetchTrades() { const d = await api('/trading/history?days=7'); setTrades(d.trades || []) }

  if (!token) return <LoginPage onLogin={(t) => { localStorage.setItem('token', t); setToken(t) }} />

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#0a0a0f' }}>
      {/* Sidebar */}
      <aside style={{ width: 240, background: '#12121a', borderRight: '1px solid #1a1a2e', padding: 24, display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 40 }}>
          <Zap size={28} color="#6366f1" />
          <span style={{ fontSize: 20, fontWeight: 800, background: 'linear-gradient(135deg, #6366f1, #a855f7)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>CryptoQuant AI</span>
        </div>
        <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4 }}>
          {[
            { id: 'dashboard', icon: <Activity size={18} />, label: '仪表盘' },
            { id: 'exchanges', icon: <Wallet size={18} />, label: '交易所' },
            { id: 'strategies', icon: <BarChart3 size={18} />, label: '策略' },
            { id: 'trades', icon: <TrendingUp size={18} />, label: '交易记录' },
            { id: 'settings', icon: <Settings size={18} />, label: '设置' },
          ].map(item => (
            <button key={item.id} onClick={() => setPage(item.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px',
                borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: 14,
                background: page === item.id ? '#1a1a2e' : 'transparent',
                color: page === item.id ? '#f8fafc' : '#94a3b8',
                transition: 'all 0.15s',
              }}>
              {item.icon} {item.label}
            </button>
          ))}
        </nav>
        <div style={{ borderTop: '1px solid #1a1a2e', paddingTop: 16, fontSize: 13, color: '#64748b' }}>
          <div>{user?.username} · {user?.subscription_tier}</div>
          <button onClick={() => { localStorage.removeItem('token'); setToken(null) }}
            style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8, background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: 13 }}>
            <LogOut size={14} /> 退出
          </button>
        </div>
      </aside>

      {/* Main */}
      <main style={{ flex: 1, padding: 32, overflowY: 'auto' }}>
        {page === 'dashboard' && <Dashboard data={dashboard} trades={trades} />}
        {page === 'exchanges' && <ExchangePage exchanges={exchanges} onUpdate={fetchExchanges} />}
        {page === 'trades' && <TradesPage trades={trades} />}
        {page === 'strategies' && <StrategiesPage />}
        {page === 'settings' && <SettingsPage user={user} />}
      </main>
    </div>
  )
}

// ─── Login Page ───
function LoginPage({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isRegister, setIsRegister] = useState(false)
  const [username, setUsername] = useState('')
  const [error, setError] = useState('')

  async function submit() {
    setError('')
    const endpoint = isRegister ? '/auth/register' : '/auth/login'
    const body = isRegister ? { email, password, username } : { email, password }
    try {
      const res = await fetch(API + endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      const data = await res.json()
      if (data.token) { onLogin(data.token) } else { setError(data.detail || '登录失败') }
    } catch { setError('网络错误') }
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%)' }}>
      <div style={{ width: 400, padding: 40, background: '#12121a', borderRadius: 16, border: '1px solid #1a1a2e' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Zap size={40} color="#6366f1" />
          <h1 style={{ fontSize: 24, fontWeight: 700, marginTop: 12, background: 'linear-gradient(135deg, #6366f1, #a855f7)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            CryptoQuant AI
          </h1>
          <p style={{ color: '#64748b', fontSize: 14, marginTop: 4 }}>AI 量化交易平台</p>
        </div>
        {error && <div style={{ background: '#3b0a0a', color: '#fca5a5', padding: 10, borderRadius: 8, marginBottom: 16, fontSize: 13 }}>{error}</div>}
        {isRegister && <input placeholder="用户名" value={username} onChange={e => setUsername(e.target.value)}
          style={inputStyle} />}
        <input placeholder="邮箱" value={email} onChange={e => setEmail(e.target.value)} style={inputStyle} />
        <input placeholder="密码" type="password" value={password} onChange={e => setPassword(e.target.value)} style={inputStyle}
          onKeyDown={e => e.key === 'Enter' && submit()} />
        <button onClick={submit} style={{ ...btnPrimary, width: '100%', marginTop: 8, padding: 14 }}>
          {isRegister ? '注册' : '登录'}
        </button>
        <p style={{ textAlign: 'center', marginTop: 16, fontSize: 13, color: '#64748b' }}>
          {isRegister ? '已有账号？' : '没有账号？'}
          <button onClick={() => setIsRegister(!isRegister)} style={{ background: 'none', border: 'none', color: '#6366f1', cursor: 'pointer', fontSize: 13, marginLeft: 4 }}>
            {isRegister ? '登录' : '注册'}
          </button>
        </p>
      </div>
    </div>
  )
}

const inputStyle = {
  width: '100%', padding: '12px 14px', marginBottom: 10, borderRadius: 8,
  border: '1px solid #1e293b', background: '#0a0a0f', color: '#f8fafc', fontSize: 14, outline: 'none',
}

const btnPrimary = {
  padding: '10px 20px', borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: 14, fontWeight: 600,
  background: 'linear-gradient(135deg, #6366f1, #a855f7)', color: '#fff',
}

// ─── Dashboard ───
function Dashboard({ data, trades }) {
  if (!data) return <div style={{ color: '#64748b' }}>加载中...</div>

  const cards = [
    { icon: <DollarSign size={20} color="#10b981" />, label: '今日盈亏', value: `$${(data.today_pnl || 0).toLocaleString()}`, sub: `${data.today_pnl_pct || 0}%`, color: data.today_pnl >= 0 ? '#10b981' : '#ef4444' },
    { icon: <Activity size={20} color="#6366f1" />, label: '交易次数', value: data.total_trades_today || 0, sub: `胜率 ${data.win_rate || 0}%` },
    { icon: <Wallet size={20} color="#a855f7" />, label: '总资产', value: `$${(data.total_balance || 0).toLocaleString()}`, sub: `${data.active_strategies} 个策略运行中` },
    { icon: <Bitcoin size={20} color="#06b6d4" />, label: '交易量', value: `$${(data.total_volume || 0).toLocaleString()}`, sub: '今日累计' },
  ]

  // Mock chart data (will be replaced by real data from API)
  const chartData = trades?.slice(-20).map(t => ({ time: new Date(t.created_at).toLocaleTimeString(), pnl: t.pnl })) || []

  return (
    <div>
      <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>📊 仪表盘</h2>

      {/* Stats Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        {cards.map((c, i) => (
          <div key={i} style={{ background: '#12121a', border: '1px solid #1a1a2e', borderRadius: 12, padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ color: '#64748b', fontSize: 12, marginBottom: 4 }}>{c.label}</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: c.color || '#f8fafc' }}>{c.value}</div>
                <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>{c.sub}</div>
              </div>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: '#1a1a2e', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {c.icon}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Chart */}
      <div style={{ background: '#12121a', border: '1px solid #1a1a2e', borderRadius: 12, padding: 24, marginBottom: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>📈 盈亏走势</h3>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={chartData.length > 0 ? chartData : generateMockData()}>
            <defs><linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#6366f1" stopOpacity={0.3} /><stop offset="100%" stopColor="#6366f1" stopOpacity={0} /></linearGradient></defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="time" stroke="#475569" fontSize={11} />
            <YAxis stroke="#475569" fontSize={11} />
            <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid #25253e', borderRadius: 8, color: '#f8fafc' }} />
            <Area type="monotone" dataKey="pnl" stroke="#6366f1" fill="url(#pnlGrad)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Exchange Balances */}
      <div style={{ background: '#12121a', border: '1px solid #1a1a2e', borderRadius: 12, padding: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>💰 资产分布</h3>
        {(data.balances || []).map((b, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: i < (data.balances?.length || 0) - 1 ? '1px solid #1a1a2e' : 'none' }}>
            <span style={{ textTransform: 'capitalize' }}>{b.exchange}</span>
            <span style={{ fontWeight: 600, color: '#10b981' }}>${b.balance?.toLocaleString() || '0'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function generateMockData() {
  const data = [] as any[]
  let pnl = 0
  for (let i = 0; i < 20; i++) {
    pnl += (Math.random() - 0.45) * 20
    data.push({ time: `${i}:00`, pnl: Math.round(pnl) })
  }
  return data
}

// ─── Exchange Page ───
function ExchangePage({ exchanges, onUpdate }) {
  const [exchange, setExchange] = useState('binance')
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [passphrase, setPassphrase] = useState('')
  const [loading, setLoading] = useState(false)

  async function addExchange() {
    setLoading(true)
    await api('/exchanges/add', {
      method: 'POST',
      body: JSON.stringify({ exchange, api_key: apiKey, api_secret: apiSecret, passphrase: passphrase || null }),
    })
    setApiKey(''); setApiSecret(''); setPassphrase('')
    onUpdate()
    setLoading(false)
  }

  async function removeExchange(id) {
    await api(`/exchanges/${id}`, { method: 'DELETE' })
    onUpdate()
  }

  return (
    <div>
      <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>🔗 交易所管理</h2>

      {/* Add Form */}
      <div style={{ background: '#12121a', border: '1px solid #1a1a2e', borderRadius: 12, padding: 24, marginBottom: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>添加交易所</h3>
        <select value={exchange} onChange={e => setExchange(e.target.value)} style={inputStyle}>
          <option value="binance">Binance 币安</option>
          <option value="okx">OKX</option>
          <option value="bybit">Bybit</option>
        </select>
        <input placeholder="API Key" value={apiKey} onChange={e => setApiKey(e.target.value)} style={inputStyle} />
        <input placeholder="API Secret" value={apiSecret} onChange={e => setApiSecret(e.target.value)} style={inputStyle} />
        {exchange === 'okx' && <input placeholder="Passphrase (OKX专用)" value={passphrase} onChange={e => setPassphrase(e.target.value)} style={inputStyle} />}
        <button onClick={addExchange} disabled={!apiKey || !apiSecret || loading} style={{ ...btnPrimary, opacity: !apiKey || !apiSecret ? 0.5 : 1 }}>
          {loading ? '添加中...' : '添加'}
        </button>
      </div>

      {/* List */}
      <div style={{ background: '#12121a', border: '1px solid #1a1a2e', borderRadius: 12, padding: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>已添加 ({exchanges.length})</h3>
        {exchanges.length === 0 && <div style={{ color: '#64748b', textAlign: 'center', padding: 40 }}>尚未添加任何交易所</div>}
        {exchanges.map(e => (
          <div key={e.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #1a1a2e' }}>
            <div>
              <div style={{ fontWeight: 600, textTransform: 'capitalize' }}>{e.exchange}</div>
              <div style={{ fontSize: 12, color: '#64748b', fontFamily: 'monospace' }}>{e.api_key}</div>
            </div>
            <button onClick={() => removeExchange(e.id)} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer' }}>
              <Trash2 size={16} />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Trades Page ───
function TradesPage({ trades }) {
  return (
    <div>
      <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>📋 交易记录</h2>
      <div style={{ background: '#12121a', border: '1px solid #1a1a2e', borderRadius: 12, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #1a1a2e', color: '#64748b', textAlign: 'left' }}>
              <th style={thStyle}>时间</th><th style={thStyle}>交易所</th><th style={thStyle}>币对</th><th style={thStyle}>方向</th><th style={thStyle}>价格</th><th style={thStyle}>数量</th><th style={thStyle}>盈亏</th>
            </tr>
          </thead>
          <tbody>
            {trades?.map(t => (
              <tr key={t.id} style={{ borderBottom: '1px solid #0f0f1a' }}>
                <td style={tdStyle}>{new Date(t.created_at).toLocaleString()}</td>
                <td style={tdStyle}>{t.exchange}</td>
                <td style={tdStyle}>{t.symbol}</td>
                <td style={{ ...tdStyle, color: t.side === 'buy' ? '#10b981' : '#ef4444' }}>{t.side === 'buy' ? '买入' : '卖出'}</td>
                <td style={tdStyle}>${t.price}</td>
                <td style={tdStyle}>{t.amount}</td>
                <td style={{ ...tdStyle, color: t.pnl >= 0 ? '#10b981' : '#ef4444', fontWeight: 600 }}>${t.pnl?.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {(!trades || trades.length === 0) && <div style={{ color: '#64748b', textAlign: 'center', padding: 40 }}>暂无交易记录</div>}
      </div>
    </div>
  )
}

const thStyle = { padding: '12px 16px', fontWeight: 500 } as const
const tdStyle = { padding: '10px 16px' } as const

// ─── Strategies Page ───
function StrategiesPage() {
  async function trainAI() {
    const keyId = prompt('输入交易所密钥 ID:')
    const symbol = prompt('币对 (默认 BTC/USDT):', 'BTC/USDT') || 'BTC/USDT'
    if (!keyId) return
    const result = await api(`/trading/ai/train?exchange_key_id=${keyId}&symbol=${symbol}`, { method: 'POST' })
    alert(JSON.stringify(result, null, 2))
  }

  return (
    <div>
      <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>🤖 AI 策略</h2>
      <div style={{ background: '#12121a', border: '1px solid #1a1a2e', borderRadius: 12, padding: 24 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>ML 模型训练</h3>
        <p style={{ color: '#64748b', fontSize: 13, marginBottom: 16 }}>基于 XGBoost 机器学习算法，分析 K 线形态和技术指标，预测短期价格走势。</p>
        <button onClick={trainAI} style={btnPrimary}>🧠 训练 AI 模型</button>
      </div>
    </div>
  )
}

// ─── Settings Page ───
function SettingsPage({ user }) {
  return (
    <div>
      <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>⚙️ 设置</h2>
      <div style={{ background: '#12121a', border: '1px solid #1a1a2e', borderRadius: 12, padding: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid #1a1a2e' }}>
          <span>用户名</span><span>{user?.username}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid #1a1a2e' }}>
          <span>邮箱</span><span>{user?.email}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid #1a1a2e' }}>
          <span>订阅套餐</span><span style={{ color: '#a855f7', fontWeight: 600, textTransform: 'uppercase' }}>{user?.subscription_tier}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0' }}>
          <span>到期时间</span><span>{user?.subscription_expires ? new Date(user.subscription_expires).toLocaleDateString() : '-'}</span>
        </div>
      </div>
    </div>
  )
}
