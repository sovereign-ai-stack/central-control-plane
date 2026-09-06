import * as React from "react";
import Image from "next/image";

export function BrandLogoFull({ className = "w-36 h-auto" }: { className?: string }) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <div className="relative size-9 rounded-xl overflow-hidden shadow-lg shadow-brand-cyan/20 border border-brand-cyan/30 shrink-0">
        <Image
          src="/logo.png"
          alt="Sovereign AI Logo"
          fill
          sizes="36px"
          className="object-cover"
          priority
        />
      </div>
      <div className="flex flex-col text-start leading-tight">
        <div className="flex items-center gap-1 font-extrabold text-sm tracking-wider text-foreground">
          <span>SOVEREIGN</span>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-mint to-brand-cyan">AI</span>
        </div>
        <span className="text-[8px] font-bold tracking-widest text-muted-foreground uppercase">ENTERPRISE PLATFORM</span>
      </div>
    </div>
  );
}

export function BrandLogoIcon({ className = "size-7" }: { className?: string }) {
  return (
    <div className={`relative rounded-lg overflow-hidden shadow-md shadow-brand-cyan/20 border border-brand-cyan/30 shrink-0 ${className}`}>
      <Image
        src="/logo.png"
        alt="Sovereign AI Icon"
        fill
        sizes="28px"
        className="object-cover"
        priority
      />
    </div>
  );
}

// Aliases
export const SovereignLogoFull = BrandLogoFull;
export const SovereignLogoIcon = BrandLogoIcon;
