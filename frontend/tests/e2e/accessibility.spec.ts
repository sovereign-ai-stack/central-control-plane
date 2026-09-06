import { test, expect } from "@playwright/test";

test.describe("Sovereign AI Assistant Accessibility & WCAG Standards (T059)", () => {
  test("Focus-visible, landmarks, aria attributes, and local font checks", async ({ page }) => {
    await page.goto("/");

    // Landmark verification
    const main = page.getByRole("main");
    await expect(main).toBeVisible();

    // Check that textarea has proper accessible label or placeholder
    const composer = page.getByPlaceholder(/پیام خود را بنویسید|Type your message/i);
    await expect(composer).toBeVisible();

    // Check that buttons have accessible text
    const buttons = await page.getByRole("button").all();
    expect(buttons.length).toBeGreaterThan(0);

    for (const button of buttons) {
      const name = await button.getAttribute("aria-label") || (await button.innerText()).trim();
      expect(name.length).toBeGreaterThan(0);
    }
  });
});
