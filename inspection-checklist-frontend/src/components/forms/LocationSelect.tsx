import { Plus } from 'lucide-react'
import { useMemo, useState } from 'react'

import { getErrorMessage } from '@/api/client'
import { useCreateLocationMutation, useLocationsQuery } from '@/api/hooks'
import { useAuth } from '@/auth/useAuth'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Select } from '@/components/ui/Select'
import { useToast } from '@/components/ui/toastContext'

type LocationSelectProps = {
  value?: string
  onChange: (value: string) => void
  disabled?: boolean
  placeholder?: string
  legacyLabel?: string | null
  name?: string
  id?: string
}

export const LocationSelect = ({
  value = '',
  onChange,
  disabled,
  placeholder = 'Select location',
  legacyLabel,
  name,
  id,
}: LocationSelectProps) => {
  const locationsQuery = useLocationsQuery()
  const createLocation = useCreateLocationMutation()
  const { push } = useToast()
  const { hasRole } = useAuth()
  const canManageLocations = hasRole(['admin'])
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [newLocationName, setNewLocationName] = useState('')

  const options = useMemo(() => locationsQuery.data ?? [], [locationsQuery.data])
  const isLoading = locationsQuery.isLoading
  const hasNoLocations = !isLoading && options.length === 0

  const handleSelectChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    onChange(event.target.value)
  }

  const handleAddLocation = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmed = newLocationName.trim()
    if (!trimmed) {
      push({ title: 'Location name is required', variant: 'warning' })
      return
    }
    try {
      const location = await createLocation.mutateAsync({ name: trimmed })
      push({ title: 'Location added', variant: 'success' })
      setNewLocationName('')
      setIsModalOpen(false)
      onChange(String(location.id))
    } catch (error) {
      push({ title: 'Unable to add location', description: getErrorMessage(error), variant: 'error' })
    }
  }

  const placeholderLabel = isLoading ? 'Loading locations…' : placeholder

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        <Select
          id={id}
          name={name}
          value={value ?? ''}
          onChange={handleSelectChange}
          disabled={disabled || isLoading}
        >
          <option value="" disabled>
            {placeholderLabel}
          </option>
          {options.map((location) => (
            <option key={location.id} value={location.id}>
              {location.name}
            </option>
          ))}
        </Select>
        {canManageLocations && (
          <>
            <Button
              type="button"
              variant="secondary"
              className="px-3"
              onClick={() => setIsModalOpen(true)}
              aria-label="Add location"
            >
              <Plus className="h-4 w-4" />
            </Button>
            <Modal open={isModalOpen} onOpenChange={setIsModalOpen} title="Add location">
              <form className="space-y-4" onSubmit={handleAddLocation}>
                <Input
                  autoFocus
                  placeholder="Location name"
                  value={newLocationName}
                  onChange={(event) => setNewLocationName(event.target.value)}
                />
                <div className="flex justify-end gap-2">
                  <Button type="button" variant="ghost" onClick={() => setIsModalOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" loading={createLocation.isPending}>
                    Save
                  </Button>
                </div>
              </form>
            </Modal>
          </>
        )}
      </div>
      {legacyLabel && !value && <p className="text-xs text-slate-500">Existing value: {legacyLabel}</p>}
      {hasNoLocations && (
        <p className="text-xs text-slate-500">
          {canManageLocations ? 'Add the first location using the + button.' : 'Ask an administrator to create locations.'}
        </p>
      )}
    </div>
  )
}
