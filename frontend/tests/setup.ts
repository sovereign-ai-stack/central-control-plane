import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// Mock next/font/local
vi.mock("next/font/local", () => {
  return {
    default: (options: { variable?: string; src?: unknown }) => {
      return {
        className: `className-${options.variable || "font"}`,
        variable: options.variable || "--font-mock",
        style: { fontFamily: "mock-font" },
      };
    },
  };
});
