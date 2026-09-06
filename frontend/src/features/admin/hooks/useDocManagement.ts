import * as React from "react";
import { toast } from "sonner";
import {
  createTextDocumentApi,
  deleteDocumentApi,
  uploadDocumentApi,
} from "@/api/index";

export function useDocManagement(onReload: () => void) {
  const [addDocOpen, setAddDocOpen] = React.useState(false);
  const [docMode, setDocMode] = React.useState<"file" | "text">("file");
  const [uploadFile, setUploadFile] = React.useState<File | null>(null);
  const [textTitle, setTextTitle] = React.useState("");
  const [textContent, setTextContent] = React.useState("");
  const [uploadDocOrgId, setUploadDocOrgId] = React.useState("");
  const [uploadDocTeamId, setUploadDocTeamId] = React.useState("global");
  const [uploadingDoc, setUploadingDoc] = React.useState(false);
  const [uploadStageText, setUploadStageText] = React.useState("۱. ارسال بایت‌های سند به سرور...");

  const handleUploadDocument = async (e: React.FormEvent) => {
    e.preventDefault();

    if (docMode === "file") {
      if (!uploadFile) {
        toast.error("لطفاً یک فایل (PDF، Word یا متنی) انتخاب کنید.");
        return;
      }

      try {
        setUploadingDoc(true);
        setUploadStageText("در حال ارسال سند به سرور...");

        const formData = new FormData();
        formData.append("file", uploadFile);
        if (uploadDocOrgId) formData.append("organizationId", uploadDocOrgId);
        if (uploadDocTeamId) formData.append("teamId", uploadDocTeamId);

        await uploadDocumentApi(formData);

        toast.success(`سند «${uploadFile.name}» با موفقیت ثبت شد و در پس‌زمینه در حال نمایه‌سازی برداری است.`);
        setAddDocOpen(false);
        setUploadFile(null);
        setTextTitle("");
        setTextContent("");
        setUploadDocOrgId("");
        setUploadDocTeamId("global");
        onReload();
      } catch {
        toast.error("خطا در آپلود و پردازش سند.");
      } finally {
        setUploadingDoc(false);
      }
    } else {
      if (!textTitle.trim()) {
        toast.error("لطفاً نام یا عنوان سند را وارد کنید.");
        return;
      }
      if (!textContent.trim()) {
        toast.error("لطفاً متن سند را وارد کنید.");
        return;
      }

      try {
        setUploadingDoc(true);
        setUploadStageText("در حال ذخیره و شروع قطعه‌بندی برداری متن...");

        await createTextDocumentApi({
          title: textTitle.trim(),
          content: textContent.trim(),
          organizationId: uploadDocOrgId || undefined,
          teamId: uploadDocTeamId || undefined,
        });

        toast.success(`سند متنی «${textTitle}» با موفقیت ایجاد شد و در حال نمایه‌سازی برداری است.`);
        setAddDocOpen(false);
        setUploadFile(null);
        setTextTitle("");
        setTextContent("");
        setUploadDocOrgId("");
        setUploadDocTeamId("global");
        onReload();
      } catch {
        toast.error("خطا در ثبت سند متنی.");
      } finally {
        setUploadingDoc(false);
      }
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    try {
      await deleteDocumentApi(docId);
      toast.success("سند با موفقیت از پایگاه دانش حذف شد.");
      onReload();
    } catch {
      toast.error("خطا در حذف سند.");
    }
  };

  return {
    addDocOpen,
    setAddDocOpen,
    docMode,
    setDocMode,
    uploadFile,
    setUploadFile,
    textTitle,
    setTextTitle,
    textContent,
    setTextContent,
    uploadDocOrgId,
    setUploadDocOrgId,
    uploadDocTeamId,
    setUploadDocTeamId,
    uploadingDoc,
    uploadStageText,
    handleUploadDocument,
    handleDeleteDocument,
  };
}
