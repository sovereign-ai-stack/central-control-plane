import localFont from "next/font/local";

export const yekanBakh = localFont({
  src: [
    {
      path: "../assets/fonts/YekanBakh-Thin-100.woff2",
      weight: "100",
      style: "normal",
    },
    {
      path: "../assets/fonts/YekanBakh-Light-300.woff2",
      weight: "300",
      style: "normal",
    },
    {
      path: "../assets/fonts/YekanBakh-Regular-400.woff2",
      weight: "400",
      style: "normal",
    },
    {
      path: "../assets/fonts/YekanBakh-SemiBold-600.woff2",
      weight: "600",
      style: "normal",
    },
    {
      path: "../assets/fonts/YekanBakh-Bold-700.woff2",
      weight: "700",
      style: "normal",
    },
    {
      path: "../assets/fonts/YekanBakh-ExtraBold-800.woff2",
      weight: "800",
      style: "normal",
    },
    {
      path: "../assets/fonts/YekanBakh-Black-900.woff2",
      weight: "900",
      style: "normal",
    },
  ],
  variable: "--font-yekan-bakh",
  display: "swap",
  fallback: ["system-ui", "-apple-system", "sans-serif"],
});

export const iranSansMono = localFont({
  src: [
    {
      path: "../assets/fonts/IRANSans-MonoSpacedNum-Light-300.woff",
      weight: "300",
      style: "normal",
    },
  ],
  variable: "--font-iransans-mono",
  display: "swap",
  fallback: [
    "ui-monospace",
    "SFMono-Regular",
    "Menlo",
    "Monaco",
    "Consolas",
    "Liberation Mono",
    "Courier New",
    "monospace",
  ],
});
