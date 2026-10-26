import { Navigate, Outlet, createBrowserRouter, useLocation } from 'react-router'
import { useAuth } from './auth/AuthContext'
import Logo from './components/Logo'
import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'

import Landing from './pages/Landing'
import Login from './pages/Login'
import Signup from './pages/Signup'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import Dashboard from './pages/Dashboard'
import Products from './pages/Products'
import AddProduct from './pages/AddProduct'
import Invoices from './pages/Invoices'
import InvoiceUpload from './pages/InvoiceUpload'
import InvoiceReview from './pages/InvoiceReview'
import Sales from './pages/Sales'
import VoiceSales from './pages/VoiceSales'
import SalesConfirmation from './pages/SalesConfirmation'
import History from './pages/History'
import Settings from './pages/Settings'

/** Blocks everything under it until we know who the user is. */
function ProtectedRoute() {
  const { user, checking } = useAuth()
  const location = useLocation()
  if (checking) {
    return <div className="route-loader"><Logo compact /><p>Loading StockLens…</p></div>
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  }
  return <Outlet />
}

function AppLayout() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main>
        <Navbar />
        <div className="content"><Outlet /></div>
      </main>
    </div>
  )
}

export const router = createBrowserRouter([
  { path: '/', Component: Landing },
  { path: '/login', Component: Login },
  { path: '/signup', Component: Signup },
  { path: '/forgot-password', Component: ForgotPassword },
  { path: '/reset-password', Component: ResetPassword },
  {
    Component: ProtectedRoute,
    children: [
      {
        path: '/app',
        Component: AppLayout,
        children: [
          { index: true, element: <Navigate to="dashboard" replace /> },
          { path: 'dashboard', Component: Dashboard },
          { path: 'products', Component: Products },
          { path: 'products/new', Component: AddProduct },
          { path: 'products/:id/edit', Component: AddProduct },
          { path: 'invoices', Component: Invoices },
          { path: 'invoices/upload', Component: InvoiceUpload },
          { path: 'invoices/review', Component: InvoiceReview },
          { path: 'sales', Component: Sales },
          { path: 'sales/voice', Component: VoiceSales },
          { path: 'sales/confirm', Component: SalesConfirmation },
          { path: 'history', Component: History },
          { path: 'settings', Component: Settings },
          { path: '*', element: <Navigate to="dashboard" replace /> },
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
])
