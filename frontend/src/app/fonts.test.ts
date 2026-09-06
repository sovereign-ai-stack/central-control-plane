import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";
import { yekanBakh, iranSansMono } from "./fonts";

describe("Local Fonts Verification (T007)", () => {
  const fontsDir = path.resolve(__dirname, "../assets/fonts");

  it("should have all 7 Yekan Bakh font weight files present locally", () => {
    const requiredFiles = [
      "YekanBakh-Thin-100.woff2",
      "YekanBakh-Light-300.woff2",
      "YekanBakh-Regular-400.woff2",
      "YekanBakh-SemiBold-600.woff2",
      "YekanBakh-Bold-700.woff2",
      "YekanBakh-ExtraBold-800.woff2",
      "YekanBakh-Black-900.woff2",
    ];

    for (const file of requiredFiles) {
      const filePath = path.join(fontsDir, file);
      expect(fs.existsSync(filePath), `Missing font file: ${file}`).toBe(true);
      const stat = fs.statSync(filePath);
      expect(stat.size).toBeGreaterThan(1000);
    }
  });

  it("should have IRANSans Mono font file present locally", () => {
    const filePath = path.join(fontsDir, "IRANSans-MonoSpacedNum-Light-300.woff");
    expect(fs.existsSync(filePath)).toBe(true);
    const stat = fs.statSync(filePath);
    expect(stat.size).toBeGreaterThan(1000);
  });

  it("should export correct CSS variable names for fonts", () => {
    expect(yekanBakh.variable).toBe("--font-yekan-bakh");
    expect(iranSansMono.variable).toBe("--font-iransans-mono");
  });

  it("should have zero remote font references in CSS and layout", () => {
    const globalsCssPath = path.resolve(__dirname, "./globals.css");
    const globalsCss = fs.readFileSync(globalsCssPath, "utf-8");

    expect(globalsCss).not.toContain("fonts.googleapis.com");
    expect(globalsCss).not.toContain("fonts.gstatic.com");
    expect(globalsCss).not.toContain("cdn.jsdelivr.net");
    expect(globalsCss).not.toContain("unpkg.com");
  });
});
