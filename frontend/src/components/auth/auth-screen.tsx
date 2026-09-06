"use client";

import * as React from "react";
import { ArrowLeft, Loader2, Lock, Mail, ShieldCheck } from "lucide-react";

import { apiFetch } from "@/lib/api";
import { useTranslation } from "@/lib/locale";
import type { AuthResponse, AuthUser, Language } from "@/lib/types";
import { ChatRail } from "@/components/shell/chat-rail";
import { Composer } from "@/components/chat/composer";
import { EmptyChat } from "@/components/chat/empty-chat";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { BrandLogoFull } from "@/components/ui/brand-logo";

export interface AuthScreenProps {
  language: Language;
  onAuthenticated: (user: AuthUser) => void;
}

export function AuthScreen({ language, onAuthenticated }: AuthScreenProps) {
  const t = useTranslation(language);
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [isPending, setIsPending] = React.useState(false);

  const handleLoginSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedEmail = email.trim().toLowerCase();
    if (!normalizedEmail || !normalizedEmail.includes("@")) {
      setError(t.auth.invalidEmail || "ایمیل وارد شده نامعتبر است.");
      return;
    }
    if (!password) {
      setError("لطفاً گذرواژه خود را وارد کنید.");
      return;
    }

    setError(null);
    setIsPending(true);
    try {
      const response = await apiFetch("auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: normalizedEmail, password }),
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || "ایمیل یا گذرواژه وارد شده نادرست است.");
      }

      const data = (await response.json()) as AuthResponse;
      onAuthenticated(data.user);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "خطا در برقراری ارتباط با سرور.");
    } finally {
      setIsPending(false);
    }
  };

  const handleQuickLogin = (quickEmail: string, quickPass: string) => {
    setEmail(quickEmail);
    setPassword(quickPass);
    setError(null);
  };

  return (
    <div className="relative flex h-[100dvh] w-full overflow-hidden bg-canvas">
      {/* Background disabled shell view */}
      <div className="pointer-events-none absolute inset-0 flex select-none opacity-40 blur-[1px]">
        <ChatRail
          language={language}
          conversations={[]}
          activeConversationId={undefined}
          onSelectConversation={() => undefined}
          onNewChat={() => undefined}
          onShareConversation={() => undefined}
          onRenameConversation={() => undefined}
          onDeleteConversation={() => undefined}
          onOpenAccount={() => undefined}
          onToggleLanguage={() => undefined}
        />
        <div className="flex flex-1 flex-col">
          <EmptyChat language={language} onSelectStarter={() => undefined} />
          <Composer
            language={language}
            onSubmit={() => undefined}
            isStreaming={false}
            disabled={true}
          />
        </div>
      </div>

      {/* Central Login Modal */}
      <div className="relative z-50 flex h-full w-full items-center justify-center p-4">
        <div className="pointer-events-none absolute -left-20 top-10 size-72 rounded-full bg-brand-mint/10 blur-[120px]" />
        <div className="pointer-events-none absolute -right-20 bottom-0 size-80 rounded-full bg-brand-cyan/10 blur-[140px]" />

        <Card className="w-full max-w-md border-border/70 bg-surface/95 shadow-2xl backdrop-blur-2xl">
          <CardHeader className="flex flex-col items-center gap-2 text-center pb-2">
            <BrandLogoFull className="mb-2 w-32 h-auto" />
            <CardTitle className="text-xl font-bold tracking-tight text-foreground">
              ورود به سامانه هوش مصنوعی سازمانی
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              برای دسترسی به کلاستر و پایگاه دانش، با ایمیل سازمانی خود وارد شوید.
            </p>
          </CardHeader>

          <CardContent className="space-y-4 pt-2">
            <form onSubmit={handleLoginSubmit} className="space-y-3.5" noValidate>
              <FieldGroup className="space-y-3">
                <Field className="space-y-1.5 text-start">
                  <FieldLabel htmlFor="auth-email" className="text-xs font-semibold text-foreground">
                    ایمیل سازمانی
                  </FieldLabel>
                  <div className="relative">
                    <Mail className="absolute start-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                    <Input
                      id="auth-email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="name@organization.ir"
                      className="ps-9 h-10 text-xs font-mono bg-surface-container border-border/80 text-start"
                      dir="ltr"
                      disabled={isPending}
                      required
                    />
                  </div>
                </Field>

                <Field className="space-y-1.5 text-start">
                  <FieldLabel htmlFor="auth-password" className="text-xs font-semibold text-foreground">
                    گذرواژه
                  </FieldLabel>
                  <div className="relative">
                    <Lock className="absolute start-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                    <Input
                      id="auth-password"
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="ps-9 h-10 text-xs font-mono bg-surface-container border-border/80 text-start"
                      dir="ltr"
                      disabled={isPending}
                      required
                    />
                  </div>
                </Field>
              </FieldGroup>

              {error && (
                <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-2.5 text-xs text-destructive text-start">
                  {error}
                </div>
              )}

              <Button
                type="submit"
                disabled={isPending}
                className="w-full h-10 bg-brand-cyan hover:bg-brand-cyan/90 text-canvas font-bold text-xs shadow-lg shadow-brand-cyan/20 cursor-pointer"
              >
                {isPending ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="size-4 animate-spin" />
                    <span>در حال احراز هویت...</span>
                  </span>
                ) : (
                  <span>ورود به حساب کاربری</span>
                )}
              </Button>
            </form>
          </CardContent>

          <CardFooter className="flex flex-col gap-1 pb-4 pt-1 text-center">
            <div className="text-[11px] text-muted-foreground">
              ثبت‌نام مستقیم غیرفعال است. نام‌نویسی کاربران توسط مدیران سیستم انجام می‌گیرد.
            </div>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
