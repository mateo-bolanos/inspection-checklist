import { createBrowserRouter, Navigate } from 'react-router-dom'

import { AppLayout } from '@/components/layout/AppLayout'
import { ProtectedRoute } from '@/routes/protected'

import { LoginPage } from '@/pages/Login'
import { OverviewPage } from '@/pages/Dashboard/Overview'
import { DashboardActionsPage } from '@/pages/Dashboard/Actions'
import { DashboardItemsPage } from '@/pages/Dashboard/Items'
import { TemplatesListPage } from '@/pages/Templates/TemplatesList'
import { TemplateEditorPage } from '@/pages/Templates/TemplateEditor'
import { NewInspectionPage } from '@/pages/Inspections/NewInspection'
import { InspectionEditPage } from '@/pages/Inspections/InspectionEdit'
import { InspectionViewPage } from '@/pages/Inspections/InspectionView'
import { InspectionsListPage } from '@/pages/Inspections/InspectionsList'
import { ActionsListPage } from '@/pages/Actions/ActionsList'
import { ReviewQueuePage } from '@/pages/Reviews/ReviewQueue'
import { FileUploadPage } from '@/pages/Files/Upload'
import { useAuth } from '@/auth/useAuth'

const HomeRedirect = () => {
  const { defaultRoute } = useAuth()
  return <Navigate to={defaultRoute} replace />
}

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <HomeRedirect /> },
      {
        path: 'dash/overview',
        element: (
          <ProtectedRoute roles={['admin', 'reviewer']}>
            <OverviewPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'dash/actions',
        element: (
          <ProtectedRoute roles={['admin', 'reviewer']}>
            <DashboardActionsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'dash/items',
        element: (
          <ProtectedRoute roles={['admin', 'reviewer']}>
            <DashboardItemsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'templates',
        element: (
          <ProtectedRoute roles={['admin']}>
            <TemplatesListPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'templates/:templateId',
        element: (
          <ProtectedRoute roles={['admin']}>
            <TemplateEditorPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'templates/new',
        element: (
          <ProtectedRoute roles={['admin']}>
            <TemplateEditorPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'inspections/new',
        element: (
          <ProtectedRoute roles={['admin', 'inspector']}>
            <NewInspectionPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'inspections',
        element: (
          <ProtectedRoute roles={['admin', 'inspector', 'reviewer']}>
            <InspectionsListPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'inspections/:inspectionId/edit',
        element: (
          <ProtectedRoute roles={['admin', 'inspector']}>
            <InspectionEditPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'inspections/:inspectionId',
        element: (
          <ProtectedRoute roles={['admin', 'inspector', 'reviewer']}>
            <InspectionViewPage />
          </ProtectedRoute>
        ),
      },
      { path: 'actions', element: <ActionsListPage /> },
      {
        path: 'reviews',
        element: (
          <ProtectedRoute roles={['admin', 'reviewer']}>
            <ReviewQueuePage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'files/upload',
        element: (
          <ProtectedRoute roles={['admin', 'inspector']}>
            <FileUploadPage />
          </ProtectedRoute>
        ),
      },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
])
