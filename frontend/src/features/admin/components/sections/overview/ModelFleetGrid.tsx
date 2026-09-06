"use client";

import * as React from "react";
import { ArrowLeft, Cpu } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AdminSection } from "../../../types";

interface ModelFleetGridProps {
  isSuperAdmin: boolean;
  models?: any[];
  onSelectSection?: (section: AdminSection) => void;
}

export function ModelFleetGrid({
  isSuperAdmin,
  models = [],
  onSelectSection,
}: ModelFleetGridProps) {
  return (
    <Card className="bg-surface-raised border-border/40">
      <CardHeader className="pb-3 border-b border-border/30">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold text-on-surface flex items-center gap-2">
            <Cpu className="size-4 text-brand-cyan" />
            <span>ناوگان مدل‌های فعال و نگاشت نقش‌های سیستمی (Active Model Fleet)</span>
          </CardTitle>
          {onSelectSection && isSuperAdmin && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onSelectSection("models")}
              className="text-xs h-7 px-2 border-border/40 text-brand-cyan hover:bg-brand-cyan/10 cursor-pointer"
            >
              <span>مدیریت مدل‌ها</span>
              <ArrowLeft className="size-3 mr-1" />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {/* General Model */}
          <div className="p-3.5 rounded-xl bg-surface-container/40 border border-emerald-500/30 space-y-2">
            <div className="flex items-center justify-between">
              <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 text-[10px] font-mono">
                general-model
              </Badge>
              <div className="flex items-center gap-1">
                <span className="size-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span className="text-[10px] text-emerald-400 font-bold">آماده</span>
              </div>
            </div>
            <div className="font-bold text-xs text-on-surface">Qwen 2.5 3B / 7B Instruct</div>
            <p className="text-[10.5px] text-on-surface-variant leading-normal">
              مدل پیش‌فرض گفتگو، بازنویسی متون، احوالپرسی و پاسخ به پرسش‌های عمومی فارسی.
            </p>
          </div>

          {/* Coding Model */}
          <div className="p-3.5 rounded-xl bg-surface-container/40 border border-brand-cyan/30 space-y-2">
            <div className="flex items-center justify-between">
              <Badge className="bg-brand-cyan/20 text-brand-cyan border-brand-cyan/30 text-[10px] font-mono">
                coding-model
              </Badge>
              <div className="flex items-center gap-1">
                <span className="size-1.5 rounded-full bg-brand-cyan animate-pulse"></span>
                <span className="text-[10px] text-brand-cyan font-bold">آماده</span>
              </div>
            </div>
            <div className="font-bold text-xs text-on-surface">DeepSeek Coder / Qwen Coder</div>
            <p className="text-[10.5px] text-on-surface-variant leading-normal">
              تخصصی برای تولید کدهای پایتون، کوئری‌های دیتابیس، دیباگ و بررسی سینتکس.
            </p>
          </div>

          {/* Reasoning Model */}
          <div className="p-3.5 rounded-xl bg-surface-container/40 border border-purple-500/30 space-y-2">
            <div className="flex items-center justify-between">
              <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/30 text-[10px] font-mono">
                reasoning-model
              </Badge>
              <div className="flex items-center gap-1">
                <span className="size-1.5 rounded-full bg-purple-400 animate-pulse"></span>
                <span className="text-[10px] text-purple-400 font-bold">آماده</span>
              </div>
            </div>
            <div className="font-bold text-xs text-on-surface">DeepSeek-R1 Distill 1.5B / 7B</div>
            <p className="text-[10.5px] text-on-surface-variant leading-normal">
              استدلال چندمرحله‌ای، تحلیل منطقی و مسائل پیچیده ریاضی با تگ تفکر (&lt;think&gt;).
            </p>
          </div>

          {/* RAG Vector Embedding */}
          <div className="p-3.5 rounded-xl bg-surface-container/40 border border-amber-500/30 space-y-2">
            <div className="flex items-center justify-between">
              <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30 text-[10px] font-mono">
                rag-model
              </Badge>
              <div className="flex items-center gap-1">
                <span className="size-1.5 rounded-full bg-amber-400 animate-pulse"></span>
                <span className="text-[10px] text-amber-400 font-bold">متصل</span>
              </div>
            </div>
            <div className="font-bold text-xs text-on-surface">BAAI / BGE-M3 Multilingual</div>
            <p className="text-[10.5px] text-on-surface-variant leading-normal">
              تولید امبدینگ‌های چندزبانه ۱۰۲۴ بُعدی و جستجوی شباهت معنایی اسناد سازمانی.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
