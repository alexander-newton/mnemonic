/**
 * Login page - User authentication page.
 * Provides email/password login with form validation and error handling.
 */

import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ErrorMessage } from '@/components/ui/ErrorMessage';
import { useAuthStore } from '@/stores/authStore';
import { useLogin } from '@/hooks/useAuth';

/**
 * Validation schema for login form
 */
const loginSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Invalid email format'),
  password: z
    .string()
    .min(1, 'Password is required')
    .min(8, 'Password must be at least 8 characters'),
  rememberMe: z.boolean().default(false),
});

type LoginFormData = z.infer<typeof loginSchema>;

/**
 * LoginPage provides the login interface.
 * Users can authenticate with email and password.
 * Features include form validation, error handling, and remember me checkbox.
 *
 * @example
 * ```tsx
 * <Route path="/login" element={<LoginPage />} />
 * ```
 */
export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const { mutate: login, isPending, error } = useLogin();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/decks', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const onSubmit = (data: LoginFormData) => {
    login({ email: data.email, password: data.password });
  };

  const errorMessage = error
    ? error instanceof Error
      ? error.message
      : 'Login failed. Please try again.'
    : null;

  return (
    <div className="max-w-md mx-auto py-12">
      <div className="bg-white rounded-lg shadow p-8">
        <h1 className="text-3xl font-bold mb-6">Login</h1>

        {errorMessage && (
          <div className="mb-6">
            <ErrorMessage message={errorMessage} onRetry={() => reset()} />
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} role="form" className="space-y-4">
          <Input
            {...register('email')}
            label="Email"
            type="email"
            placeholder="you@example.com"
            error={errors.email?.message}
            disabled={isPending}
          />

          <Input
            {...register('password')}
            label="Password"
            type="password"
            placeholder="Enter your password"
            error={errors.password?.message}
            disabled={isPending}
          />

          <div className="flex items-center">
            <input
              type="checkbox"
              id="rememberMe"
              {...register('rememberMe')}
              className="w-4 h-4 border-gray-300 rounded"
              disabled={isPending}
            />
            <label htmlFor="rememberMe" className="ml-2 text-sm text-gray-700">
              Remember me
            </label>
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full"
            loading={isPending}
            disabled={isPending}
          >
            Login
          </Button>
        </form>

        <div className="mt-6 space-y-4">
          <a href="#" className="block text-center text-sm text-blue-600 hover:text-blue-700">
            Forgot password?
          </a>

          <p className="text-center text-sm text-gray-600">
            Don't have an account?{' '}
            <a href="/register" className="text-blue-600 hover:text-blue-700 font-medium">
              Register
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};
