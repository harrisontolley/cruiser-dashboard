"use client";

import { useCopyToClipboard } from "@/hooks/use-copy-to-clipboard";
import { Copy, Check, Terminal } from "lucide-react";
import { cn } from "@/lib/utils";

interface AccessSnippetsProps {
  s3Url: string;
  format?: string;
}

interface SnippetBlockProps {
  title: string;
  command: string;
}

function SnippetBlock({ title, command }: SnippetBlockProps) {
  const { copied, copy } = useCopyToClipboard();

  return (
    <div className="group relative">
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <Terminal className="h-2.5 w-2.5 text-muted-foreground" />
          <span className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            {title}
          </span>
        </div>
        <button
          onClick={() => copy(command)}
          aria-label={`Copy ${title} snippet`}
          className={cn(
            "flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] transition-colors",
            "text-muted-foreground hover:text-foreground hover:bg-white/[0.05]"
          )}
        >
          {copied ? (
            <>
              <Check className="h-3 w-3 text-emerald-400" />
              <span className="text-emerald-400">Copied</span>
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="overflow-x-auto rounded-md bg-background/60 ring-1 ring-white/[0.06] px-3 py-2 text-[11px] font-mono leading-relaxed text-foreground/90">
        <code>{command}</code>
      </pre>
    </div>
  );
}

export function AccessSnippets({ s3Url, format }: AccessSnippetsProps) {
  const cleanUrl = s3Url.endsWith("/") ? s3Url : `${s3Url}/`;
  const awsSync = `aws s3 sync ${cleanUrl} ./local-data/`;
  const isParquet = format?.toLowerCase().includes("parquet");
  const duckdbQuery = isParquet
    ? `SELECT * FROM read_parquet('${cleanUrl}**/*.parquet') LIMIT 100;`
    : null;

  return (
    <div className="space-y-3">
      <SnippetBlock title="AWS CLI — download" command={awsSync} />
      {duckdbQuery && <SnippetBlock title="DuckDB — query in place" command={duckdbQuery} />}
    </div>
  );
}
