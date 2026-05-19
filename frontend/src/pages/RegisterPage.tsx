/**
 * Register page - User registration page.
 * Provides email/password registration with form validation and error handling.
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
import { useRegister } from '@/hooks/useAuth';

/**
 * Validation schema for registration form
 */
const registerSchema = z
  .object({
    email: z.string().min(1, 'Email is required').email('Invalid email format'),
    password: z
      .string()
      .min(1, 'Password is required')
      .min(8, 'Password must be at least 8 characters')
      .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
      .regex(/[0-9]/, 'Password must contain at least one number'),
    confirmPassword: z.string().min(1, 'Confirm password is required'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

type RegisterFormData = z.infer<typeof registerSchema>;

/**
 * RegisterPage provides the user registration interface.
 * Users can create a new account with email and password.
 * Features include form validation, password strength requirements, and error handling.
 *
 * @example
 * ```tsx
 * <Route path="/register" element={<RegisterPage />} />
 * ```
 */
export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const { mutate: register, isPending, error } = useRegister();

  const {
    register: registerField,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/decks', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const onSubmit = (data: RegisterFormData) => {
    register({ email: data.email, password: data.password });
  };

  const errorMessage = error
    ? error instanceof Error
      ? error.message
      : 'Registration failed. Please try again.'
    : null;

  return (
    <div className="max-w-md mx-auto py-12">
      <div className="bg-white rounded-lg shadow p-8">
        <h1 className="text-3xl font-bold mb-6">Register</h1>

        {errorMessage && (
          <div className="mb-6">
            <ErrorMessage message={errorMessage} onRetry={() => reset()} />
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} role="form" className="space-y-4">
          <Input
            {...registerField('email')}
            label="Email"
            type="email"
            placeholder="you@example.com"
            error={errors.email?.message}
            disabled={isPending}
          />

          <Input
            {...registerField('password')}
            label="Password"
            type="password"
            placeholder="Create a strong password"
            error={errors.password?.message}
            helperText="At least 8 characters, including uppercase letter and number"
            disabled={isPending}
          />

          <Input
            {...registerField('confirmPassword')}
            label="Confirm Password"
            type="password"
            placeholder="Confirm your password"
            error={errors.confirmPassword?.message}
            disabled={isPending}
          />

          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full"
            loading={isPending}
            disabled={isPending}
          >
            Register
          </Button>
        </form>

        <div className="mt-6">
          <p className="text-center text-sm text-gray-600">
            Already have an account?{' '}
            <a href="/login" className="text-blue-600 hover:text-blue-700 font-medium">
              Login
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};
