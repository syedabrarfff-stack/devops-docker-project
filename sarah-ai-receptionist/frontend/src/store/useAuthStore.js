import { create } from "zustand";
import { persist } from "zustand/middleware";

// Two stores:
//
//   useAuthStore  -- identity fields (role, clinic_id, full name). Safe to
//                    persist in localStorage; the browser knowing which
//                    portal to render before /auth/refresh completes avoids
//                    a login-screen flash on every reload. These are not
//                    credentials by themselves.
//
//   accessToken   -- module-level variable, NOT persisted. XSS reading
//                    localStorage cannot lift the session token this way,
//                    because it isn't there. The token lives only in the
//                    JS heap and dies when the tab closes; a reload calls
//                    /auth/refresh to mint a fresh one from the HttpOnly
//                    refresh cookie the browser sends automatically.
//
// The old model (token in a persisted store, 24h lifetime) meant any XSS
// anywhere in the SPA was a full 24h session-token theft with nothing the
// server could do about it. This split isolates the credential from disk.

let _accessToken = null;
const _listeners = new Set();

export function getAccessToken() {
  return _accessToken;
}

export function setAccessToken(token) {
  _accessToken = token || null;
  for (const l of _listeners) l(_accessToken);
}

export function onAccessTokenChange(listener) {
  _listeners.add(listener);
  return () => _listeners.delete(listener);
}

export const useAuthStore = create(
  persist(
    (set) => ({
      // token is intentionally NOT here anymore.
      role: null,
      clinicId: null,
      organizationId: null,
      fullName: null,
      // Distinguishes "not signed in" from "haven't tried to refresh yet",
      // so pages don't flash the login screen on a hard reload before the
      // silent refresh completes.
      bootstrapped: false,

      // Called on successful /auth/login or /auth/refresh.
      setSession: ({ role, clinic_id, organization_id, full_name }) =>
        set({
          role,
          clinicId: clinic_id,
          organizationId: organization_id,
          fullName: full_name,
          bootstrapped: true,
        }),

      markBootstrapped: () => set({ bootstrapped: true }),

      logout: () => {
        setAccessToken(null);
        set({
          role: null,
          clinicId: null,
          organizationId: null,
          fullName: null,
          bootstrapped: true,
        });
      },
    }),
    {
      name: "sarah-auth",
      // Never persist the token even if a caller accidentally sets it -- a
      // defense-in-depth check, since setAccessToken bypasses this store.
      partialize: (state) => ({
        role: state.role,
        clinicId: state.clinicId,
        organizationId: state.organizationId,
        fullName: state.fullName,
      }),
    }
  )
);
