import { zodResolver } from '@hookform/resolvers/zod'
import { ClipboardCheck } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'

import { useCreateInspectionMutation, useTemplatesQuery } from '@/api/hooks'
import { FormField } from '@/components/forms/FormField'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Textarea } from '@/components/ui/Textarea'
import { useToast } from '@/components/ui/Toast'

const inspectionSchema = z.object({
  template_id: z.string().min(1, 'Choose a template'),
  location: z.string().min(2, 'Location is required'),
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
    defaultValues: { template_id: '', location: '', notes: '' },
  })

  const onSubmit = async (values: InspectionFormValues) => {
    try {
      const inspection = await createInspection.mutateAsync(values)
      push({ title: 'Inspection created', variant: 'success' })
      navigate(`/inspections/${inspection.id}/edit`)
    } catch (error) {
      push({ title: 'Unable to create inspection', description: String((error as Error).message), variant: 'error' })
    }
  }

  return (
    <Card title="Start inspection" subtitle="Choose template and location">
      <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
        <FormField label="Template" error={form.formState.errors.template_id?.message}>
          <Select {...form.register('template_id')}>
            <option value="">Select a template</option>
            {templates.data?.map((template) => (
              <option key={template.id} value={template.id}>
                {template.name}
              </option>
            ))}
          </Select>
        </FormField>
        <FormField label="Location" error={form.formState.errors.location?.message}>
          <Input {...form.register('location')} placeholder="Site or facility" />
        </FormField>
        <FormField label="Notes" error={form.formState.errors.notes?.message}>
          <Textarea rows={4} {...form.register('notes')} placeholder="Optional" />
        </FormField>
        <Button type="submit" disabled={templates.isLoading} loading={createInspection.isPending}>
          <ClipboardCheck className="mr-2 h-4 w-4" />
          Create inspection
        </Button>
      </form>
    </Card>
  )
}
