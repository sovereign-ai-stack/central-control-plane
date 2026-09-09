import * as React from "react";
import {
  Building2,
  Cpu,
  FileText,
  FolderTree,
  LayoutDashboard,
  SlidersHorizontal,
  Users,
} from "lucide-react";
import type { UserRole } from "@/lib/types";

export type AdminSection =
  | "overview"
  | "organizations"
  | "teams"
  | "users"
  | "knowledge"
  | "models"
  | "limits";

export interface NavItem {
  id: AdminSection;
  label: string;
  detail: string;
  icon: React.ComponentType<{ className?: string }>;
  allowedRoles: UserRole[];
}

export const ALL_NAV_ITEMS: NavItem[] = [
  {
    id: "overview",
    label: "داشبورد و وضعیت",
    detail: "تله‌متری زنده و نودهای پردازشی",
    icon: LayoutDashboard,
    allowedRoles: ["super_admin", "org_admin", "team_admin"],
  },
  {
    id: "organizations",
    label: "ارگان‌ها و شرکت‌ها",
    detail: "مدیریت سازمان‌های سامانه",
    icon: Building2,
    allowedRoles: ["super_admin"],
  },
  {
    id: "teams",
    label: "تیم‌ها و دپارتمان‌ها",
    detail: "مدیریت واحدهای سازمانی",
    icon: FolderTree,
    allowedRoles: ["super_admin", "org_admin"],
  },
  {
    id: "users",
    label: "مدیریت کاربران",
    detail: "تعریف، ویرایش و فیلتر کاربران",
    icon: Users,
    allowedRoles: ["super_admin", "org_admin", "team_admin"],
  },
  {
    id: "knowledge",
    label: "پایگاه دانش (RAG)",
    detail: "آپلود و ایندکس اسناد سازمانی",
    icon: FileText,
    allowedRoles: ["super_admin", "org_admin", "team_admin"],
  },
  {
    id: "models",
    label: "مدل‌ها و نودهای GPU",
    detail: "مدل‌های فعال و کارت‌های گرافیک",
    icon: Cpu,
    allowedRoles: ["super_admin"],
  },
  {
    id: "limits",
    label: "سهمیه‌ها و محدودیت‌ها",
    detail: "تنظیم سقف توکن و Rate Limit",
    icon: SlidersHorizontal,
    allowedRoles: ["super_admin"],
  },
];

export const ALLOWED_OBSERVABILITY_ROLES: UserRole[] = ["super_admin"];

export function getLangfuseUrl(): string {
  if (process.env.NEXT_PUBLIC_LANGFUSE_URL) {
    return process.env.NEXT_PUBLIC_LANGFUSE_URL;
  }
  if (typeof window !== "undefined" && window.location?.hostname) {
    return `${window.location.protocol}//${window.location.hostname}:3000`;
  }
  return "http://localhost:3000";
}

export function getLiteLlmUrl(): string {
  if (process.env.NEXT_PUBLIC_LITELLM_URL) {
    return process.env.NEXT_PUBLIC_LITELLM_URL;
  }
  if (typeof window !== "undefined" && window.location?.hostname) {
    return `${window.location.protocol}//${window.location.hostname}:4000`;
  }
  return "http://localhost:4000";
}

export const DEFAULT_LANGFUSE_URL = "http://localhost:3000";
export const DEFAULT_LITELLM_URL = "http://localhost:4000";

