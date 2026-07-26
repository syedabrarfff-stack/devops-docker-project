import { create } from "zustand";
import { persist } from "zustand/middleware";

export const useAuthStore = create(
  persist(
    (set) => ({
      token: null,
      role: null,
      clinicId: null,
      organizationId: null,
      fullName: null,

      login: ({ access_token, role, clinic_id, organization_id, full_name }) =>
        set({
          token: access_token,
          role,
          clinicId: clinic_id,
          organizationId: organization_id,
          fullName: full_name,
        }),

      logout: () =>
        set({ token: null, role: null, clinicId: null, organizationId: null, fullName: null }),
    }),
    { name: "sarah-auth" }
  )
);
