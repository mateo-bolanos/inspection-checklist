import { useMemo, useState } from 'react'

import {
  useActionsQuery,
  useInspectionQuery,
  useInspectionsQuery,
  useTemplateQuery,
  useTemplatesQuery,
  useUploadMediaMutation,
} from '@/api/hooks'
import { FormField } from '@/components/forms/FormField'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Select } from '@/components/ui/Select'
import { useToast } from '@/components/ui/Toast'
import { formatInspectionName } from '@/lib/formatters'

type TargetType = 'response' | 'action'

export const FileUploadPage = () => {
  const [targetType, setTargetType] = useState<TargetType>('response')
  const [selectedInspectionId, setSelectedInspectionId] = useState('')
  const [selectedResponseId, setSelectedResponseId] = useState('')
  const [selectedActionId, setSelectedActionId] = useState('')
  const [file, setFile] = useState<File | null>(null)

  const inspectionsQuery = useInspectionsQuery()
  const inspectionQuery = useInspectionQuery(selectedInspectionId || undefined)
  const templatesQuery = useTemplatesQuery()
  const templateQuery = useTemplateQuery(inspectionQuery.data?.template_id)
  const actionsQuery = useActionsQuery()
  const upload = useUploadMediaMutation()
  const { push } = useToast()

  const templateNameMap = useMemo(() => {
    const map = new Map<string, string>()
    templatesQuery.data?.forEach((template) => map.set(template.id, template.name))
    return map
  }, [templatesQuery.data])

  const inspectionOptions = useMemo(() => {
    return (inspectionsQuery.data ?? []).map((inspection) => ({
      value: inspection.id,
      label: formatInspectionName(templateNameMap.get(inspection.template_id), inspection.started_at, inspection.id),
    }))
  }, [inspectionsQuery.data, templateNameMap])

  const templateItemPromptMap = useMemo(() => {
    const map = new Map<string, string>()
    templateQuery.data?.sections?.forEach((section) => {
      section.items?.forEach((item) => map.set(item.id, item.prompt))
    })
    return map
  }, [templateQuery.data])

  const responseOptions = useMemo(() => {
    return (inspectionQuery.data?.responses ?? []).map((response) => ({
      value: response.id,
      label: templateItemPromptMap.get(response.template_item_id) ?? response.template_item_id,
    }))
  }, [inspectionQuery.data?.responses, templateItemPromptMap])

  const actionOptions = useMemo(() => {
    return (actionsQuery.data ?? []).map((action) => ({
      value: action.id.toString(),
      label: `Action #${action.id} • ${action.title} (${action.status.replace('_', ' ')})`,
    }))
  }, [actionsQuery.data])

  const isResponseTarget = targetType === 'response'

  const handleTargetChange = (value: TargetType) => {
    setTargetType(value)
    setSelectedInspectionId('')
    setSelectedResponseId('')
    setSelectedActionId('')
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!file) {
      push({ title: 'Select a file first', variant: 'warning' })
      return
    }
    if (isResponseTarget && !selectedResponseId) {
      push({ title: 'Choose a checklist response', variant: 'warning' })
      return
    }
    if (!isResponseTarget && !selectedActionId) {
      push({ title: 'Choose a corrective action', variant: 'warning' })
      return
    }
    try {
      await upload.mutateAsync({
        file,
        responseId: isResponseTarget ? selectedResponseId : undefined,
        actionId: !isResponseTarget ? Number(selectedActionId) : undefined,
      })
      push({ title: 'File uploaded', variant: 'success' })
      setFile(null)
      setSelectedResponseId('')
      setSelectedActionId('')
    } catch (error) {
      push({ title: 'Upload failed', description: String((error as Error).message), variant: 'error' })
    }
  }

  return (
    <Card title="Upload evidence" subtitle="Attach files to checklist responses or corrective actions">
      <form className="space-y-4" onSubmit={handleSubmit}>
        <FormField label="Attach to">
          <Select value={targetType} onChange={(event) => handleTargetChange(event.target.value as TargetType)}>
            <option value="response">Checklist response</option>
            <option value="action">Corrective action</option>
          </Select>
        </FormField>

        {isResponseTarget ? (
          <>
            <FormField label="Inspection">
              <Select
                value={selectedInspectionId}
                onChange={(event) => {
                  setSelectedInspectionId(event.target.value)
                  setSelectedResponseId('')
                }}
              >
                <option value="">Select an inspection</option>
                {inspectionOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </FormField>
            <FormField
              label="Checklist item"
              description={
                selectedInspectionId && responseOptions.length === 0
                  ? 'Save a response for this inspection before uploading evidence.'
                  : undefined
              }
            >
              <Select
                value={selectedResponseId}
                onChange={(event) => setSelectedResponseId(event.target.value)}
                disabled={!selectedInspectionId || responseOptions.length === 0}
              >
                <option value="">Select a checklist item response</option>
                {responseOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </FormField>
          </>
        ) : (
          <FormField
            label="Corrective action"
            description={
              actionOptions.length === 0 ? 'Create a corrective action first from the inspection details page.' : undefined
            }
          >
            <Select
              value={selectedActionId}
              onChange={(event) => setSelectedActionId(event.target.value)}
              disabled={actionOptions.length === 0}
            >
              <option value="">Select a corrective action</option>
              {actionOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </FormField>
        )}

        <FormField label="File">
          <input
            type="file"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            accept="image/*"
            className="text-sm"
          />
        </FormField>

        <Button type="submit" disabled={upload.isPending}>
          Upload file
        </Button>
      </form>
    </Card>
  )
}
