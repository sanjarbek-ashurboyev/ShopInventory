import { lazy, Suspense, type ReactNode } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router'
import { useMe } from './api/hooks'
import { useAuth } from './auth'
import Layout from './components/Layout'
import AddStock from './pages/AddStock'
import DailyReport from './pages/DailyReport'
import EditEntry from './pages/EditEntry'
import Entry from './pages/Entry'
import Export from './pages/Export'
import Home from './pages/Home'
import Labels from './pages/Labels'
import Login from './pages/Login'
import Reports from './pages/Reports'
import Sell from './pages/Sell'
import Stats from './pages/Stats'
import StockList from './pages/StockList'
import { ErrorNotice, Loading } from './components/ui'

// The barcode decoder is large; load it only when the scanner is opened.
const Scan = lazy(() => import('./pages/Scan'))

function RequireLogin({ children }: { children: ReactNode }) {
  const { loggedIn } = useAuth()
  const location = useLocation()
  if (!loggedIn) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  return children
}

/** Purchase prices, profit and stock changes; the API refuses these to sellers as well. */
function OwnerOnly({ children }: { children: ReactNode }) {
  const me = useMe()
  if (me.isPending) return <Loading />
  if (me.isError) return <ErrorNotice error={me.error} onRetry={() => me.refetch()} />
  if (!me.data.is_owner) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<RequireLogin><Layout /></RequireLogin>}>
        <Route index element={<Home />} />
        <Route path="stock" element={<StockList />} />
        <Route path="add" element={<OwnerOnly><AddStock /></OwnerOnly>} />
        <Route path="e/:code" element={<Entry />} />
        <Route path="e/:code/sell" element={<Sell />} />
        <Route path="e/:code/edit" element={<OwnerOnly><EditEntry /></OwnerOnly>} />
        <Route path="scan" element={<Suspense fallback={<Loading />}><Scan /></Suspense>} />
        <Route path="labels" element={<Labels />} />
        <Route path="stats" element={<OwnerOnly><Stats /></OwnerOnly>} />
        <Route path="export" element={<OwnerOnly><Export /></OwnerOnly>} />
        <Route path="reports" element={<OwnerOnly><Reports /></OwnerOnly>} />
        <Route path="reports/:date" element={<OwnerOnly><DailyReport /></OwnerOnly>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
