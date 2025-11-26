import { describe, expect, test, vi } from 'vitest'
import userEvent from '@testing-library/user-event'
import { screen } from '@testing-library/react'

import { TemplateEditorPage } from '@/pages/Templates/TemplateEditor'
import { renderWithProviders } from '@/test-utils'

const mockCreate = vi.fn()
const noopMutation = { mutateAsync: vi.fn(), isPending: false }

vi.mock('@/api/hooks', () => ({
  useCreateTemplateMutation: () => ({ mutateAsync: mockCreate, isPending: false }),
  useUpdateTemplateMutation: () => noopMutation,
  useTemplateQuery: () => ({ data: undefined, isLoading: false }),
  useTemplatesQuery: () => ({ data: [], isLoading: false }),
  useSectionMutations: () => ({
    createSection: noopMutation,
    updateSection: noopMutation,
    deleteSection: noopMutation,
  }),
  useItemMutations: () => ({
    createItem: noopMutation,
    updateItem: noopMutation,
    deleteItem: noopMutation,
  }),
}))

describe('TemplateEditorPage', () => {
  test('collects nested sections and items', async () => {
    renderWithProviders(<TemplateEditorPage />)

    await userEvent.type(screen.getByLabelText(/name/i), 'Vehicle template')
    await userEvent.click(screen.getByRole('button', { name: /add section/i }))

    const [sectionTitle] = screen.getAllByLabelText(/title/i)
    await userEvent.clear(sectionTitle)
    await userEvent.type(sectionTitle, 'Engine bay')

    await userEvent.click(screen.getByRole('button', { name: /add item/i }))
    const promptInput = screen.getByLabelText(/prompt/i)
    await userEvent.clear(promptInput)
    await userEvent.type(promptInput, 'Check coolant level')

    await userEvent.click(screen.getByRole('button', { name: /save template/i }))

    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Vehicle template',
        sections: expect.arrayContaining([
          expect.objectContaining({
            title: 'Engine bay',
            items: expect.arrayContaining([expect.objectContaining({ prompt: 'Check coolant level' })]),
          }),
        ]),
      }),
    )
  })
})
