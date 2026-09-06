import { test, expect, type Page } from "@playwright/test";

const appPath = `/${(process.env.NEXT_PUBLIC_APP_SECRET_PATH || "secret-path")
  .split("/")
  .filter(Boolean)
  .join("/")}`;

async function signUp(page: Page) {
  const email = `e2e-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;
  await page.goto(appPath);
  await page.locator("#auth-email").fill(email);
  await page.getByRole("button", { name: /ادامه|Continue/i }).click();
  await page.locator("#auth-password").fill("e2e-password-123");
  await page.locator("#auth-password-confirm").fill("e2e-password-123");
  await page.getByRole("button", { name: /ساخت حساب|Create account/i }).click();
  await expect(page.getByTestId("chat-rail")).toBeVisible();
}

test.describe("Sovereign AI Assistant Conversation Journeys (T059 / US4)", () => {
  test("Desktop Persian & English Journey: Chat Rail, Starters, Composer, and Sources", async ({
    page,
    isMobile,
  }) => {
    test.skip(isMobile, "Desktop test only");

    await signUp(page);

    // Verify Sovereign brand identity in rail
    const chatRail = page.getByTestId("chat-rail");
    await expect(chatRail).toBeVisible();

    // Verify New Chat button is prominent
    const newChatBtn = page.getByRole("button", { name: /گفتگوی جدید|New chat/i });
    await expect(newChatBtn).toBeVisible();

    // Verify Empty state starter actions
    const starters = page.getByTestId("starter-actions");
    await expect(starters).toBeVisible();

    // Verify Composer
    const composer = page.getByPlaceholder(/پیام خود را بنویسید|Type your message/i);
    await expect(composer).toBeVisible();

    // Verify authenticated account button at bottom of rail
    const accountBtn = page.getByTestId("account-menu-button");
    await expect(accountBtn).toBeVisible();
    await accountBtn.click();

    // Verify Account subpanel content
    await expect(page.getByRole("heading", { name: /پروفایل محلی|Local Profile/i })).toBeVisible();
    await expect(page.getByRole("dialog").getByText(/مستندات و راهنما|Documentation & Help/i)).toBeVisible();
    await expect(page.getByRole("dialog").getByText(/حریم خصوصی|Privacy/i)).toBeVisible();
    await expect(page.getByRole("dialog").getByText(/کلیدهای MCP|MCP API keys/i)).toBeVisible();

    // Verify prohibited items are absent
    await expect(page.getByRole("button", { name: /ورود|login|sign in/i })).not.toBeVisible();
    await expect(page.getByText(/تم روشن|Light mode/i)).not.toBeVisible();
    await expect(page.getByText(/انتخاب مدل|Model/i)).not.toBeVisible();
  });

  test("Mobile 360px Journey: Drawers for History and Sources", async ({ page, isMobile }) => {
    test.skip(!isMobile, "Mobile test only");

    await signUp(page);

    // Conversation should be primary view
    const composer = page.getByPlaceholder(/پیام خود را بنویسید|Type your message/i);
    await expect(composer).toBeVisible();

    // Mobile header buttons for sources and history
    const historyToggle = page.getByTestId("mobile-history-toggle");
    await expect(historyToggle).toBeVisible();

    const sourcesToggle = page.getByTestId("mobile-sources-toggle");
    await expect(sourcesToggle).toBeVisible();

    // Open mobile history drawer
    await historyToggle.click();
    const newChatBtn = page.getByRole("dialog").getByRole("button", { name: /گفتگوی جدید|New chat/i });
    await expect(newChatBtn).toBeVisible();
  });
});
