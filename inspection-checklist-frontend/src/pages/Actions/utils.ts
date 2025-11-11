import type { components } from '@/api/gen/schema'

type ActionRecord = components['schemas']['CorrectiveActionRead']

export const getActionDisplayStatus = (status: ActionRecord['status']) => (status === 'in_progress' ? 'open' : status)
