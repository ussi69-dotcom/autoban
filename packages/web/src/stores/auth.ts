import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { api, type User, ApiRequestError } from '@/lib/api'

// ============================================================================
// Types
// ============================================================================

export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
}

export interface AuthActions {
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  register: (email: string, password: string, name: string) => Promise<void>
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  checkAuth: () => Promise<void>
  clearError: () => void
}

export type AuthStore = AuthState & AuthActions

// ============================================================================
// Initial State
// ============================================================================

const initialState: AuthState = {
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: true, // Start with loading true to check auth on mount
  error: null,
}

// ============================================================================
// Store
// ============================================================================

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      // ------------------------------------------------------------------------
      // Login
      // ------------------------------------------------------------------------
      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null })

        try {
          const response = await api.auth.login({ email, password })
          const { user, token } = response.data

          set({
            user,
            token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })
        } catch (error) {
          const message = error instanceof ApiRequestError
            ? error.message
            : 'Failed to login'

          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
            error: message,
          })

          throw error
        }
      },

      // ------------------------------------------------------------------------
      // Logout
      // ------------------------------------------------------------------------
      logout: async () => {
        set({ isLoading: true })

        try {
          await api.auth.logout()
        } catch (error) {
          // Continue with logout even if API call fails
          console.error('Logout API error:', error)
        } finally {
          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
          })
        }
      },

      // ------------------------------------------------------------------------
      // Register
      // ------------------------------------------------------------------------
      register: async (email: string, password: string, name: string) => {
        set({ isLoading: true, error: null })

        try {
          const response = await api.auth.register({ email, password, name })
          const { user, token } = response.data

          set({
            user,
            token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })
        } catch (error) {
          const message = error instanceof ApiRequestError
            ? error.message
            : 'Failed to register'

          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
            error: message,
          })

          throw error
        }
      },

      // ------------------------------------------------------------------------
      // Set User
      // ------------------------------------------------------------------------
      setUser: (user: User | null) => {
        set({
          user,
          isAuthenticated: user !== null,
        })
      },

      // ------------------------------------------------------------------------
      // Set Token
      // ------------------------------------------------------------------------
      setToken: (token: string | null) => {
        set({ token })
      },

      // ------------------------------------------------------------------------
      // Check Auth
      // ------------------------------------------------------------------------
      checkAuth: async () => {
        const { token } = get()

        // If no token, not authenticated
        if (!token) {
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
          })
          return
        }

        set({ isLoading: true })

        try {
          const response = await api.auth.me()
          set({
            user: response.data,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })
        } catch (error) {
          // Token is invalid or expired
          if (error instanceof ApiRequestError && error.status === 401) {
            // Try to refresh token
            try {
              const refreshResponse = await api.auth.refresh()
              const { user, token: newToken } = refreshResponse.data

              set({
                user,
                token: newToken,
                isAuthenticated: true,
                isLoading: false,
                error: null,
              })
              return
            } catch {
              // Refresh failed, clear auth state
            }
          }

          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
          })
        }
      },

      // ------------------------------------------------------------------------
      // Clear Error
      // ------------------------------------------------------------------------
      clearError: () => {
        set({ error: null })
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        token: state.token,
        // Don't persist user data for security, re-fetch on checkAuth
      }),
    }
  )
)

// ============================================================================
// Selectors
// ============================================================================

export const selectUser = (state: AuthStore) => state.user
export const selectIsAuthenticated = (state: AuthStore) => state.isAuthenticated
export const selectIsLoading = (state: AuthStore) => state.isLoading
export const selectAuthError = (state: AuthStore) => state.error

// ============================================================================
// Hooks
// ============================================================================

export function useAuth() {
  const user = useAuthStore(selectUser)
  const isAuthenticated = useAuthStore(selectIsAuthenticated)
  const isLoading = useAuthStore(selectIsLoading)
  const error = useAuthStore(selectAuthError)
  const login = useAuthStore((state) => state.login)
  const logout = useAuthStore((state) => state.logout)
  const register = useAuthStore((state) => state.register)
  const checkAuth = useAuthStore((state) => state.checkAuth)
  const clearError = useAuthStore((state) => state.clearError)

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    register,
    checkAuth,
    clearError,
  }
}

export default useAuthStore
