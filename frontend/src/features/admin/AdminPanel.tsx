"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft, Loader2, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { AdminHeader } from "./components/AdminHeader";
import { AdminNav } from "./components/AdminNav";
import { CreateOrgDialog } from "./components/dialogs/CreateOrgDialog";
import { CreateTeamDialog } from "./components/dialogs/CreateTeamDialog";
import { OrgDetailDialog } from "./components/dialogs/OrgDetailDialog";
import { TeamDetailDialog } from "./components/dialogs/TeamDetailDialog";
import { UploadDocDialog } from "./components/dialogs/UploadDocDialog";
import { UserDialog } from "./components/dialogs/UserDialog";
import { KnowledgeSection } from "./components/sections/KnowledgeSection";
import { LimitsSection } from "./components/sections/LimitsSection";
import { ModelsSection } from "./components/sections/ModelsSection";
import { OrganizationsSection } from "./components/sections/OrganizationsSection";
import { OverviewSection } from "./components/sections/OverviewSection";
import { TeamsSection } from "./components/sections/TeamsSection";
import { UsersSection } from "./components/sections/UsersSection";
import { useAdminData } from "./hooks/useAdminData";
import { useDocManagement } from "./hooks/useDocManagement";
import { useOrgManagement } from "./hooks/useOrgManagement";
import { useTeamManagement } from "./hooks/useTeamManagement";
import { useUserManagement } from "./hooks/useUserManagement";
import type { AdminSection } from "./types";

import { AuthScreen } from "@/components/auth/auth-screen";

export function AdminPanel() {
  const [activeSection, setActiveSection] = React.useState<AdminSection>("overview");
  const [mobileNavOpen, setMobileNavOpen] = React.useState(false);

  // 1. Core Data Hook
  const {
    currentUser,
    loading,
    refreshing,
    dashboard,
    organizations,
    teams,
    users,
    documents,
    models,
    loadData,
  } = useAdminData();

  // 2. Entity Management Hooks
  const orgMgmt = useOrgManagement(loadData);
  const teamMgmt = useTeamManagement(loadData);
  const userMgmt = useUserManagement(loadData);
  const docMgmt = useDocManagement(loadData);

  // 3. Confirm Dialog State
  const [confirmState, setConfirmState] = React.useState<{
    open: boolean;
    title: string;
    description: string;
    onConfirm: () => void;
  }>({
    open: false,
    title: "",
    description: "",
    onConfirm: () => {},
  });

  const confirmDelete = (title: string, description: string, onConfirm: () => void) => {
    setConfirmState({
      open: true,
      title,
      description,
      onConfirm,
    });
  };

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-canvas text-on-surface" dir="rtl">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="size-8 text-brand-cyan animate-spin" />
          <div className="text-xs font-semibold text-on-surface-variant">در حال بارگذاری پنل مدیریت سازمانی...</div>
        </div>
      </div>
    );
  }

  // 1. Not signed in: show Login Screen
  if (!currentUser) {
    return (
      <AuthScreen
        language="fa"
        onAuthenticated={() => {
          void loadData(true);
        }}
      />
    );
  }

  // 2. Signed in but standard user without admin rights: show Access Denied
  if (currentUser.role === "user") {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-canvas text-on-surface p-4" dir="rtl">
        <div className="flex flex-col items-center gap-4 max-w-md w-full p-6 bg-surface-raised border border-border/40 rounded-2xl text-center shadow-lg">
          <div className="size-12 rounded-full bg-destructive/15 text-destructive flex items-center justify-center">
            <Shield className="size-6" />
          </div>
          <div>
            <h2 className="text-base font-bold text-on-surface">دسترسی غیرمجاز به پنل مدیریت</h2>
            <p className="text-xs text-on-surface-variant mt-2 leading-relaxed">
              حساب کاربری شما دارای سطح دسترسی مدیریت نیست. لطفاً برای دسترسی به این بخش با حساب مدیر وارد شوید.
            </p>
          </div>
          <Button
            asChild
            variant="default"
            className="bg-brand-cyan hover:bg-brand-cyan/90 text-surface font-semibold text-xs rounded-xl px-5 mt-2"
          >
            <Link href="/">
              <ArrowLeft className="size-4 ms-1.5 rotate-180" />
              بازگشت به صفحه چت
            </Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full bg-canvas text-on-surface overflow-hidden font-sans select-none" dir="rtl">
      {/* DESKTOP SIDEBAR */}
      <div className="hidden md:block">
        <AdminNav
          activeSection={activeSection}
          onSelectSection={setActiveSection}
          currentUser={currentUser}
        />
      </div>

      {/* MOBILE SIDEBAR SHEET */}
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="right" className="p-0 w-64 bg-surface-raised border-border/40">
          <AdminNav
            activeSection={activeSection}
            onSelectSection={setActiveSection}
            currentUser={currentUser}
            onCloseMobile={() => setMobileNavOpen(false)}
          />
        </SheetContent>
      </Sheet>

      {/* MAIN CONTENT AREA */}
      <div className="flex flex-1 flex-col h-full overflow-hidden">
        <AdminHeader
          currentUser={currentUser}
          refreshing={refreshing}
          onRefresh={() => loadData(true)}
          onOpenMobileNav={() => setMobileNavOpen(true)}
        />

        <main className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8 space-y-6">
          {activeSection === "overview" && (
            <OverviewSection
              dashboard={dashboard}
              currentUser={currentUser}
              organizations={organizations}
              teams={teams}
              users={users}
              documents={documents}
              models={models}
              onSelectSection={setActiveSection}
              onRefresh={() => loadData(true)}
            />
          )}

          {activeSection === "organizations" && (
            <OrganizationsSection
              organizations={organizations}
              onOpenAddOrg={() => orgMgmt.setAddOrgOpen(true)}
              onOpenDetail={orgMgmt.openEditOrg}
            />
          )}

          {activeSection === "teams" && (
            <TeamsSection
              teams={teams}
              onOpenAddTeam={() => teamMgmt.setAddTeamOpen(true)}
              onOpenDetail={teamMgmt.openEditTeam}
            />
          )}

          {activeSection === "users" && (
            <UsersSection
              users={users}
              organizations={organizations}
              teams={teams}
              userSearch={userMgmt.userSearch}
              onUserSearchChange={userMgmt.setUserSearch}
              userFilterRole={userMgmt.userFilterRole}
              onUserFilterRoleChange={userMgmt.setUserFilterRole}
              userFilterOrg={userMgmt.userFilterOrg}
              onUserFilterOrgChange={userMgmt.setUserFilterOrg}
              userFilterTeam={userMgmt.userFilterTeam}
              onUserFilterTeamChange={userMgmt.setUserFilterTeam}
              onOpenAddUser={() => userMgmt.setAddUserOpen(true)}
              onOpenEditUser={userMgmt.openEditUser}
              onToggleUserActive={userMgmt.handleToggleUserActive}
              onDeleteUser={(userId) =>
                confirmDelete(
                  "حذف حساب کاربر",
                  "آیا از حذف این حساب کاربری اطمینان دارید؟ این عملیات غیرقابل بازگشت است.",
                  () => userMgmt.handleDeleteUser(userId)
                )
              }
            />
          )}

          {activeSection === "knowledge" && (
            <KnowledgeSection
              documents={documents}
              onOpenAddDoc={() => docMgmt.setAddDocOpen(true)}
              onDeleteDoc={(docId) =>
                confirmDelete(
                  "حذف سند از پایگاه دانش",
                  "آیا از حذف این سند و بردار‌های مربوط به آن از Weaviate اطمینان دارید؟",
                  () => docMgmt.handleDeleteDocument(docId)
                )
              }
            />
          )}

          {activeSection === "models" && currentUser?.role === "super_admin" && <ModelsSection />}

          {activeSection === "limits" && <LimitsSection dashboard={dashboard} />}
        </main>
      </div>

      {/* DIALOGS */}
      <CreateOrgDialog
        open={orgMgmt.addOrgOpen}
        onOpenChange={orgMgmt.setAddOrgOpen}
        name={orgMgmt.newOrgName}
        onNameChange={orgMgmt.setNewOrgName}
        code={orgMgmt.newOrgCode}
        onCodeChange={orgMgmt.setNewOrgCode}
        tokenLimit={orgMgmt.newOrgTokenLimit}
        onTokenLimitChange={orgMgmt.setNewOrgTokenLimit}
        onSubmit={orgMgmt.handleCreateOrg}
      />

      <OrgDetailDialog
        org={orgMgmt.selectedOrg}
        open={Boolean(orgMgmt.selectedOrg)}
        onOpenChange={(open) => !open && orgMgmt.setSelectedOrg(null)}
        tab={orgMgmt.orgDetailTab}
        onTabChange={orgMgmt.setOrgDetailTab}
        teams={teams}
        editName={orgMgmt.editOrgName}
        onEditNameChange={orgMgmt.setEditOrgName}
        editCode={orgMgmt.editOrgCode}
        onEditCodeChange={orgMgmt.setEditOrgCode}
        editTokenLimit={orgMgmt.editOrgTokenLimit}
        onEditTokenLimitChange={orgMgmt.setEditOrgTokenLimit}
        onSave={orgMgmt.handleSaveEditOrg}
        onDelete={(orgId) =>
          confirmDelete(
            "حذف کامل سازمان",
            "آیا از حذف سازمان و تمام تیم‌ها و اعضای زیرمجموعه آن اطمینان دارید؟",
            () => orgMgmt.handleDeleteOrg(orgId)
          )
        }
      />

      <CreateTeamDialog
        open={teamMgmt.addTeamOpen}
        onOpenChange={teamMgmt.setAddTeamOpen}
        name={teamMgmt.newTeamName}
        onNameChange={teamMgmt.setNewTeamName}
        orgId={teamMgmt.newTeamOrgId}
        onOrgIdChange={teamMgmt.setNewTeamOrgId}
        tokenLimit={teamMgmt.newTeamTokenLimit}
        onTokenLimitChange={teamMgmt.setNewTeamTokenLimit}
        rpm={teamMgmt.newTeamRpm}
        onRpmChange={teamMgmt.setNewTeamRpm}
        organizations={organizations}
        onSubmit={teamMgmt.handleCreateTeam}
      />

      <TeamDetailDialog
        team={teamMgmt.selectedTeam}
        open={Boolean(teamMgmt.selectedTeam)}
        onOpenChange={(open) => !open && teamMgmt.setSelectedTeam(null)}
        tab={teamMgmt.teamDetailTab}
        onTabChange={teamMgmt.setTeamDetailTab}
        members={users}
        documents={documents}
        editName={teamMgmt.editTeamName}
        onEditNameChange={teamMgmt.setEditTeamName}
        editTokenLimit={teamMgmt.editTeamTokenLimit}
        onEditTokenLimitChange={teamMgmt.setEditTeamTokenLimit}
        editRpm={teamMgmt.editTeamRpm}
        onEditRpmChange={teamMgmt.setEditTeamRpm}
        editTpm={teamMgmt.editTeamTpm}
        onEditTpmChange={teamMgmt.setEditTeamTpm}
        onSave={teamMgmt.handleSaveEditTeam}
        onDelete={(teamId) =>
          confirmDelete(
            "حذف تیم سازمانی",
            "آیا از حذف تیم و بازنشانی منابع اعضای آن مطمئن هستید؟",
            () => teamMgmt.handleDeleteTeam(teamId)
          )
        }
      />

      <UserDialog
        mode="create"
        open={userMgmt.addUserOpen}
        onOpenChange={userMgmt.setAddUserOpen}
        name={userMgmt.newUserName}
        onNameChange={userMgmt.setNewUserName}
        email={userMgmt.newUserEmail}
        onEmailChange={userMgmt.setNewUserEmail}
        password={userMgmt.newUserPassword}
        onPasswordChange={userMgmt.setNewUserPassword}
        role={userMgmt.newUserRole}
        onRoleChange={userMgmt.setNewUserRole}
        orgId={userMgmt.newUserOrgId}
        onOrgIdChange={userMgmt.setNewUserOrgId}
        teamId={userMgmt.newUserTeamId}
        onTeamIdChange={userMgmt.setNewUserTeamId}
        tokenLimit={userMgmt.newUserTokenLimit}
        onTokenLimitChange={userMgmt.setNewUserTokenLimit}
        organizations={organizations}
        teams={teams}
        currentUserRole={currentUser?.role}
        onSubmit={userMgmt.handleCreateUser}
      />

      <UserDialog
        mode="edit"
        open={userMgmt.editUserOpen}
        onOpenChange={userMgmt.setEditUserOpen}
        name={userMgmt.editUserName}
        onNameChange={userMgmt.setEditUserName}
        email={userMgmt.editUserEmail}
        password={userMgmt.editUserPassword}
        onPasswordChange={userMgmt.setEditUserPassword}
        role={userMgmt.editUserRole}
        onRoleChange={userMgmt.setEditUserRole}
        orgId={userMgmt.editUserOrgId}
        onOrgIdChange={userMgmt.setEditUserOrgId}
        teamId={userMgmt.editUserTeamId}
        onTeamIdChange={userMgmt.setEditUserTeamId}
        tokenLimit={userMgmt.editUserTokenLimit}
        onTokenLimitChange={userMgmt.setEditUserTokenLimit}
        isActive={userMgmt.editUserIsActive}
        onIsActiveChange={userMgmt.setEditUserIsActive}
        organizations={organizations}
        teams={teams}
        currentUserRole={currentUser?.role}
        onSubmit={userMgmt.handleSaveEditUser}
      />

      <UploadDocDialog
        open={docMgmt.addDocOpen}
        onOpenChange={docMgmt.setAddDocOpen}
        docMode={docMgmt.docMode}
        onDocModeChange={docMgmt.setDocMode}
        file={docMgmt.uploadFile}
        onFileChange={docMgmt.setUploadFile}
        textTitle={docMgmt.textTitle}
        onTextTitleChange={docMgmt.setTextTitle}
        textContent={docMgmt.textContent}
        onTextContentChange={docMgmt.setTextContent}
        orgId={docMgmt.uploadDocOrgId}
        onOrgIdChange={docMgmt.setUploadDocOrgId}
        teamId={docMgmt.uploadDocTeamId}
        onTeamIdChange={docMgmt.setUploadDocTeamId}
        uploading={docMgmt.uploadingDoc}
        stageText={docMgmt.uploadStageText}
        organizations={organizations}
        teams={teams}
        currentUserOrgId={currentUser?.organizationId}
        currentUserTeamId={currentUser?.teamId}
        currentUserRole={currentUser?.role}
        onSubmit={docMgmt.handleUploadDocument}
      />

      <ConfirmDialog
        open={confirmState.open}
        onOpenChange={(open) => setConfirmState((s) => ({ ...s, open }))}
        title={confirmState.title}
        description={confirmState.description}
        confirmText="بله، حذف شود"
        cancelText="انصراف"
        variant="destructive"
        onConfirm={() => {
          confirmState.onConfirm();
          setConfirmState((s) => ({ ...s, open: false }));
        }}
      />
    </div>
  );
}
