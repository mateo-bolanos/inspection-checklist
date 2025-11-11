import { useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from './client'
import type { components, paths } from './gen/schema'

export const queryKeys = {
  templates: ['templates'] as const,
  template: (templateId: string | undefined) => ['templates', templateId] as const,
  inspections: ['inspections'] as const,
  inspection: (inspectionId: string | number | undefined) => ['inspections', inspectionId] as const,
  inspectionResponses: (inspectionId: string | number | undefined) => ['inspections', inspectionId, 'responses'] as const,
  actions: ['actions'] as const,
  dashboard: {
    overview: ['dash', 'overview'] as const,
    actions: ['dash', 'actions'] as const,
    items: ['dash', 'items'] as const,
  },
  files: ['files'] as const,
  actionFiles: (actionId: number | undefined) => ['files', 'action', actionId] as const,
}

type TemplateListResponse = paths['/templates/']['get']['responses']['200']['content']['application/json']
type TemplateRead = components['schemas']['ChecklistTemplateRead']
type TemplateSectionRead = components['schemas']['TemplateSectionRead']
type TemplateItemRead = components['schemas']['TemplateItemRead']
type TemplateCreateInput = paths['/templates/']['post']['requestBody']['content']['application/json']
type TemplateUpdateInput = paths['/templates/{template_id}']['put']['requestBody']['content']['application/json']
type SectionCreateInput = paths['/templates/{template_id}/sections']['post']['requestBody']['content']['application/json']
type SectionUpdateInput = paths['/templates/{template_id}/sections/{section_id}']['put']['requestBody']['content']['application/json']
type ItemCreateInput = paths['/templates/{template_id}/sections/{section_id}/items']['post']['requestBody']['content']['application/json']
type ItemUpdateInput = paths['/templates/{template_id}/sections/{section_id}/items/{item_id}']['put']['requestBody']['content']['application/json']

type InspectionListResponse = paths['/inspections/']['get']['responses']['200']['content']['application/json']
type InspectionDetailResponse = paths['/inspections/{inspection_id}']['get']['responses']['200']['content']['application/json']
type InspectionCreateInput = paths['/inspections/']['post']['requestBody']['content']['application/json']
type InspectionUpdateInput = paths['/inspections/{inspection_id}']['put']['requestBody']['content']['application/json']
type InspectionSubmitResponse = paths['/inspections/{inspection_id}/submit']['post']['responses']['200']['content']['application/json']
type InspectionApproveResponse = paths['/inspections/{inspection_id}/approve']['post']['responses']['200']['content']['application/json']
type InspectionRejectResponse = paths['/inspections/{inspection_id}/reject']['post']['responses']['200']['content']['application/json']

type ResponseCreateInput = paths['/inspections/{inspection_id}/responses']['post']['requestBody']['content']['application/json']
type ResponseUpdateInput = paths['/inspections/{inspection_id}/responses/{response_id}']['put']['requestBody']['content']['application/json']
type InspectionResponseRead = components['schemas']['InspectionResponseRead']
type ResponseCreatePayload = ResponseCreateInput
type ResponseUpdatePayload = ResponseUpdateInput & { responseId: string }
type UpsertResponsePayload = ResponseCreatePayload | ResponseUpdatePayload

type CorrectiveActionListResponse = paths['/actions/']['get']['responses']['200']['content']['application/json']
type CorrectiveActionCreateInput = paths['/actions/']['post']['requestBody']['content']['application/json']
type CorrectiveActionUpdateInput = paths['/actions/{action_id}']['put']['requestBody']['content']['application/json']
type CorrectiveActionRead = components['schemas']['CorrectiveActionRead']

type OverviewMetrics = components['schemas']['OverviewMetrics']
type ActionMetrics = components['schemas']['ActionMetrics']
type ItemsMetrics = components['schemas']['ItemsMetrics']

type MediaListResponse = paths['/files/']['get']['responses']['200']['content']['application/json']
type MediaUploadResponse = paths['/files/']['post']['responses']['201']['content']['application/json']

type LoginResponse = components['schemas']['Token']

type LoginInput = {
  username: string
  password: string
}

export const useTemplatesQuery = () => {
  return useQuery({
    queryKey: queryKeys.templates,
    queryFn: async () => {
      const { data } = await api.get<TemplateListResponse>('/templates/')
      return data
    },
  })
}

export const useTemplateQuery = (templateId?: string) => {
  return useQuery({
    queryKey: queryKeys.template(templateId),
    enabled: Boolean(templateId),
    queryFn: async () => {
      const { data } = await api.get<TemplateRead>(`/templates/${templateId}`)
      return data
    },
  })
}

export const useCreateTemplateMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: TemplateCreateInput) => {
      const { data } = await api.post<TemplateRead>('/templates/', payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.templates })
    },
  })
}

export const useUpdateTemplateMutation = (templateId: string) => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: TemplateUpdateInput) => {
      const { data } = await api.put<TemplateRead>(`/templates/${templateId}`, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.templates })
      queryClient.invalidateQueries({ queryKey: queryKeys.template(templateId) })
    },
  })
}

export const useDeleteTemplateMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (templateId: string) => {
      await api.delete(`/templates/${templateId}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.templates }),
  })
}

export const useSectionMutations = (templateId: string) => {
  const queryClient = useQueryClient()
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.templates })
    queryClient.invalidateQueries({ queryKey: queryKeys.template(templateId) })
  }

  const createSection = useMutation({
    mutationFn: async (payload: SectionCreateInput) => {
      const { data } = await api.post<TemplateSectionRead>(`/templates/${templateId}/sections`, payload)
      return data
    },
    onSuccess: invalidate,
  })

  const updateSection = useMutation({
    mutationFn: async ({ sectionId, data }: { sectionId: string; data: SectionUpdateInput }) => {
      const response = await api.put<TemplateSectionRead>(
        `/templates/${templateId}/sections/${sectionId}`,
        data,
      )
      return response.data
    },
    onSuccess: invalidate,
  })

  const deleteSection = useMutation({
    mutationFn: async (sectionId: string) => {
      await api.delete(`/templates/${templateId}/sections/${sectionId}`)
    },
    onSuccess: invalidate,
  })

  return { createSection, updateSection, deleteSection }
}

export const useItemMutations = (templateId: string) => {
  const queryClient = useQueryClient()
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.templates })
    queryClient.invalidateQueries({ queryKey: queryKeys.template(templateId) })
  }

  const createItem = useMutation({
    mutationFn: async ({ sectionId, payload }: { sectionId: string; payload: ItemCreateInput }) => {
      const { data } = await api.post<TemplateItemRead>(
        `/templates/${templateId}/sections/${sectionId}/items`,
        payload,
      )
      return data
    },
    onSuccess: invalidate,
  })

  const updateItem = useMutation({
    mutationFn: async ({
      sectionId,
      itemId,
      data,
    }: { sectionId: string; itemId: string; data: ItemUpdateInput }) => {
      const response = await api.put<TemplateItemRead>(
        `/templates/${templateId}/sections/${sectionId}/items/${itemId}`,
        data,
      )
      return response.data
    },
    onSuccess: invalidate,
  })

  const deleteItem = useMutation({
    mutationFn: async ({ sectionId, itemId }: { sectionId: string; itemId: string }) => {
      await api.delete(`/templates/${templateId}/sections/${sectionId}/items/${itemId}`)
    },
    onSuccess: invalidate,
  })

  return { createItem, updateItem, deleteItem }
}

export const useInspectionsQuery = () => {
  return useQuery({
    queryKey: queryKeys.inspections,
    queryFn: async () => {
      const { data } = await api.get<InspectionListResponse>('/inspections/')
      return data
    },
  })
}

export const useInspectionQuery = (inspectionId?: string | number) => {
  const hasInspectionId = inspectionId !== undefined && inspectionId !== null && inspectionId !== ''
  return useQuery({
    queryKey: queryKeys.inspection(inspectionId),
    enabled: hasInspectionId,
    queryFn: async () => {
      if (!hasInspectionId) {
        throw new Error('Inspection ID is required')
      }
      const resolvedId = inspectionId as string | number
      const { data } = await api.get<InspectionDetailResponse>(`/inspections/${resolvedId}`)
      return data
    },
  })
}

export const useCreateInspectionMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: InspectionCreateInput) => {
      const { data } = await api.post('/inspections/', payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.inspections })
    },
  })
}

export const useUpdateInspectionMutation = (inspectionId: string | number) => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: InspectionUpdateInput) => {
      const { data } = await api.put(`/inspections/${inspectionId}`, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.inspection(inspectionId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.inspections })
    },
  })
}

export const useSubmitInspectionMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (inspectionId: string | number) => {
      const { data } = await api.post<InspectionSubmitResponse>(`/inspections/${inspectionId}/submit`)
      return data
    },
    onSuccess: (_, inspectionId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.inspection(inspectionId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.inspections })
    },
  })
}

export const useApproveInspectionMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (inspectionId: string | number) => {
      const { data } = await api.post<InspectionApproveResponse>(`/inspections/${inspectionId}/approve`)
      return data
    },
    onSuccess: (_, inspectionId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.inspection(inspectionId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.inspections })
    },
  })
}

export const useRejectInspectionMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (inspectionId: string | number) => {
      const { data } = await api.post<InspectionRejectResponse>(`/inspections/${inspectionId}/reject`)
      return data
    },
    onSuccess: (_, inspectionId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.inspection(inspectionId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.inspections })
    },
  })
}

export const useUpsertResponseMutation = (inspectionId: string | number) => {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: async (payload: UpsertResponsePayload) => {
      if ('responseId' in payload && payload.responseId) {
        const { responseId, ...body } = payload
        const { data } = await api.put<InspectionResponseRead>(
          `/inspections/${inspectionId}/responses/${responseId}`,
          body as ResponseUpdatePayload,
        )
        return data
      }
      const { data } = await api.post<InspectionResponseRead>(
        `/inspections/${inspectionId}/responses`,
        payload as ResponseCreatePayload,
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.inspection(inspectionId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.inspectionResponses(inspectionId) })
    },
  })

  return mutation
}

export const useActionsQuery = () => {
  return useQuery({
    queryKey: queryKeys.actions,
    queryFn: async () => {
      const { data } = await api.get<CorrectiveActionListResponse>('/actions/')
      return data
    },
  })
}

export const useCreateActionMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: CorrectiveActionCreateInput) => {
      const { data } = await api.post<CorrectiveActionRead>('/actions/', payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.actions })
      queryClient.invalidateQueries({ queryKey: queryKeys.inspections })
    },
  })
}

export const useUpdateActionMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ actionId, data }: { actionId: number; data: CorrectiveActionUpdateInput }) => {
      const response = await api.put<CorrectiveActionRead>(`/actions/${actionId}`, data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.actions })
      queryClient.invalidateQueries({ queryKey: queryKeys.inspections })
    },
  })
}

export const useDashboardOverviewQuery = () => {
  return useQuery({
    queryKey: queryKeys.dashboard.overview,
    queryFn: async () => {
      const { data } = await api.get<OverviewMetrics>('/dash/overview')
      return data
    },
  })
}

export const useDashboardActionsQuery = () => {
  return useQuery({
    queryKey: queryKeys.dashboard.actions,
    queryFn: async () => {
      const { data } = await api.get<ActionMetrics>('/dash/actions')
      return data
    },
  })
}

export const useDashboardItemsQuery = (limit = 5) => {
  return useQuery({
    queryKey: [...queryKeys.dashboard.items, limit] as const,
    queryFn: async () => {
      const { data } = await api.get<ItemsMetrics>('/dash/items', { params: { limit } })
      return data
    },
  })
}

export const useFilesQuery = () => {
  return useQuery({
    queryKey: queryKeys.files,
    queryFn: async () => {
      const { data } = await api.get<MediaListResponse>('/files/')
      return data
    },
  })
}

export const useActionFilesQuery = (actionId?: number) => {
  return useQuery({
    queryKey: queryKeys.actionFiles(actionId),
    enabled: typeof actionId === 'number',
    queryFn: async () => {
      const { data } = await api.get<MediaListResponse>('/files/', { params: { action_id: actionId } })
      return data
    },
  })
}

export const useUploadMediaMutation = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { file: File; responseId?: string; actionId?: number }) => {
      const formData = new FormData()
      formData.append('file', payload.file)
      const params: Record<string, string> = {}
      if (payload.responseId) params.response_id = payload.responseId
      if (payload.actionId !== undefined) params.action_id = String(payload.actionId)
      const { data } = await api.post<MediaUploadResponse>('/files/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        params,
      })
      return data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.files })
      queryClient.invalidateQueries({ queryKey: queryKeys.actions })
      if (variables.actionId !== undefined) {
        queryClient.invalidateQueries({ queryKey: queryKeys.actionFiles(variables.actionId) })
      }
    },
  })
}

export const useLoginMutation = () => {
  return useMutation({
    mutationFn: async ({ username, password }: LoginInput) => {
      const body = new URLSearchParams()
      body.append('username', username)
      body.append('password', password)
      const { data } = await api.post<LoginResponse>('/auth/login', body, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      return data
    },
  })
}

export const useMemoizedTemplates = () => {
  const { data, ...rest } = useTemplatesQuery()
  const options = useMemo(() => {
    return (data ?? []).map((template) => ({ label: template.name, value: template.id }))
  }, [data])
  return { data, options, ...rest }
}
