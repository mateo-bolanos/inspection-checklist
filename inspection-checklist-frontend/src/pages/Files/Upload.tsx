import { useState } from 'react'

import { useUploadMediaMutation } from '@/api/hooks'
import { Card } from '@/components/ui/Card'
import { FormField } from '@/components/forms/FormField'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { useToast } from '@/components/ui/Toast'

export const FileUploadPage = () => {
  const [responseId, setResponseId] = useState('')
  const [actionId, setActionId] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const upload = useUploadMediaMutation()
  const { push } = useToast()

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!file) {
      push({ title: 'Select a file first', variant: 'warning' })
      return
    }
    if (!responseId && !actionId) {
      push({ title: 'Provide a response or action ID', variant: 'warning' })
      return
    }
    try {
      await upload.mutateAsync({ file, responseId: responseId || undefined, actionId: actionId || undefined })
      push({ title: 'File uploaded', variant: 'success' })
      setFile(null)
      setResponseId('')
      setActionId('')
    } catch (error) {
      push({ title: 'Upload failed', description: String((error as Error).message), variant: 'error' })
    }
  }

  return (
    <Card title="Upload evidence" subtitle="Attach files to responses or actions">
      <form className="space-y-4" onSubmit={handleSubmit}>
        <FormField label="Response ID" description="Provide either a response ID or an action ID">
          <Input value={responseId} onChange={(event) => setResponseId(event.target.value)} />
        </FormField>
        <FormField label="Action ID">
          <Input value={actionId} onChange={(event) => setActionId(event.target.value)} />
        </FormField>
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
