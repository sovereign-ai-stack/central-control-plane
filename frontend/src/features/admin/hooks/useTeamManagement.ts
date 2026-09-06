"use client";

import * as React from "react";
import { toast } from "sonner";
import {
  createTeam,
  deleteTeam,
  updateTeam,
} from "@/api/index";
import type { Team } from "@/lib/types";

export function useTeamManagement(onReload: () => void) {
  const [addTeamOpen, setAddTeamOpen] = React.useState(false);
  const [selectedTeam, setSelectedTeam] = React.useState<Team | null>(null);
  const [teamDetailTab, setTeamDetailTab] = React.useState<"overview" | "users" | "docs" | "edit">("overview");

  // Create form state
  const [newTeamName, setNewTeamName] = React.useState("");
  const [newTeamOrgId, setNewTeamOrgId] = React.useState("");
  const [newTeamTokenLimit, setNewTeamTokenLimit] = React.useState(2000000);
  const [newTeamRpm, setNewTeamRpm] = React.useState(100);

  // Edit form state
  const [editTeamName, setEditTeamName] = React.useState("");
  const [editTeamTokenLimit, setEditTeamTokenLimit] = React.useState(2000000);
  const [editTeamRpm, setEditTeamRpm] = React.useState(100);
  const [editTeamTpm, setEditTeamTpm] = React.useState(100000);

  const openEditTeam = (team: Team) => {
    setSelectedTeam(team);
    setEditTeamName(team.name);
    setEditTeamTokenLimit(team.tokenLimit);
    setEditTeamRpm(team.rpmLimit || 100);
    setEditTeamTpm(team.tpmLimit || 100000);
    setTeamDetailTab("overview");
  };

  const handleCreateTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTeamName.trim() || !newTeamOrgId) {
      toast.error("لطفاً نام تیم و سازمان مربوطه را انتخاب نمایید.");
      return;
    }
    try {
      await createTeam({
        name: newTeamName.trim(),
        organizationId: newTeamOrgId,
        tokenLimit: Number(newTeamTokenLimit) || 2000000,
        rpmLimit: Number(newTeamRpm) || 100,
      });
      toast.success(`تیم «${newTeamName}» با موفقیت افزوده شد.`);
      setAddTeamOpen(false);
      setNewTeamName("");
      setNewTeamOrgId("");
      setNewTeamTokenLimit(2000000);
      setNewTeamRpm(100);
      onReload();
    } catch {
      toast.error("خطا در ایجاد تیم جدید.");
    }
  };

  const handleSaveEditTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTeam || !editTeamName.trim()) return;

    try {
      await updateTeam(selectedTeam.id, {
        name: editTeamName.trim(),
        tokenLimit: Number(editTeamTokenLimit),
        rpmLimit: Number(editTeamRpm),
        tpmLimit: Number(editTeamTpm),
      });
      toast.success("مشخصات تیم به‌روزرسانی شد.");
      setSelectedTeam(null);
      onReload();
    } catch {
      toast.error("خطا در ویرایش اطلاعات تیم.");
    }
  };

  const handleDeleteTeam = async (teamId: string) => {
    try {
      await deleteTeam(teamId);
      toast.success("تیم با موفقیت حذف شد.");
      if (selectedTeam?.id === teamId) {
        setSelectedTeam(null);
      }
      onReload();
    } catch {
      toast.error("خطا در حذف تیم.");
    }
  };

  return {
    addTeamOpen,
    setAddTeamOpen,
    selectedTeam,
    setSelectedTeam,
    teamDetailTab,
    setTeamDetailTab,
    newTeamName,
    setNewTeamName,
    newTeamOrgId,
    setNewTeamOrgId,
    newTeamTokenLimit,
    setNewTeamTokenLimit,
    newTeamRpm,
    setNewTeamRpm,
    editTeamName,
    setEditTeamName,
    editTeamTokenLimit,
    setEditTeamTokenLimit,
    editTeamRpm,
    setEditTeamRpm,
    editTeamTpm,
    setEditTeamTpm,
    openEditTeam,
    handleCreateTeam,
    handleSaveEditTeam,
    handleDeleteTeam,
  };
}
