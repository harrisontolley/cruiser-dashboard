"use client";

import { Database, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { ViewMode } from "@/lib/data/types";
import { cn } from "@/lib/utils";

const VIEW_OPTIONS: { value: ViewMode; label: string }[] = [
  { value: "all", label: "All" },
  { value: "raw", label: "Raw" },
  { value: "processed", label: "Processed" },
];

export function Header({
  datasetCount,
  viewMode,
  onViewModeChange,
}: {
  datasetCount?: number;
  viewMode?: ViewMode;
  onViewModeChange?: (mode: ViewMode) => void;
}) {
  const { theme, setTheme } = useTheme();

  return (
    <motion.header
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="sticky top-0 z-50 border-b border-white/[0.06] bg-background/60 backdrop-blur-2xl backdrop-saturate-150"
    >
      <div className="mx-auto flex h-14 max-w-[1400px] items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/20">
            <Database className="h-4 w-4" />
            <span className="pulse-dot absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-emerald-400 ring-2 ring-background" />
          </div>
          <div className="flex items-baseline gap-2">
            <h1 className="text-sm font-semibold tracking-tight">DataCruiser</h1>
            <span className="hidden sm:inline text-xs font-mono text-muted-foreground uppercase tracking-widest">
              Catalogue
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Stage Toggle */}
          {viewMode && onViewModeChange && (
            <div className="flex items-center rounded-full bg-card/50 p-0.5 ring-1 ring-white/[0.06]">
              {VIEW_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => onViewModeChange(opt.value)}
                  className={cn(
                    "relative rounded-full px-3 py-1 text-xs font-medium transition-all duration-200",
                    viewMode === opt.value
                      ? "bg-primary/15 text-primary ring-1 ring-primary/20"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}

          <div className="hidden sm:flex items-center gap-2 rounded-full bg-card/50 px-3 py-1 ring-1 ring-white/[0.06]">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            <span className="text-xs font-mono text-muted-foreground">
              {datasetCount ?? 0} datasets connected
            </span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="h-8 w-8 rounded-lg"
          >
            <Sun className="h-3.5 w-3.5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-3.5 w-3.5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            <span className="sr-only">Toggle theme</span>
          </Button>
        </div>
      </div>
    </motion.header>
  );
}
