/** Single password rule for sign-up and password change; mirrors backend `UserCreate.password` (min_length=8). */
export const PASSWORD_MIN_LENGTH = 8

export const passwordRules = [
  (v: string) => !!v || 'Password is required',
  (v: string) =>
    v.length >= PASSWORD_MIN_LENGTH || `Password must be at least ${PASSWORD_MIN_LENGTH} characters`
]
