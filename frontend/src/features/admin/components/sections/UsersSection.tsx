"use client";

import * as React from "react";
import { Edit2, Plus, Search, Trash2, UserCheck, UserPlus, Users, UserX } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CustomSelect } from "@/components/ui/custom-select";
import { Input } from "@/components/ui/input";
import type { AdminUserQuota, Organization, Team } from "@/lib/types";

interface UsersSectionProps {
  users: AdminUserQuota[];
  organizations: Organization[];
  teams: Team[];
  userSearch: string;
  onUserSearchChange: (val: string) => void;
  userFilterRole: string;
  onUserFilterRoleChange: (val: string) => void;
  userFilterOrg: string;
  onUserFilterOrgChange: (val: string) => void;
  userFilterTeam: string;
  onUserFilterTeamChange: (val: string) => void;
  onOpenAddUser: () => void;
  onOpenEditUser: (user: AdminUserQuota) => void;
  onToggleUserActive: (userId: string, currentActive: boolean) => void;
  onDeleteUser: (userId: string) => void;
}

export function UsersSection({
  users,
  organizations,
  teams,
  userSearch,
  onUserSearchChange,
  userFilterRole,
  onUserFilterRoleChange,
  userFilterOrg,
  onUserFilterOrgChange,
  userFilterTeam,
  onUserFilterTeamChange,
  onOpenAddUser,
  onOpenEditUser,
  onToggleUserActive,
  onDeleteUser,
}: UsersSectionProps) {
  const filteredUsers = users.filter((u) => {
    if (userSearch.trim()) {
      const q = userSearch.toLowerCase();
      const matchName = u.name.toLowerCase().includes(q);
      const matchEmail = u.email.toLowerCase().includes(q);
      if (!matchName && !matchEmail) return false;
    }
    if (userFilterRole !== "all" && u.role !== userFilterRole) return false;
    if (userFilterOrg !== "all" && u.organizationId !== userFilterOrg) return false;
    if (userFilterTeam !== "all" && u.teamId !== userFilterTeam) return false;
    return true;
  });

  const getRoleBadge = (role?: string) => {
    switch (role) {
      case "super_admin":
        return <Badge className="bg-brand-cyan/20 text-brand-cyan border-brand-cyan/30 text-[10.5px]">مدیر کل سیستم</Badge>;
      case "org_admin":
        return <Badge className="bg-warning/20 text-warning border-warning/30 text-[10.5px]">مدیر سازمان</Badge>;
      case "team_admin":
        return <Badge className="bg-info/20 text-info border-info/30 text-[10.5px]">مدیر تیم</Badge>;
      default:
        return <Badge variant="outline" className="border-border/40 text-[10.5px]">کاربر عادی</Badge>;
    }
  };

  const availableFilterTeams =
    userFilterOrg && userFilterOrg !== "all"
      ? teams.filter((t) => t.organizationId === userFilterOrg)
      : teams;

  const handleOrgFilterChange = (val: string) => {
    onUserFilterOrgChange(val);
    if (val !== "all" && userFilterTeam !== "all") {
      const validInOrg = teams.some((t) => t.id === userFilterTeam && t.organizationId === val);
      if (!validInOrg) {
        onUserFilterTeamChange("all");
      }
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-on-surface">مدیریت کاربران و دسترسی‌ها</h2>
          <p className="text-xs text-on-surface-variant">
            تعریف حساب‌های کاربری، کنترل سطح دسترسی RBAC و سقف توکن
          </p>
        </div>
        <Button
          size="sm"
          onClick={onOpenAddUser}
          className="bg-brand-cyan hover:bg-brand-cyan-strong text-slate-950 font-bold text-xs gap-1.5 cursor-pointer self-start sm:self-auto"
        >
          <UserPlus className="size-4" />
          افزودن کاربر جدید
        </Button>
      </div>

      {/* FILTERS BAR */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5 bg-surface-raised border border-border/40 rounded-2xl p-3">
        <div className="relative">
          <Search className="size-4 text-on-surface-variant absolute right-3 top-1/2 -translate-y-1/2" />
          <Input
            placeholder="جستجوی نام یا ایمیل..."
            value={userSearch}
            onChange={(e) => onUserSearchChange(e.target.value)}
            className="bg-surface-container/50 pe-9 text-xs h-9"
          />
        </div>

        <CustomSelect
          value={userFilterRole}
          onChange={onUserFilterRoleChange}
          options={[
            { value: "all", label: "همه نقش‌ها" },
            { value: "super_admin", label: "Super Admin" },
            { value: "org_admin", label: "Org Admin" },
            { value: "team_admin", label: "Team Admin" },
            { value: "user", label: "User (کاربر عادی)" },
          ]}
          className="bg-surface-container/50 text-xs h-9"
        />

        <CustomSelect
          value={userFilterOrg}
          onChange={handleOrgFilterChange}
          options={[
            { value: "all", label: "همه سازمان‌ها" },
            ...organizations.map((o) => ({ value: o.id, label: o.name })),
          ]}
          className="bg-surface-container/50 text-xs h-9"
        />

        <CustomSelect
          value={userFilterTeam}
          onChange={onUserFilterTeamChange}
          options={[
            { value: "all", label: "همه تیم‌ها" },
            ...availableFilterTeams.map((t) => ({ value: t.id, label: t.name })),
          ]}
          className="bg-surface-container/50 text-xs h-9"
        />
      </div>

      {/* USERS TABLE */}
      <div className="bg-surface-raised border border-border/40 rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-start text-xs">
            <thead className="bg-surface-container/50 border-b border-border/30 text-on-surface-variant font-semibold">
              <tr>
                <th className="p-3 text-start">کاربر</th>
                <th className="p-3 text-start">نقش</th>
                <th className="p-3 text-start">سازمان / تیم</th>
                <th className="p-3 text-start">مصرف سهمیه</th>
                <th className="p-3 text-start">وضعیت</th>
                <th className="p-3 text-end">عملیات</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/20">
              {filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-on-surface-variant">
                    کاربری با مشخصات جستجو شده یافت نشد.
                  </td>
                </tr>
              ) : (
                filteredUsers.map((u) => {
                  const usedPct = Math.min(
                    100,
                    Math.round(((u.usedTokens || 0) / Math.max(1, u.tokenLimit || 1)) * 100)
                  );
                  return (
                    <tr key={u.id} className="hover:bg-surface-container/30 transition-colors">
                      <td className="p-3">
                        <div className="flex items-center gap-2.5">
                          <div className="flex size-8 items-center justify-center rounded-xl bg-surface-container border border-border/40 font-bold font-mono text-brand-cyan">
                            {u.name.charAt(0)}
                          </div>
                          <div>
                            <div className="font-bold text-on-surface">{u.name}</div>
                            <div className="text-[11px] text-on-surface-variant font-mono">{u.email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="p-3">{getRoleBadge(u.role)}</td>
                      <td className="p-3">
                        <div className="text-on-surface">{u.organizationName || u.organizationId || "سراسری"}</div>
                        <div className="text-[10.5px] text-on-surface-variant font-mono">
                          {u.teamName || u.teamId || "بدون تیم"}
                        </div>
                      </td>
                      <td className="p-3 min-w-[140px]">
                        <div className="space-y-1">
                          <div className="flex justify-between text-[10.5px] font-mono">
                            <span>{(u.usedTokens || 0).toLocaleString()}</span>
                            <span>{(u.tokenLimit || 0).toLocaleString()}</span>
                          </div>
                          <div className="h-1.5 w-full rounded-full bg-surface-container overflow-hidden">
                            <div
                              className={`h-full ${usedPct > 90 ? "bg-destructive" : "bg-brand-cyan"}`}
                              style={{ width: `${usedPct}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="p-3">
                        <Badge
                          variant="outline"
                          className={`text-[10.5px] ${
                            u.isActive !== false
                              ? "text-brand-cyan border-brand-cyan/30"
                              : "text-destructive border-destructive/30"
                          }`}
                        >
                          {u.isActive !== false ? "فعال" : "غیرفعال"}
                        </Badge>
                      </td>
                      <td className="p-3 text-end">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => onOpenEditUser(u)}
                            className="size-7 text-on-surface-variant hover:text-brand-cyan"
                            title="ویرایش"
                          >
                            <Edit2 className="size-3.5" />
                          </Button>
                          {u.role !== "super_admin" && (
                            <>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => onToggleUserActive(u.id, u.isActive !== false)}
                                className="size-7 text-on-surface-variant hover:text-warning"
                                title={u.isActive !== false ? "غیرفعال‌سازی" : "فعال‌سازی"}
                              >
                                {u.isActive !== false ? (
                                  <UserX className="size-3.5" />
                                ) : (
                                  <UserCheck className="size-3.5" />
                                )}
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => onDeleteUser(u.id)}
                                className="size-7 text-on-surface-variant hover:text-destructive"
                                title="حذف کاربر"
                              >
                                <Trash2 className="size-3.5" />
                              </Button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
