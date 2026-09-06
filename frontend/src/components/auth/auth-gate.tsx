"use client";

import * as React from "react";

import { apiFetch } from "@/lib/api";
import type { AuthResponse, AuthUser, Language } from "@/lib/types";
import { Workspace } from "@/components/shell/workspace";
import { BrandLogoIcon } from "@/components/ui/brand-logo";
import { AuthScreen } from "./auth-screen";

export interface AuthGateProps {
  initialLanguage?: Language;
}

type AuthStatus = "checking" | "signed-out" | "signed-in";

export function AuthGate({ initialLanguage = "fa" }: AuthGateProps) {
  const [status, setStatus] = React.useState<AuthStatus>("checking");
  const [user, setUser] = React.useState<AuthUser | null>(null);

  const loadUser = React.useCallback(async () => {
    try {
      const response = await apiFetch("auth/me", { cache: "no-store" });
      if (!response.ok) {
        setUser(null);
        setStatus("signed-out");
        return;
      }

      const data = (await response.json()) as AuthResponse;
      setUser(data.user);
      setStatus("signed-in");
    } catch {
      setUser(null);
      setStatus("signed-out");
    }
  }, []);

  React.useEffect(() => {
    void loadUser();
  }, [loadUser]);

  const handleLogout = React.useCallback(async () => {
    await apiFetch("auth/logout", { method: "POST" }).catch(() => undefined);
    setUser(null);
    setStatus("signed-out");
  }, []);

  if (status === "checking") {
    return <AuthLoadingScreen />;
  }

  if (!user) {
    return (
      <AuthScreen
        language={initialLanguage}
        onAuthenticated={(nextUser) => {
          setUser(nextUser);
          setStatus("signed-in");
        }}
      />
    );
  }

  return <Workspace initialLanguage={initialLanguage} user={user} onLogout={handleLogout} />;
}

function AuthLoadingScreen() {
  return (
    <main
      dir="rtl"
      className="relative flex min-h-[100dvh] items-center justify-center overflow-hidden bg-canvas px-4 text-foreground"
    >
      <div className="absolute size-80 rounded-full bg-brand-mint/10 blur-[100px]" />
      <div className="relative flex flex-col items-center gap-4 text-sm text-muted-foreground">
        <div
          role="img"
          aria-label="Sovereign AI"
          className="flex size-10 animate-pulse items-center justify-center rounded-2xl border border-brand-cyan/30 bg-brand-gradient shadow-lg shadow-brand-cyan/20"
        >
          <BrandLogoIcon className="size-6" />
        </div>
        <span>در حال آماده‌سازی دستیار هوشمند سازمانی…</span>
      </div>
    </main>
  );
}
