import { zodResolver } from '@hookform/resolvers/zod'
import { Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useFieldArray, useForm } from 'react-hook-form'
import { useNavigate, useParams } from 'react-router-dom'
import { z } from 'zod'

import {
  useCreateTemplateMutation,
  useItemMutations,
  useSectionMutations,
  useTemplateQuery,
  useUpdateTemplateMutation,
} from '@/api/hooks'
import type { components } from '@/api/gen/schema'
import { FormField } from '@/components/forms/FormField'
import { EmptyState } from '@/components/feedback/EmptyState'
import { LoadingState } from '@/components/feedback/LoadingState'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { useToast } from '@/components/ui/toastContext'

const itemSchema = z.object({
  prompt: z.string().min(2),
  is_required: z.boolean(),
  order_index: z.number().min(0),
})

const sectionSchema = z.object({
  title: z.string().min(2),
  order_index: z.number().min(0),
  items: z.array(itemSchema),
})

const templateSchema = z.object({
  name: z.string().min(2),
  description: z.string().optional(),
  sections: z.array(sectionSchema),
})

type TemplateFormValues = z.infer<typeof templateSchema>

type TemplateSection = components['schemas']['TemplateSectionRead']

export const TemplateEditorPage = () => {
  const { templateId } = useParams<{ templateId: string }>()
  const isNewTemplate = !templateId
  const navigate = useNavigate()
  const { push } = useToast()

  const { data: template, isLoading } = useTemplateQuery(templateId)
  const createTemplate = useCreateTemplateMutation()
  const updateTemplate = useUpdateTemplateMutation(templateId)
  const sectionMutations = useSectionMutations(templateId)
  const itemMutations = useItemMutations(templateId)

  const form = useForm<TemplateFormValues>({
    resolver: zodResolver(templateSchema),
    defaultValues: { name: '', description: '', sections: [] },
  })

  const sectionsArray = useFieldArray({ control: form.control, name: 'sections' })

  useEffect(() => {
    if (template && !isNewTemplate) {
      form.reset({
        name: template.name,
        description: template.description ?? '',
        sections:
          template.sections?.map((section, sectionIndex) => ({
            title: section.title,
            order_index: typeof section.order_index === 'number' ? section.order_index : sectionIndex,
            items:
              section.items?.map((item, itemIndex) => ({
                prompt: item.prompt,
                is_required: item.is_required,
                order_index: typeof item.order_index === 'number' ? item.order_index : itemIndex,
              })) ?? [],
          })) ?? [],
      })
    }
  }, [form, template, isNewTemplate])

  const [sectionDrafts, setSectionDrafts] = useState<Record<string, { title: string; order_index: number }>>({})
  const [itemDrafts, setItemDrafts] = useState<
    Record<string, { prompt: string; is_required: boolean; order_index: number }>
  >({})

  useEffect(() => {
    if (template?.sections && !isNewTemplate) {
      const drafts: Record<string, { title: string; order_index: number }> = {}
      const itemDefaults: Record<string, { prompt: string; is_required: boolean; order_index: number }> = {}
      template.sections.forEach((section, index) => {
        drafts[section.id] = {
          title: section.title,
          order_index: typeof section.order_index === 'number' ? section.order_index : index,
        }
        itemDefaults[section.id] = { prompt: '', is_required: true, order_index: (section.items?.length ?? 0) + 1 }
      })
      setSectionDrafts(drafts)
      setItemDrafts(itemDefaults)
    }
  }, [template, isNewTemplate])

  const handleSubmit = async (values: TemplateFormValues) => {
    try {
      if (isNewTemplate) {
        await createTemplate.mutateAsync(values)
        push({ title: 'Template created', variant: 'success' })
        form.reset({ name: '', description: '', sections: [] })
        navigate('/templates')
      } else if (templateId) {
        await updateTemplate.mutateAsync({ name: values.name, description: values.description })
        push({ title: 'Template updated', variant: 'success' })
      }
    } catch (error) {
      push({ title: 'Unable to save template', description: String((error as Error).message), variant: 'error' })
    }
  }

  const addSection = () => {
    sectionsArray.append({ title: 'New section', order_index: sectionsArray.fields.length, items: [] })
  }

  const addItemToSection = (sectionIndex: number) => {
    const path = `sections.${sectionIndex}.items` as const
    const items = form.getValues(path) ?? []
    form.setValue(path, [...items, { prompt: 'New item', is_required: true, order_index: items.length }])
  }

  const removeItem = (sectionIndex: number, itemIndex: number) => {
    const path = `sections.${sectionIndex}.items` as const
    const items = form.getValues(path) ?? []
    form.setValue(
      path,
      items.filter((_, index) => index !== itemIndex),
    )
  }

  const handleSectionDraftChange = (sectionId: string, field: 'title' | 'order_index', value: string) => {
    setSectionDrafts((current) => ({
      ...current,
      [sectionId]: { ...current[sectionId], [field]: field === 'order_index' ? Number(value) : value },
    }))
  }

  const handleSaveSection = async (section: TemplateSection) => {
    if (!templateId) return
    const draft = sectionDrafts[section.id]
    if (!draft) return
    try {
      await sectionMutations.updateSection.mutateAsync({
        sectionId: section.id,
        data: { title: draft.title, order_index: draft.order_index },
      })
      push({ title: 'Section updated', variant: 'success' })
    } catch (error) {
      push({ title: 'Unable to update section', description: String((error as Error).message), variant: 'error' })
    }
  }

  const handleDeleteSection = async (sectionId: string) => {
    if (!templateId) return
    if (!window.confirm('Delete this section?')) return
    try {
      await sectionMutations.deleteSection.mutateAsync(sectionId)
      push({ title: 'Section removed', variant: 'success' })
    } catch (error) {
      push({ title: 'Unable to delete section', description: String((error as Error).message), variant: 'error' })
    }
  }

  const handleCreateSection = async () => {
    if (!templateId) return
    const draft = { title: 'New section', order_index: (template?.sections?.length ?? 0) + 1, items: [] }
    try {
      await sectionMutations.createSection.mutateAsync(draft)
      push({ title: 'Section created', variant: 'success' })
    } catch (error) {
      push({ title: 'Unable to create section', description: String((error as Error).message), variant: 'error' })
    }
  }

  const handleCreateItem = async (section: TemplateSection) => {
    if (!templateId) return
    const draft = itemDrafts[section.id]
    if (!draft?.prompt) {
      push({ title: 'Item prompt required', variant: 'warning' })
      return
    }
    try {
      await itemMutations.createItem.mutateAsync({
        sectionId: section.id,
        payload: { prompt: draft.prompt, is_required: draft.is_required, order_index: draft.order_index },
      })
      push({ title: 'Item added', variant: 'success' })
      setItemDrafts((current) => ({ ...current, [section.id]: { prompt: '', is_required: true, order_index: draft.order_index + 1 } }))
    } catch (error) {
      push({ title: 'Unable to add item', description: String((error as Error).message), variant: 'error' })
    }
  }

  const handleDeleteItem = async (section: TemplateSection, itemId: string) => {
    if (!templateId) return
    try {
      await itemMutations.deleteItem.mutateAsync({ sectionId: section.id, itemId })
      push({ title: 'Item removed', variant: 'success' })
    } catch (error) {
      push({ title: 'Unable to remove item', description: String((error as Error).message), variant: 'error' })
    }
  }

  const builder = !isNewTemplate ? null : (
    <div className="space-y-4">
      {sectionsArray.fields.length === 0 && (
        <EmptyState
          title="No sections yet"
          description="Add sections and items before saving the template."
          action={
            <Button onClick={addSection} type="button">
              <Plus className="h-4 w-4" /> Add section
            </Button>
          }
        />
      )}
      {sectionsArray.fields.map((section, index) => (
        <Card
          key={section.id}
          title={`Section ${index + 1}`}
          actions={
            <Button variant="ghost" onClick={() => sectionsArray.remove(index)}>
              Remove
            </Button>
          }
        >
          <div className="grid gap-4 md:grid-cols-2">
            <FormField label="Title" error={form.formState.errors.sections?.[index]?.title?.message}>
              <Input {...form.register(`sections.${index}.title` as const)} />
            </FormField>
            <FormField label="Order" error={form.formState.errors.sections?.[index]?.order_index?.message}>
              <Input
                type="number"
                min={0}
                {...form.register(`sections.${index}.order_index` as const, { valueAsNumber: true })}
              />
            </FormField>
          </div>
          <div className="mt-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-slate-700">Items</p>
              <Button type="button" variant="secondary" onClick={() => addItemToSection(index)}>
                <Plus className="h-4 w-4" />
                Add item
              </Button>
            </div>
            {(form.watch(`sections.${index}.items`) ?? []).map((_, itemIndex) => (
              <div key={itemIndex} className="grid gap-3 rounded-lg border border-slate-100 p-3 md:grid-cols-3">
                <FormField
                  label="Prompt"
                  className="md:col-span-2"
                  error={form.formState.errors.sections?.[index]?.items?.[itemIndex]?.prompt?.message}
                >
                  <Input {...form.register(`sections.${index}.items.${itemIndex}.prompt` as const)} />
                </FormField>
                <div className="flex items-end gap-2">
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" {...form.register(`sections.${index}.items.${itemIndex}.is_required` as const)} />
                    Required
                  </label>
                  <Button type="button" variant="ghost" onClick={() => removeItem(index, itemIndex)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      ))}
      {sectionsArray.fields.length > 0 && (
        <Button type="button" variant="secondary" onClick={addSection}>
          Add another section
        </Button>
      )}
    </div>
  )

  if (!isNewTemplate && isLoading) {
    return <LoadingState label="Loading template..." />
  }

  return (
    <div className="space-y-6">
      <Card
        title={isNewTemplate ? 'Create template' : `Edit template • ${template?.name ?? ''}`}
        subtitle="Define the high-level information"
      >
        <form className="grid gap-4 md:grid-cols-2" onSubmit={form.handleSubmit(handleSubmit)}>
          <FormField label="Name" error={form.formState.errors.name?.message}>
            <Input {...form.register('name')} placeholder="Pre-trip inspection" />
          </FormField>
          <FormField label="Description" error={form.formState.errors.description?.message}>
            <Textarea rows={3} {...form.register('description')} placeholder="Optional" />
          </FormField>
          <div className="md:col-span-2 flex justify-end">
            <Button type="submit" loading={createTemplate.isPending || updateTemplate?.isPending}>Save template</Button>
          </div>
        </form>
      </Card>

      {isNewTemplate ? (
        builder
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900">Sections</h2>
            <Button variant="secondary" onClick={handleCreateSection}>
              <Plus className="h-4 w-4" /> New section
            </Button>
          </div>
          {template?.sections?.map((section) => (
            <Card key={section.id} title={section.title} subtitle={`${section.items?.length ?? 0} items`}>
              <div className="grid gap-4 md:grid-cols-3">
                <FormField label="Title">
                  <Input
                    value={sectionDrafts[section.id]?.title ?? ''}
                    onChange={(event) => handleSectionDraftChange(section.id, 'title', event.target.value)}
                  />
                </FormField>
                <FormField label="Order">
                  <Input
                    type="number"
                    min={0}
                    value={sectionDrafts[section.id]?.order_index ?? 0}
                    onChange={(event) => handleSectionDraftChange(section.id, 'order_index', event.target.value)}
                  />
                </FormField>
                <div className="flex items-center gap-2">
                  <Button type="button" variant="secondary" onClick={() => handleSaveSection(section)}>
                    Save
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => handleDeleteSection(section.id)}>
                    Delete
                  </Button>
                </div>
              </div>
              <div className="mt-4 space-y-2">
                {section.items?.map((item) => (
                  <div key={item.id} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2 text-sm">
                    <div>
                      <p className="font-medium text-slate-900">{item.prompt}</p>
                      <p className="text-xs text-slate-500">{item.is_required ? 'Required' : 'Optional'}</p>
                    </div>
                    <Button variant="ghost" onClick={() => handleDeleteItem(section, item.id)}>
                      Remove
                    </Button>
                  </div>
                ))}
                <div className="rounded-lg border border-dashed border-slate-200 p-3">
                  <p className="text-sm font-semibold text-slate-700">Add item</p>
                  <div className="mt-2 grid gap-2 md:grid-cols-3">
                    <Input
                      placeholder="Prompt"
                      value={itemDrafts[section.id]?.prompt ?? ''}
                      onChange={(event) =>
                        setItemDrafts((current) => ({
                          ...current,
                          [section.id]: { ...current[section.id], prompt: event.target.value },
                        }))
                      }
                    />
                    <label className="flex items-center gap-2 text-sm text-slate-600">
                      <input
                        type="checkbox"
                        checked={itemDrafts[section.id]?.is_required ?? true}
                        onChange={(event) =>
                          setItemDrafts((current) => ({
                            ...current,
                            [section.id]: { ...current[section.id], is_required: event.target.checked },
                          }))
                        }
                      />
                      Required
                    </label>
                    <Input
                      type="number"
                      min={0}
                      value={itemDrafts[section.id]?.order_index ?? 0}
                      onChange={(event) =>
                        setItemDrafts((current) => ({
                          ...current,
                          [section.id]: { ...current[section.id], order_index: Number(event.target.value) },
                        }))
                      }
                    />
                  </div>
                  <div className="mt-3 flex justify-end">
                    <Button type="button" variant="secondary" onClick={() => handleCreateItem(section)}>
                      Add item
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
