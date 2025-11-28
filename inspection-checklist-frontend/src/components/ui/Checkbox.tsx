import { forwardRef } from 'react'
import type { InputHTMLAttributes } from 'react'

import { clsx } from 'clsx'

type CheckboxProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'checked' | 'defaultChecked' | 'onChange'> & {
  checked?: boolean
  defaultChecked?: boolean
  onCheckedChange?: (checked: boolean) => void
  onChange?: InputHTMLAttributes<HTMLInputElement>['onChange']
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { className, checked, defaultChecked, onCheckedChange, onChange, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      type="checkbox"
      className={clsx(
        'h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-2 focus:ring-brand-100 focus:ring-offset-0',
        className,
      )}
      checked={checked}
      defaultChecked={defaultChecked}
      onChange={(event) => {
        onCheckedChange?.(event.target.checked)
        onChange?.(event)
      }}
      {...props}
    />
  )
})

Checkbox.displayName = 'Checkbox'
