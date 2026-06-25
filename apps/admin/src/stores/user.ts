import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { WebResultUser } from '@en/common/user'

interface UserState {
  user: WebResultUser | null
  accessToken: string | null
  setUser: (user: WebResultUser) => void
  logout: () => void
}

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      setUser: (user) =>
        set({
          user,
          accessToken: user.token.accessToken,
        }),
      logout: () => set({ user: null, accessToken: null }),
    }),
    { name: 'admin-user' },
  ),
)
