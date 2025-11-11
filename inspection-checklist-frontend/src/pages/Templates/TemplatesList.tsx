import { Link, useNavigate } from 'react-router-dom'

import { useDeleteTemplateMutation, useTemplatesQuery } from '@/api/hooks'
import { EmptyState } from '@/components/feedback/EmptyState'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { useToast } from '@/components/ui/Toast'

export const TemplatesListPage = () => {
  const navigate = useNavigate()
  const { data, isLoading } = useTemplatesQuery()
  const deleteMutation = useDeleteTemplateMutation()
  const { push } = useToast()

  const handleDelete = async (templateId: string) => {
    if (!window.confirm('Delete this template?')) return
    try {
      await deleteMutation.mutateAsync(templateId)
      push({ title: 'Template deleted', variant: 'success' })
    } catch (error) {
      push({ title: 'Failed to delete template', description: String((error as Error).message), variant: 'error' })
    }
  }

  if (isLoading) {
    return <Skeleton className="h-40 w-full" />
  }

  return (
    <Card
      title="Templates"
      actions={
        <Button onClick={() => navigate('/templates/new')}>
          New template
        </Button>
      }
    >
      {data && data.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">Sections</th>
                <th className="px-4 py-2">Items</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {data.map((template) => {
                const sectionCount = template.sections?.length ?? 0
                const itemCount =
                  template.sections?.reduce((total, section) => total + (section.items?.length ?? 0), 0) ?? 0
                return (
                  <tr key={template.id} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-medium text-slate-900">
                      <Link className="text-brand-600 hover:underline" to={`/templates/${template.id}`}>
                        {template.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{sectionCount}</td>
                    <td className="px-4 py-3 text-slate-600">{itemCount}</td>
                    <td className="px-4 py-3 text-right">
                      <Button variant="ghost" onClick={() => handleDelete(template.id)}>
                        Delete
                      </Button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          title="No templates"
          description="Create your first inspection template."
          action={<Button onClick={() => navigate('/templates/new')}>Create template</Button>}
        />
      )}
    </Card>
  )
}
