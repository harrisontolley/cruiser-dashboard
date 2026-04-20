"use client";

import { useEffect, useState } from "react";
import { Command } from "cmdk";
import { useTheme } from "next-themes";
import {
  Dataset,
  ALL_CATEGORIES,
  CATEGORY_BG_CLASSES,
} from "@/lib/data/types";
import { formatBytes } from "@/lib/utils";
import { useCopyToClipboard } from "@/hooks/use-copy-to-clipboard";
import {
  Search,
  Database,
  Map,
  BarChart3,
  Layers,
  Copy,
  Check,
  Moon,
  Sun,
  ArrowRight,
  Command as CommandIcon,
} from "lucide-react";

interface CommandPaletteProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  datasets: Dataset[];
  onDatasetSelect: (dataset: Dataset) => void;
}

const SECTIONS: { id: string; label: string; icon: React.ReactNode }[] = [
  { id: "section-stats", label: "Stats overview", icon: <BarChart3 className="h-3.5 w-3.5" /> },
  { id: "section-map", label: "Coverage map", icon: <Map className="h-3.5 w-3.5" /> },
  { id: "section-grid", label: "All datasets", icon: <Database className="h-3.5 w-3.5" /> },
  { id: "section-analytics", label: "Analytics", icon: <Layers className="h-3.5 w-3.5" /> },
];

export function CommandPalette({
  open,
  setOpen,
  datasets,
  onDatasetSelect,
}: CommandPaletteProps) {
  const [search, setSearch] = useState("");
  const { theme, setTheme } = useTheme();
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const { copy } = useCopyToClipboard();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen(!open);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, setOpen]);

  useEffect(() => {
    if (!open) setSearch("");
  }, [open]);

  const handleSelectDataset = (dataset: Dataset) => {
    onDatasetSelect(dataset);
    setOpen(false);
  };

  const handleSectionJump = (sectionId: string) => {
    const el = document.getElementById(sectionId);
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
    setOpen(false);
  };

  const handleCopyS3 = async (dataset: Dataset) => {
    if (!dataset.s3Url) return;
    await copy(dataset.s3Url);
    setCopiedId(dataset.id);
    window.setTimeout(() => setCopiedId(null), 1400);
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center px-4 pt-[14vh] bg-black/60 backdrop-blur-md"
      onClick={() => setOpen(false)}
    >
      <Command
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-xl overflow-hidden rounded-xl bg-card ring-1 ring-white/[0.08] shadow-2xl"
        shouldFilter={true}
        loop
      >
        <div className="flex items-center gap-3 border-b border-white/[0.06] px-4 py-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <Command.Input
            value={search}
            onValueChange={setSearch}
            placeholder="Search datasets, jump to section, run action..."
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/70 outline-none"
            autoFocus
          />
          <kbd className="hidden sm:inline-flex items-center gap-1 rounded border border-white/[0.06] bg-white/[0.02] px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
            ESC
          </kbd>
        </div>

        <Command.List className="max-h-[60vh] overflow-y-auto py-2">
          <Command.Empty className="px-4 py-8 text-center text-xs text-muted-foreground">
            No matches.
          </Command.Empty>

          <Command.Group
            heading="Jump to"
            className="px-2 [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.2em] [&_[cmdk-group-heading]]:text-muted-foreground"
          >
            {SECTIONS.map((s) => (
              <Command.Item
                key={s.id}
                value={`jump-${s.label}`}
                onSelect={() => handleSectionJump(s.id)}
                className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-foreground/90 cursor-pointer aria-selected:bg-white/[0.05] aria-selected:text-foreground transition-colors"
              >
                <span className="text-muted-foreground">{s.icon}</span>
                <span>{s.label}</span>
                <ArrowRight className="ml-auto h-3 w-3 text-muted-foreground/50" />
              </Command.Item>
            ))}
          </Command.Group>

          <Command.Group
            heading="Datasets"
            className="px-2 mt-2 [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.2em] [&_[cmdk-group-heading]]:text-muted-foreground"
          >
            {datasets.map((d) => {
              const catLabel =
                ALL_CATEGORIES.find((c) => c.value === d.category)?.label ?? d.category;
              return (
                <Command.Item
                  key={d.id}
                  value={`${d.name} ${d.tags?.join(" ") ?? ""} ${d.region} ${catLabel}`}
                  onSelect={() => handleSelectDataset(d)}
                  className="flex items-center gap-3 rounded-md px-3 py-2 text-sm cursor-pointer aria-selected:bg-white/[0.05] transition-colors group"
                >
                  <Database className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className="text-foreground truncate">{d.name}</span>
                      <span
                        className={`font-mono text-[9px] uppercase tracking-wider rounded px-1 py-px shrink-0 ${
                          d.stage === "raw"
                            ? "bg-orange-500/15 text-orange-400"
                            : "bg-emerald-500/15 text-emerald-400"
                        }`}
                      >
                        {d.stage === "raw" ? "RAW" : "PROC"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-mono">
                      <span
                        className={`px-1 py-px rounded ${CATEGORY_BG_CLASSES[d.category]}`}
                      >
                        {catLabel}
                      </span>
                      <span>{formatBytes(d.sizeBytes)}</span>
                    </div>
                  </div>
                  {d.s3Url && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCopyS3(d);
                      }}
                      aria-label="Copy S3 path"
                      className="ml-auto flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] text-muted-foreground hover:text-foreground hover:bg-white/[0.05] transition-colors"
                    >
                      {copiedId === d.id ? (
                        <>
                          <Check className="h-3 w-3 text-emerald-400" />
                          <span className="text-emerald-400">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="h-3 w-3" />
                          <span>S3</span>
                        </>
                      )}
                    </button>
                  )}
                </Command.Item>
              );
            })}
          </Command.Group>

          <Command.Group
            heading="Settings"
            className="px-2 mt-2 [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.2em] [&_[cmdk-group-heading]]:text-muted-foreground"
          >
            <Command.Item
              value="toggle-theme"
              onSelect={() => {
                setTheme(theme === "dark" ? "light" : "dark");
                setOpen(false);
              }}
              className="flex items-center gap-3 rounded-md px-3 py-2 text-sm cursor-pointer aria-selected:bg-white/[0.05] transition-colors"
            >
              <span className="text-muted-foreground">
                {theme === "dark" ? (
                  <Sun className="h-3.5 w-3.5" />
                ) : (
                  <Moon className="h-3.5 w-3.5" />
                )}
              </span>
              <span className="text-foreground/90">
                Toggle theme — {theme === "dark" ? "light" : "dark"} mode
              </span>
            </Command.Item>
          </Command.Group>
        </Command.List>

        <div className="flex items-center justify-between border-t border-white/[0.06] px-4 py-2 text-[10px] text-muted-foreground">
          <div className="flex items-center gap-2">
            <CommandIcon className="h-3 w-3" />
            <span>DataCruiser</span>
          </div>
          <div className="flex items-center gap-3">
            <span>
              <kbd className="font-mono">↑↓</kbd> navigate
            </span>
            <span>
              <kbd className="font-mono">↵</kbd> select
            </span>
          </div>
        </div>
      </Command>
    </div>
  );
}
