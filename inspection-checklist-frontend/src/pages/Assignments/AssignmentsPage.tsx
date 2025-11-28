import { useMemo, useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import type { Resolver, SubmitHandler } from 'react-hook-form'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'
import dayjs from 'dayjs'

import {
  useAssignmentsQuery,
  useCreateAssignmentMutation,
  useStartAssignmentInspectionMutation,
  useTemplatesQuery,
  useUsersQuery,
} from '@/api/hooks'
import { getErrorMessage } from '@/api/client'
import type { components } from '@/api/gen/schema'
import { useAuth } from '@/auth/useAuth'
import { FormField } from '@/components/forms/FormField'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { useToast } from '@/components/ui/toastContext'
import { Badge } from '@/components/ui/Badge'

const frequencyOptions = ['daily', 'weekly', 'monthly'] as const

const assignmentSchema = z.object({
  templateId: z.string().min(1, 'Choose a template'),
  assigned_to_id: z.string().min(1, 'Assign an inspector'),
  location: z.string().optional(),
  frequency: z.enum(frequencyOptions),
  start_due_at: z
    .string()
    .min(1, 'Start due date is required')
    .refine((value) => !Number.isNaN(new Date(value).getTime()), 'Enter a valid date and time'),
  end_date: z.string().transform((value) => {
    const trimmed = value?.trim()
    return trimmed || undefined
  }),
})

type AssignmentFormValues = z.input<typeof assignmentSchema>
type AssignmentRow = components['schemas']['AssignmentRead']

const getTemplateName = (assignment: AssignmentRow) => assignment.template_name ?? 'Inspection'

export const AssignmentsPage = () => {
  const assignments = useAssignmentsQuery()
  const assignmentRows = (assignments.data ?? []) as AssignmentRow[]
  const navigate = useNavigate()
  const { push } = useToast()
  const { user } = useAuth()
  const role = user?.role ?? 'inspector'
  const canManageAssignments = role === 'admin'
  const canStartInspection = role === 'inspector'
  const startAssignment = useStartAssignmentInspectionMutation()
  const [startingAssignmentId, setStartingAssignmentId] = useState<number | null>(null)

  const handleStartInspection = async (assignmentId: number) => {
    setStartingAssignmentId(assignmentId)
    try {
      const inspection = await startAssignment.mutateAsync(assignmentId)
      push({ title: 'Inspection draft created', variant: 'success' })
      assignments.refetch()
      navigate(`/inspections/${inspection.id}/edit`)
    } catch (error) {
      push({
        title: 'Unable to start inspection',
        description: getErrorMessage(error),
        variant: 'error',
      })
    } finally {
      setStartingAssignmentId(null)
    }
  }

  return (
    <div className="space-y-6">
      {canManageAssignments && <AssignmentCreateCard />}

      <Card
        title="Recurring assignments"
        subtitle="Track who owns each scheduled inspection, its cadence, and upcoming due dates."
        actions={
          <Button
            type="button"
            variant="secondary"
            onClick={() => assignments.refetch()}
            loading={assignments.isFetching}
          >
            Refresh
          </Button>
        }
      >
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-3 py-2">Template</th>
            <th className="px-3 py-2">Assignee</th>
            <th className="px-3 py-2">Location</th>
            <th className="px-3 py-2">Schedule</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Tags &amp; notes</th>
            {canStartInspection && <th className="px-3 py-2 text-right">Actions</th>}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {assignmentRows.length === 0 && (
            <tr>
              <td colSpan={canStartInspection ? 7 : 6} className="px-3 py-6 text-center text-slate-500">
                No assignments scheduled yet.
              </td>
            </tr>
          )}
          {assignmentRows.map((assignment) => {
            const assigneeName = assignment.assignee.full_name || assignment.assignee.email
            const statusLabel = assignment.active ? 'Active' : 'Completed'
            const statusColor = assignment.active ? 'text-emerald-600' : 'text-slate-500'
            const weeklyStatusLabel = assignment.current_week_completed ? 'Completed this week' : 'Pending this week'
            const weeklyStatusColor = assignment.current_week_completed ? 'text-emerald-600' : 'text-amber-600'
            const templateLabel = getTemplateName(assignment)
            const frequencyLabel = assignment.frequency
              ? `${assignment.frequency.slice(0, 1).toUpperCase()}${assignment.frequency.slice(1)}`
              : 'Weekly'
            const startDueLabel = assignment.start_due_at
              ? dayjs(assignment.start_due_at).format('MMM D, YYYY h:mm A')
              : 'Not scheduled'
            const endLabel = assignment.end_date ? dayjs(assignment.end_date).format('MMM D, YYYY') : null
            const isRejection = (assignment.tag || '').toLowerCase() === 'denied'
            const priorityLabel = assignment.priority === 'urgent' ? 'Urgent' : 'Normal'

            return (
              <tr key={assignment.id}>
                <td className="px-3 py-3 font-medium text-slate-900">{templateLabel}</td>
                <td className="px-3 py-3 text-slate-700">{assigneeName}</td>
                    <td className="px-3 py-3 text-slate-700">{assignment.location || '—'}</td>
                    <td className="px-3 py-3 text-slate-700">
                      <div>{frequencyLabel}</div>
                      <div className="text-xs text-slate-500">
                        Starts {startDueLabel}
                        {endLabel ? ` · Ends ${endLabel}` : ' · No end date'}
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      <div className={`font-medium ${statusColor}`}>{statusLabel}</div>
                  <div className={`text-xs font-semibold ${weeklyStatusColor}`}>{weeklyStatusLabel}</div>
                </td>
                <td className="px-3 py-3 text-slate-700">
                  <div className="flex flex-wrap items-center gap-2">
                    {isRejection && <Badge variant="danger">Denied</Badge>}
                    <Badge variant={assignment.priority === 'urgent' ? 'warning' : 'neutral'}>{priorityLabel}</Badge>
                  </div>
                  {assignment.notes && (
                    <p className="mt-1 text-xs text-slate-500 whitespace-pre-line">{assignment.notes}</p>
                  )}
                </td>
                {canStartInspection && (
                  <td className="px-3 py-3 text-right">
                    <Button
                      type="button"
                      variant="secondary"
                          loading={startAssignment.isPending && startingAssignmentId === assignment.id}
                          disabled={startAssignment.isPending && startingAssignmentId !== assignment.id}
                          onClick={() => handleStartInspection(assignment.id)}
                        >
                          Start
                        </Button>
                      </td>
                    )}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}

const AssignmentCreateCard = () => {
  const { push } = useToast()
  const templates = useTemplatesQuery()
  const users = useUsersQuery('inspector')
  const createAssignment = useCreateAssignmentMutation()

  const form = useForm<AssignmentFormValues>({
    resolver: zodResolver(assignmentSchema) as Resolver<AssignmentFormValues>,
    defaultValues: {
      templateId: '',
      assigned_to_id: '',
      frequency: 'weekly',
      start_due_at: '',
      end_date: '',
      location: '',
    },
  })

  const isSubmitting = createAssignment.isPending
  const isLoading = templates.isLoading || users.isLoading

  const templateOptions = useMemo(() => templates.data ?? [], [templates.data])
  const userOptions = useMemo(() => users.data ?? [], [users.data])
  const templateField = form.register('templateId')

  const onSubmit: SubmitHandler<AssignmentFormValues> = async (values) => {
    const startDue = new Date(values.start_due_at)
    if (Number.isNaN(startDue.getTime())) {
      push({
        title: 'Invalid start date',
        description: 'Enter a valid start due date and time.',
        variant: 'error',
      })
      return
    }
    try {
      const isoStart = dayjs(values.start_due_at).toISOString()
      await createAssignment.mutateAsync({
        template_id: values.templateId,
        assigned_to_id: values.assigned_to_id,
        location: values.location || undefined,
        frequency: values.frequency,
        active: true,
        start_due_at: isoStart,
        end_date: values.end_date || undefined,
        priority: 'normal',
      })
      push({ title: 'Assignment scheduled', variant: 'success' })
      form.reset()
    } catch (error) {
      push({
        title: 'Unable to schedule assignment',
        description: getErrorMessage(error),
        variant: 'error',
      })
    }
  }

  return (
    <Card
      title="Create recurring assignment"
      subtitle="Pick a template, choose the cadence, set the first due date, and assign the inspector who will run it."
    >
      <form className="grid gap-4 md:grid-cols-2" onSubmit={form.handleSubmit(onSubmit)}>
        <FormField label="Template" error={form.formState.errors.templateId?.message}>
          <Select {...templateField} disabled={isLoading || isSubmitting}>
            <option value="">Select a template</option>
            {templateOptions.map((template) => (
              <option key={template.id} value={template.id}>
                {template.name}
              </option>
            ))}
          </Select>
        </FormField>

        <FormField label="Assignee" error={form.formState.errors.assigned_to_id?.message}>
          <Select {...form.register('assigned_to_id')} disabled={isLoading || isSubmitting}>
            <option value="">Select an inspector</option>
            {userOptions.map((user) => (
              <option key={user.id} value={user.id}>
                {user.full_name || user.email}
              </option>
            ))}
          </Select>
        </FormField>

        <FormField label="Frequency" error={form.formState.errors.frequency?.message}>
          <Select {...form.register('frequency')} disabled={isSubmitting}>
            {frequencyOptions.map((option) => (
              <option key={option} value={option}>
                {option.slice(0, 1).toUpperCase()}
                {option.slice(1)}
              </option>
            ))}
          </Select>
        </FormField>

        <FormField
          label="Start due date"
          description="Calendar date and time for the first scheduled inspection."
          error={form.formState.errors.start_due_at?.message}
        >
          <Input type="datetime-local" disabled={isSubmitting} {...form.register('start_due_at')} />
        </FormField>

        <FormField
          label="End date"
          description="Optional last day for this assignment. Leave blank to keep it active."
          error={form.formState.errors.end_date?.message}
        >
          <Input type="date" disabled={isSubmitting} {...form.register('end_date')} />
        </FormField>

        <FormField label="Location" error={form.formState.errors.location?.message}>
          <Input placeholder="Optional description" disabled={isSubmitting} {...form.register('location')} />
        </FormField>

        <div className="md:col-span-2">
          <Button type="submit" loading={isSubmitting} disabled={isLoading}>
            Schedule inspection
          </Button>
        </div>
      </form>
    </Card>
  )
}
