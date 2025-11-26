import { zodResolver } from '@hookform/resolvers/zod'
import { ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useLocation, useNavigate, type Location } from 'react-router-dom'
import { z } from 'zod'

import { api, getErrorMessage } from '@/api/client'
import { useLoginMutation } from '@/api/hooks'
import type { components } from '@/api/gen/schema'
import { useAuth } from '@/auth/useAuth'
import { FormField } from '@/components/forms/FormField'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useToast } from '@/components/ui/toastContext'

const schema = z.object({
  username: z.string().email('Use your email address'),
  password: z.string().min(6, 'Password is required'),
})

export type LoginFormValues = z.infer<typeof schema>

export const LoginPage = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, defaultRoute } = useAuth()
  const { push } = useToast()
  const mutation = useLoginMutation()
  const [serverError, setServerError] = useState<string | null>(null)

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(schema),
    defaultValues: { username: '', password: '' },
  })

  const onSubmit = async (values: LoginFormValues) => {
    setServerError(null)
    try {
      const token = await mutation.mutateAsync(values)
      const { data: user } = await api.get<components['schemas']['UserRead']>('/auth/me', {
        headers: { Authorization: `Bearer ${token.access_token}` },
      })
      login(token.access_token, user)
      push({ title: 'Welcome back', description: `Signed in as ${user.full_name}`, variant: 'success' })
      const redirectTo = (location.state as { from?: Location })?.from?.pathname ?? defaultRoute
      navigate(redirectTo, { replace: true })
    } catch (error) {
      const message = getErrorMessage(error)
      setServerError(message)
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 shadow-xl">
        <div className="mb-6 flex items-center gap-3">
          <div className="rounded-2xl bg-brand-100 p-3 text-brand-700">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div>
            <p className="text-lg font-semibold text-slate-900">Safety Inspection Checklist</p>
            <p className="text-sm text-slate-500">Sign in to manage inspections</p>
          </div>
        </div>
        <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
          <FormField label="Email" htmlFor="email" error={form.formState.errors.username?.message}>
            <Input id="email" type="email" {...form.register('username')} placeholder="you@example.com" />
          </FormField>
          <FormField label="Password" htmlFor="password" error={form.formState.errors.password?.message}>
            <Input id="password" type="password" {...form.register('password')} placeholder="********" />
          </FormField>
          {serverError && <p className="text-sm text-red-600">{serverError}</p>}
          <Button type="submit" className="w-full" loading={mutation.isPending}>
            Sign in
          </Button>
        </form>
        <p className="mt-6 text-center text-xs text-slate-400">
          Having CORS issues? Allow http://localhost:5173 in the FastAPI settings.
        </p>
      </div>
    </div>
  )
}
