import { zodResolver } from '@hookform/resolvers/zod'
import { ClipboardCheck } from 'lucide-react'
import { useMemo } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'

import { useCreateInspectionMutation, useTemplatesQuery } from '@/api/hooks'
import { FormField } from '@/components/forms/FormField'
import { LocationSelect } from '@/components/forms/LocationSelect'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Select } from '@/components/ui/Select'
import { Textarea } from '@/components/ui/Textarea'
import { useToast } from '@/components/ui/toastContext'

const inspectionSchema = z.object({
  template_id: z.string().min(1, 'Choose a template'),
  location_id: z.string().min(1, 'Location is required'),
  notes: z.string().optional(),
})

type InspectionFormValues = z.infer<typeof inspectionSchema>

export const NewInspectionPage = () => {
  const templates = useTemplatesQuery()
  const createInspection = useCreateInspectionMutation()
  const navigate = useNavigate()
  const { push } = useToast()

  const form = useForm<InspectionFormValues>({
    resolver: zodResolver(inspectionSchema),
    defaultValues: { template_id: '', location_id: '', notes: '' },
  })
  const locationValue = form.watch('location_id')
  const templateOptions = useMemo(() => templates.data ?? [], [templates.data])
  const templateField = form.register('template_id')
  const isLoading = templates.isLoading

  const onSubmit = async (values: InspectionFormValues) => {
    try {
      const inspection = await createInspection.mutateAsync({
        ...values,
        location_id: Number(values.location_id),
      })
      push({ title: 'Inspection created', variant: 'success' })
      navigate(`/inspections/${inspection.id}/edit`)
    } catch (error) {
      push({ title: 'Unable to create inspection', description: String((error as Error).message), variant: 'error' })
    }
  }

  return (
    <Card title="Start inspection" subtitle="Creates an independent inspection not tied to any assignment.">
      <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
        <FormField label="Template" error={form.formState.errors.template_id?.message}>
          <Select
            {...templateField}
            disabled={isLoading || createInspection.isPending}
            onChange={(event) => {
              templateField.onChange(event)
            }}
          >
            <option value="">Select a template</option>
            {templateOptions.map((template) => (
              <option key={template.id} value={template.id}>
                {template.name}
              </option>
            ))}
          </Select>
        </FormField>
        <FormField label="Location" error={form.formState.errors.location_id?.message}>
          <LocationSelect
            value={locationValue}
            onChange={(nextValue) => form.setValue('location_id', nextValue, { shouldValidate: true })}
            disabled={isLoading || createInspection.isPending}
          />
        </FormField>
        <FormField label="Notes" error={form.formState.errors.notes?.message}>
          <Textarea rows={4} {...form.register('notes')} placeholder="Optional" />
        </FormField>
        <Button type="submit" disabled={isLoading} loading={createInspection.isPending}>
          <ClipboardCheck className="mr-2 h-4 w-4" />
          Create inspection
        </Button>
      </form>
    </Card>
  )
}
