"use client";

import * as React from "react";
import { toast } from "sonner";
import {
  createOrganization,
  deleteOrganization,
  updateOrganization,
} from "@/api/index";
import type { Organization } from "@/lib/types";

export function useOrgManagement(onReload: () => void) {
  const [addOrgOpen, setAddOrgOpen] = React.useState(false);
  const [selectedOrg, setSelectedOrg] = React.useState<Organization | null>(null);
  const [orgDetailTab, setOrgDetailTab] = React.useState<"overview" | "teams" | "edit">("overview");

  // Create form state
  const [newOrgName, setNewOrgName] = React.useState("");
  const [newOrgCode, setNewOrgCode] = React.useState("");
  const [newOrgTokenLimit, setNewOrgTokenLimit] = React.useState(10000000);

  // Edit form state
  const [editOrgName, setEditOrgName] = React.useState("");
  const [editOrgCode, setEditOrgCode] = React.useState("");
  const [editOrgTokenLimit, setEditOrgTokenLimit] = React.useState(10000000);

  const openEditOrg = (org: Organization) => {
    setSelectedOrg(org);
    setEditOrgName(org.name);
    setEditOrgCode(org.code || "");
    setEditOrgTokenLimit(org.tokenLimit);
    setOrgDetailTab("overview");
  };

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOrgName.trim()) {
      toast.error("لطفاً نام سازمان را وارد نمایید.");
      return;
    }
    try {
      await createOrganization({
        name: newOrgName.trim(),
        code: newOrgCode.trim() || undefined,
        tokenLimit: Number(newOrgTokenLimit) || 10000000,
      });
      toast.success(`سازمان «${newOrgName}» با موفقیت افزوده شد.`);
      setAddOrgOpen(false);
      setNewOrgName("");
      setNewOrgCode("");
      setNewOrgTokenLimit(10000000);
      onReload();
    } catch {
      toast.error("خطا در ایجاد سازمان جدید.");
    }
  };

  const handleSaveEditOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrg || !editOrgName.trim()) return;

    try {
      await updateOrganization(selectedOrg.id, {
        name: editOrgName.trim(),
        code: editOrgCode.trim() || undefined,
        tokenLimit: Number(editOrgTokenLimit),
      });
      toast.success("مشخصات سازمان به‌روزرسانی شد.");
      setSelectedOrg(null);
      onReload();
    } catch {
      toast.error("خطا در ویرایش اطلاعات سازمان.");
    }
  };

  const handleDeleteOrg = async (orgId: string) => {
    try {
      await deleteOrganization(orgId);
      toast.success("سازمان با موفقیت حذف گردید.");
      if (selectedOrg?.id === orgId) {
        setSelectedOrg(null);
      }
      onReload();
    } catch {
      toast.error("خطا در حذف سازمان.");
    }
  };

  return {
    addOrgOpen,
    setAddOrgOpen,
    selectedOrg,
    setSelectedOrg,
    orgDetailTab,
    setOrgDetailTab,
    newOrgName,
    setNewOrgName,
    newOrgCode,
    setNewOrgCode,
    newOrgTokenLimit,
    setNewOrgTokenLimit,
    editOrgName,
    setEditOrgName,
    editOrgCode,
    setEditOrgCode,
    editOrgTokenLimit,
    setEditOrgTokenLimit,
    openEditOrg,
    handleCreateOrg,
    handleSaveEditOrg,
    handleDeleteOrg,
  };
}
