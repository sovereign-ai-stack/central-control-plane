"use client";

import * as React from "react";
import { Copy, KeyRound, Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { apiFetch } from "@/lib/api";
import { useTranslation } from "@/lib/locale";
import type { Language, McpApiKey, McpApiKeyCreated, UsageLimits } from "@/lib/types";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";

export interface McpKeysSectionProps {
  isOpen: boolean;
  language: Language;
  limits: UsageLimits | null;
}

export function McpKeysSection({ isOpen, language, limits }: McpKeysSectionProps) {
  const t = useTranslation(language);
  const [keys, setKeys] = React.useState<McpApiKey[]>([]);
  const [name, setName] = React.useState("");
  const [rpm, setRpm] = React.useState("60");
  const [rps, setRps] = React.useState("5");
  const [createdToken, setCreatedToken] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [creating, setCreating] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const loadKeys = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch("auth/mcp-keys", { cache: "no-store" });
      if (!response.ok) throw new Error(await readError(response, t.account.mcpKeyUnavailable));
      const data = await response.json();
      setKeys(Array.isArray(data) ? (data as McpApiKey[]) : []);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : t.account.mcpKeyUnavailable);
    } finally {
      setLoading(false);
    }
  }, [t.account.mcpKeyUnavailable]);

  React.useEffect(() => {
    if (isOpen) void loadKeys();
  }, [isOpen, loadKeys]);

  React.useEffect(() => {
    if (!limits) return;
    setRpm(String(limits.mcpDefaultRpm));
    setRps(String(limits.mcpDefaultRps));
  }, [limits]);

  const createKey = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const cleanName = name.trim();
    if (!cleanName) return;
    const rpmValue = Number(rpm);
    const rpsValue = Number(rps);
    if (
      !Number.isInteger(rpmValue) ||
      !Number.isInteger(rpsValue) ||
      rpmValue < 1 ||
      rpsValue < 1 ||
      rpsValue > rpmValue
    ) {
      setError(t.account.mcpKeyLimitInvalid);
      return;
    }

    setCreating(true);
    setError(null);
    try {
      const response = await apiFetch("auth/mcp-keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: cleanName, rpm: rpmValue, rps: rpsValue }),
      });
      if (!response.ok) throw new Error(await readError(response, t.account.mcpKeyUnavailable));
      const created = (await response.json()) as McpApiKeyCreated;
      setKeys((current) => [created, ...current]);
      setCreatedToken(created.token);
      setName("");
      toast.success(t.account.mcpKeyCreated);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : t.account.mcpKeyUnavailable);
    } finally {
      setCreating(false);
    }
  };

  const revokeKey = async (key: McpApiKey) => {
    if (!window.confirm(`${t.account.mcpKeyRevoke}: ${key.name}?`)) return;

    const response = await apiFetch(`auth/mcp-keys/${key.id}`, { method: "DELETE" });
    if (!response.ok) {
      setError(await readError(response, t.account.mcpKeyUnavailable));
      return;
    }

    setKeys((current) =>
      current.map((item) => (item.id === key.id ? { ...item, revokedAt: new Date().toISOString() } : item))
    );
    toast.success(t.account.mcpKeyRevoked);
  };

  const copyToken = async () => {
    if (!createdToken) return;
    await navigator.clipboard.writeText(createdToken);
    toast.success(t.account.mcpKeyCopied);
  };

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        <KeyRound className="text-brand-cyan" data-icon="inline-start" />
        <span>{t.account.mcpKeys}</span>
      </div>
      <p className="text-xs leading-6 text-muted-foreground">{t.account.mcpKeysDescription}</p>

      <form onSubmit={createKey} className="flex flex-col gap-3 rounded-xl border border-border/60 bg-surface/40 p-3">
        <FieldGroup className="gap-2">
          <Field>
            <FieldLabel htmlFor="mcp-key-name" className="text-xs text-foreground">
              {t.account.mcpKeyName}
            </FieldLabel>
            <Input
              id="mcp-key-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder={t.account.mcpKeyNamePlaceholder}
              maxLength={80}
              className="h-9 border-border/70 bg-surface-container-low text-xs"
            />
            <FieldDescription className="text-[11px]">{t.account.mcpKeysDescription}</FieldDescription>
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field>
              <FieldLabel htmlFor="mcp-key-rpm" className="text-xs text-foreground">
                {t.account.mcpKeyRpm}
              </FieldLabel>
              <Input
                id="mcp-key-rpm"
                type="number"
                min={1}
                max={limits?.mcpMaxRpm}
                value={rpm}
                onChange={(event) => setRpm(event.target.value)}
                className="h-9 border-border/70 bg-surface-container-low text-xs"
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="mcp-key-rps" className="text-xs text-foreground">
                {t.account.mcpKeyRps}
              </FieldLabel>
              <Input
                id="mcp-key-rps"
                type="number"
                min={1}
                max={limits?.mcpMaxRps}
                value={rps}
                onChange={(event) => setRps(event.target.value)}
                className="h-9 border-border/70 bg-surface-container-low text-xs"
              />
            </Field>
          </div>
          <p className="text-[11px] text-muted-foreground">{t.account.mcpKeyRateDescription}</p>
        </FieldGroup>
        <Button type="submit" size="sm" disabled={creating || !name.trim()} className="w-full">
          {creating && <Loader2 className="animate-spin" data-icon="inline-start" />}
          {t.account.createMcpKey}
        </Button>
      </form>

      {createdToken && (
        <Alert className="border-brand-mint/30 bg-brand-mint/5 text-foreground">
          <AlertTitle className="text-sm">{t.account.mcpKeyCreated}</AlertTitle>
          <AlertDescription className="flex flex-col gap-3 text-xs">
            <span className="leading-5 text-muted-foreground">{t.account.mcpKeyWarning}</span>
            <div className="flex items-center gap-2 rounded-lg border border-border/60 bg-surface-container-low p-2">
              <code dir="ltr" className="min-w-0 flex-1 break-all text-[11px] text-brand-mint">
                {createdToken}
              </code>
              <Button type="button" size="icon" variant="ghost" onClick={copyToken} aria-label={t.account.mcpKeyCopy}>
                <Copy data-icon="inline-start" />
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs font-medium leading-relaxed text-destructive" role="alert">
          {error}
        </div>
      )}

      <div className="flex flex-col gap-2">
        {loading && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="animate-spin" data-icon="inline-start" />
            {t.account.usageLoading}
          </div>
        )}
        {!loading && keys.length === 0 && !error && (
          <p className="rounded-lg border border-border/60 bg-surface/40 p-3 text-xs text-muted-foreground">
            {t.account.mcpKeyListEmpty}
          </p>
        )}
        {!loading &&
          keys.map((key) => (
            <div key={key.id} className="flex items-center gap-3 rounded-lg border border-border/60 bg-surface/40 p-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate text-xs font-semibold text-foreground">{key.name}</span>
                  {key.revokedAt && <Badge variant="outline" className="text-[10px]">{t.account.mcpKeyRevokedLabel}</Badge>}
                </div>
                <code dir="ltr" className="mt-1 block truncate text-[10px] text-muted-foreground">
                  {key.prefix}…
                </code>
                <div dir="ltr" className="mt-1 text-[10px] text-brand-cyan">
                  {key.rpm} RPM · {key.rps} RPS
                </div>
              </div>
              {!key.revokedAt && (
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  onClick={() => void revokeKey(key)}
                  aria-label={t.account.mcpKeyRevoke}
                >
                  <Trash2 data-icon="inline-start" />
                </Button>
              )}
            </div>
          ))}
      </div>
    </section>
  );
}

async function readError(response: Response, fallback: string): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string };
    if (data.detail) return data.detail;
  } catch {
    // Use the localized fallback for non-JSON proxy failures.
  }
  return fallback;
}
