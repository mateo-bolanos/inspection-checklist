import * as Dialog from '@radix-ui/react-dialog'
import type { ReactNode } from 'react'

import { Button } from './Button'

export type ModalProps = {
  open?: boolean
  onOpenChange?: (open: boolean) => void
  title: string
  description?: string
  triggerLabel?: string
  children: ReactNode
  widthClass?: string
}

export const Modal = ({
  open,
  onOpenChange,
  title,
  description,
  triggerLabel,
  children,
  widthClass = 'w-full max-w-xl',
}: ModalProps) => {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      {triggerLabel && (
        <Dialog.Trigger asChild>
          <Button variant="secondary">{triggerLabel}</Button>
        </Dialog.Trigger>
      )}
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-slate-900/30 backdrop-blur-sm" />
        <Dialog.Content
          className={`fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-white p-6 shadow-xl ${widthClass}`}
        >
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <Dialog.Title className="text-lg font-semibold text-slate-900">{title}</Dialog.Title>
              {description && <Dialog.Description className="text-sm text-slate-500">{description}</Dialog.Description>}
            </div>
            <Dialog.Close asChild>
              <button className="rounded-full p-2 text-slate-500 transition hover:bg-slate-100" aria-label="Close dialog">
                ×
              </button>
            </Dialog.Close>
          </div>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
