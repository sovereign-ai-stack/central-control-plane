"use client";

import * as React from "react";
import { toast } from "sonner";
import {
  createUser,
  deleteUser,
  updateUser,
} from "@/api/index";
import type { AdminUserQuota, UserRole } from "@/lib/types";

export function useUserManagement(onReload: () => void) {
  const [addUserOpen, setAddUserOpen] = React.useState(false);
  const [editUserOpen, setEditUserOpen] = React.useState(false);

  // Filter States
  const [userSearch, setUserSearch] = React.useState("");
  const [userFilterRole, setUserFilterRole] = React.useState<string>("all");
  const [userFilterOrg, setUserFilterOrg] = React.useState<string>("all");
  const [userFilterTeam, setUserFilterTeam] = React.useState<string>("all");

  // Create user form
  const [newUserName, setNewUserName] = React.useState("");
  const [newUserEmail, setNewUserEmail] = React.useState("");
  const [newUserPassword, setNewUserPassword] = React.useState("password");
  const [newUserRole, setNewUserRole] = React.useState<UserRole>("user");
  const [newUserOrgId, setNewUserOrgId] = React.useState("");
  const [newUserTeamId, setNewUserTeamId] = React.useState("");
  const [newUserTokenLimit, setNewUserTokenLimit] = React.useState(500000);

  // Edit user form
  const [editingUserId, setEditingUserId] = React.useState("");
  const [editUserName, setEditUserName] = React.useState("");
  const [editUserEmail, setEditUserEmail] = React.useState("");
  const [editUserPassword, setEditUserPassword] = React.useState("");
  const [editUserRole, setEditUserRole] = React.useState<UserRole>("user");
  const [editUserOrgId, setEditUserOrgId] = React.useState("");
  const [editUserTeamId, setEditUserTeamId] = React.useState("");
  const [editUserTokenLimit, setEditUserTokenLimit] = React.useState(500000);
  const [editUserIsActive, setEditUserIsActive] = React.useState(true);

  const openEditUser = (user: AdminUserQuota) => {
    setEditingUserId(user.id);
    setEditUserName(user.name);
    setEditUserEmail(user.email);
    setEditUserPassword("");
    setEditUserRole(user.role || "user");
    setEditUserOrgId(user.organizationId || "");
    setEditUserTeamId(user.teamId || "");
    setEditUserTokenLimit(user.tokenLimit);
    setEditUserIsActive(user.isActive !== false);
    setEditUserOpen(true);
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUserName.trim() || !newUserEmail.trim() || !newUserPassword.trim()) {
      toast.error("لطفاً تمامی فیلدهای الزامی کاربر را وارد فرمایید.");
      return;
    }
    try {
      await createUser({
        name: newUserName.trim(),
        email: newUserEmail.trim().toLowerCase(),
        password: newUserPassword.trim(),
        role: newUserRole,
        organizationId: newUserOrgId || undefined,
        teamId: newUserTeamId || undefined,
        tokenLimit: Number(newUserTokenLimit) || 500000,
      });
      toast.success(`کاربر «${newUserName}» با موفقیت افزوده شد.`);
      setAddUserOpen(false);
      setNewUserName("");
      setNewUserEmail("");
      setNewUserPassword("password");
      setNewUserRole("user");
      setNewUserOrgId("");
      setNewUserTeamId("");
      setNewUserTokenLimit(500000);
      onReload();
    } catch {
      toast.error("خطا در ایجاد کاربر جدید.");
    }
  };

  const handleSaveEditUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUserId || !editUserName.trim()) return;

    try {
      await updateUser(editingUserId, {
        name: editUserName.trim(),
        password: editUserPassword.trim() || undefined,
        role: editUserRole,
        organizationId: editUserOrgId || undefined,
        teamId: editUserTeamId || undefined,
        tokenLimit: Number(editUserTokenLimit),
        isActive: editUserIsActive,
      });
      toast.success("مشخصات کاربر به‌روزرسانی شد.");
      setEditUserOpen(false);
      onReload();
    } catch {
      toast.error("خطا در ذخیره مشخصات کاربر.");
    }
  };

  const handleToggleUserActive = async (userId: string, currentActive: boolean) => {
    try {
      await updateUser(userId, { isActive: !currentActive });
      toast.success(`وضعیت کاربر با موفقیت به ${!currentActive ? "فعال" : "غیرفعال"} تغییر یافت.`);
      onReload();
    } catch {
      toast.error("خطا در تغییر وضعیت کاربر.");
    }
  };

  const handleDeleteUser = async (userId: string) => {
    try {
      await deleteUser(userId);
      toast.success("کاربر با موفقیت حذف گردید.");
      onReload();
    } catch {
      toast.error("خطا در حذف کاربر.");
    }
  };

  return {
    addUserOpen,
    setAddUserOpen,
    editUserOpen,
    setEditUserOpen,
    userSearch,
    setUserSearch,
    userFilterRole,
    setUserFilterRole,
    userFilterOrg,
    setUserFilterOrg,
    userFilterTeam,
    setUserFilterTeam,
    newUserName,
    setNewUserName,
    newUserEmail,
    setNewUserEmail,
    newUserPassword,
    setNewUserPassword,
    newUserRole,
    setNewUserRole,
    newUserOrgId,
    setNewUserOrgId,
    newUserTeamId,
    setNewUserTeamId,
    newUserTokenLimit,
    setNewUserTokenLimit,
    editingUserId,
    editUserName,
    setEditUserName,
    editUserEmail,
    setEditUserEmail,
    editUserPassword,
    setEditUserPassword,
    editUserRole,
    setEditUserRole,
    editUserOrgId,
    setEditUserOrgId,
    editUserTeamId,
    setEditUserTeamId,
    editUserTokenLimit,
    setEditUserTokenLimit,
    editUserIsActive,
    setEditUserIsActive,
    openEditUser,
    handleCreateUser,
    handleSaveEditUser,
    handleToggleUserActive,
    handleDeleteUser,
  };
}
