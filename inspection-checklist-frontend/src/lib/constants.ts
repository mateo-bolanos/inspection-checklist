export const ROLE_HOME_ROUTE: Record<string, string> = {
  admin: '/dash/overview',
  reviewer: '/reviews',
  inspector: '/inspections/new',
}

export const INSPECTION_RESULTS = ['pass', 'fail', 'na'] as const

export const INSPECTION_STATUSES = ['draft', 'submitted', 'approved', 'rejected'] as const

export const ACTION_SEVERITIES = ['low', 'medium', 'high'] as const

export const ACTION_STATUSES = ['open', 'closed'] as const
