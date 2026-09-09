"use client";

import * as React from "react";
import { toast } from "sonner";
import {
  fetchAdminDashboard,
  fetchAdminModels,
  fetchDocuments,
  fetchOrganizations,
  fetchTeams,
  fetchUsers,
  getMeApi,
} from "@/api/index";
import type {
  AdminDashboard,
  AdminModelAccess,
  AdminUserQuota,
  AuthUser,
  Organization,
  RagDocument,
  Team,
} from "@/lib/types";

export function useAdminData() {
  const [currentUser, setCurrentUser] = React.useState<AuthUser | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [refreshing, setRefreshing] = React.useState(false);

  const [dashboard, setDashboard] = React.useState<AdminDashboard | null>(null);
  const [organizations, setOrganizations] = React.useState<Organization[]>([]);
  const [teams, setTeams] = React.useState<Team[]>([]);
  const [users, setUsers] = React.useState<AdminUserQuota[]>([]);
  const [documents, setDocuments] = React.useState<RagDocument[]>([]);
  const [models, setModels] = React.useState<AdminModelAccess[]>([]);

  const currentUserRef = React.useRef<AuthUser | null>(null);

  const loadData = React.useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) setRefreshing(true);

      // 1. Get Me
      let meUser: AuthUser | null = null;
      try {
        const meData = await getMeApi();
        meUser = meData?.user || meData;
        if (meUser) {
          currentUserRef.current = meUser;
          setCurrentUser((prev) => {
            if (prev?.id === meUser?.id && prev?.role === meUser?.role) return prev;
            return meUser;
          });
        }
      } catch {
        // Fallback for initial state
      }

      // 2. Overview / Dashboard
      try {
        const dashData = await fetchAdminDashboard();
        setDashboard(dashData);
      } catch {
        // Fallback
      }

      // 3. Organizations
      try {
        const orgsData = await fetchOrganizations();
        setOrganizations(orgsData.organizations || []);
      } catch {
        // Fallback
      }

      // 4. Teams
      try {
        const teamsData = await fetchTeams();
        setTeams(teamsData.teams || []);
      } catch {
        // Fallback
      }

      // 5. Users
      try {
        const usersData = await fetchUsers();
        setUsers(usersData.users || []);
      } catch {
        // Fallback
      }

      // 6. Documents
      try {
        const docsData = await fetchDocuments();
        setDocuments(docsData.documents || []);
      } catch {
        // Fallback
      }

      // 7. Models (Only for super_admin)
      const currentRole = meUser?.role || currentUserRef.current?.role;
      if (currentRole === "super_admin") {
        try {
          const modelsData = await fetchAdminModels();
          setModels(modelsData.models || []);
        } catch {
          // Fallback
        }
      }
    } catch {
      toast.error("خطا در دریافت اطلاعات مدیریتی از سرور.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  React.useEffect(() => {
    loadData();
  }, [loadData]);

  // Auto-poll documents when any document is processing in background
  const isProcessing = React.useMemo(
    () => documents.some((d) => d.status === "processing"),
    [documents]
  );

  React.useEffect(() => {
    if (!isProcessing) return;

    const interval = setInterval(async () => {
      try {
        const docsData = await fetchDocuments();
        if (docsData && docsData.documents) {
          setDocuments(docsData.documents);
        }
      } catch {
        // silent polling catch
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [isProcessing]);

  return {
    currentUser,
    loading,
    refreshing,
    dashboard,
    organizations,
    teams,
    users,
    documents,
    models,
    setOrganizations,
    setTeams,
    setUsers,
    setDocuments,
    loadData,
  };
}
