import {
  S3Client,
  ListObjectsV2Command,
  PutObjectCommand,
} from "@aws-sdk/client-s3";
import { readFileSync } from "fs";
import { join } from "path";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const catalogue = JSON.parse(
  readFileSync(join(__dirname, "catalogue.json"), "utf-8")
);

const BUCKET: string = catalogue.bucket;
const REGION: string = catalogue.region;
const METADATA_KEY = "metadata/datasets.json";
const TOP_PREFIXES = ["raw/", "processed/"];

const s3 = new S3Client({ region: REGION });

// ---------------------------------------------------------------------------
// Types (mirrors src/lib/data/types.ts)
// ---------------------------------------------------------------------------

interface Dataset {
  id: string;
  name: string;
  category: string;
  region: string;
  stage: "raw" | "processed";
  pairId?: string;
  timespan?: string;
  temporalRange?: { start: string; end: string | null };
  license?: string;
  sourceUrl?: string;
  s3Url?: string;
  maintainer?: string;
  sizeBytes: number;
  fileCount?: number;
  format?: string;
  lastModified: string;
  bbox?: [number, number, number, number];
  description?: string;
  tags?: string[];
}

interface CatalogueEntry {
  name?: string;
  category?: string;
  region?: string;
  stage?: "raw" | "processed";
  pairId?: string;
  description?: string;
  bbox?: [number, number, number, number];
  tags?: string[];
  maintainer?: string;
  license?: string;
  sourceUrl?: string;
  timespan?: string;
  temporalRange?: { start: string; end: string | null };
}

interface PrefixStats {
  sizeBytes: number;
  fileCount: number;
  format: string;
  lastModified: string;
}

// ---------------------------------------------------------------------------
// S3 Helpers
// ---------------------------------------------------------------------------

/** List immediate child prefixes under a given prefix. */
async function listChildPrefixes(prefix: string): Promise<string[]> {
  const res = await s3.send(
    new ListObjectsV2Command({
      Bucket: BUCKET,
      Prefix: prefix,
      Delimiter: "/",
    })
  );
  return (res.CommonPrefixes ?? [])
    .map((p) => p.Prefix!)
    .filter(Boolean);
}

/** List all root-level files (archives) under a prefix that aren't in subfolders. */
async function listRootFiles(
  prefix: string
): Promise<{ key: string; size: number; lastModified: Date }[]> {
  const res = await s3.send(
    new ListObjectsV2Command({
      Bucket: BUCKET,
      Prefix: prefix,
      Delimiter: "/",
    })
  );
  return (res.Contents ?? [])
    .filter((o) => o.Key && o.Size && o.Size > 0)
    .map((o) => ({
      key: o.Key!,
      size: o.Size!,
      lastModified: o.LastModified!,
    }));
}

/** Paginate through all objects under a prefix and return aggregate stats. */
async function scrapePrefix(prefix: string): Promise<PrefixStats> {
  let sizeBytes = 0;
  let fileCount = 0;
  let latestDate: Date | null = null;
  const extCounts = new Map<string, number>();

  let continuationToken: string | undefined;
  do {
    const res = await s3.send(
      new ListObjectsV2Command({
        Bucket: BUCKET,
        Prefix: prefix,
        ContinuationToken: continuationToken,
      })
    );

    for (const obj of res.Contents ?? []) {
      if (!obj.Key || obj.Size === undefined) continue;
      // Skip 0-byte marker objects
      if (obj.Size === 0) continue;

      sizeBytes += obj.Size;
      fileCount += 1;

      if (obj.LastModified) {
        if (!latestDate || obj.LastModified > latestDate) {
          latestDate = obj.LastModified;
        }
      }

      // Track file extension
      const ext = obj.Key.split(".").pop()?.toLowerCase();
      if (ext && ext !== obj.Key.toLowerCase()) {
        extCounts.set(ext, (extCounts.get(ext) ?? 0) + 1);
      }
    }

    continuationToken = res.IsTruncated ? res.NextContinuationToken : undefined;
  } while (continuationToken);

  // Determine dominant format
  const FORMAT_MAP: Record<string, string> = {
    parquet: "Parquet",
    csv: "CSV",
    json: "JSON",
    nc: "NetCDF",
    netcdf: "NetCDF",
    tif: "GeoTIFF",
    tiff: "GeoTIFF",
    geojson: "GeoJSON",
    zip: "ZIP",
    gz: "GZ",
    tar: "TAR",
    png: "PNG",
    avro: "Avro",
  };

  let format = "Unknown";
  if (extCounts.size > 0) {
    const sorted = [...extCounts.entries()].sort((a, b) => b[1] - a[1]);
    const topExt = sorted[0][0];
    format = FORMAT_MAP[topExt] ?? topExt.toUpperCase();
  }

  return {
    sizeBytes,
    fileCount,
    format,
    lastModified: latestDate?.toISOString() ?? new Date().toISOString(),
  };
}

// ---------------------------------------------------------------------------
// ID generation
// ---------------------------------------------------------------------------

function prefixToId(prefix: string): string {
  return prefix
    .replace(/\/+$/, "")
    .replace(/\//g, "-")
    .replace(/[^a-z0-9-]/gi, "-")
    .toLowerCase();
}

function prefixToName(prefix: string): string {
  const parts = prefix.replace(/\/+$/, "").split("/");
  const last = parts[parts.length - 1];
  return last
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  console.log(`Scraping bucket: s3://${BUCKET}/`);
  console.log(`Top-level prefixes: ${TOP_PREFIXES.join(", ")}`);
  console.log();

  const catalogueEntries: Record<string, CatalogueEntry> = catalogue.datasets;

  // Discover all dataset prefixes
  const discoveredPrefixes: string[] = [];

  for (const topPrefix of TOP_PREFIXES) {
    const children = await listChildPrefixes(topPrefix);
    discoveredPrefixes.push(...children);

    // Also check for root-level archive files (zip, tar.gz, etc.)
    const rootFiles = await listRootFiles(topPrefix);
    for (const file of rootFiles) {
      // Treat large root-level files as individual "datasets"
      discoveredPrefixes.push(file.key);
    }
  }

  console.log(`Discovered ${discoveredPrefixes.length} prefixes/files:\n`);
  for (const p of discoveredPrefixes) {
    const inCatalogue = p in catalogueEntries;
    console.log(`  ${inCatalogue ? "[catalogued]" : "[unknown]  "} ${p}`);
  }
  console.log();

  // Scrape each prefix
  const datasets: Dataset[] = [];

  for (const prefix of discoveredPrefixes) {
    const isFile = !prefix.endsWith("/");
    process.stdout.write(`  Scraping ${prefix} ... `);

    let stats: PrefixStats;

    if (isFile) {
      // Single file — get its info from the root listing
      const rootFiles = await listRootFiles(
        prefix.substring(0, prefix.lastIndexOf("/") + 1)
      );
      const file = rootFiles.find((f) => f.key === prefix);
      if (!file) {
        console.log("SKIPPED (not found)");
        continue;
      }
      const ext = prefix.split(".").pop()?.toLowerCase() ?? "";
      const FORMAT_MAP: Record<string, string> = {
        zip: "ZIP",
        gz: "GZ",
        tar: "TAR",
      };
      stats = {
        sizeBytes: file.size,
        fileCount: 1,
        format: FORMAT_MAP[ext] ?? ext.toUpperCase(),
        lastModified: file.lastModified.toISOString(),
      };
    } else {
      stats = await scrapePrefix(prefix);
    }

    console.log(
      `${stats.fileCount} files, ${formatBytes(stats.sizeBytes)}, ${stats.format}`
    );

    const meta = catalogueEntries[prefix] ?? {};
    const id = prefixToId(prefix);

    const autoStage = prefix.startsWith("processed/") ? "processed" as const : "raw" as const;

    datasets.push({
      id,
      name: meta.name ?? prefixToName(prefix),
      category: meta.category ?? "demographics", // fallback to a valid category
      region: meta.region ?? "Unknown",
      stage: meta.stage ?? autoStage,
      pairId: meta.pairId,
      description: meta.description,
      sizeBytes: stats.sizeBytes,
      fileCount: stats.fileCount,
      format: stats.format,
      lastModified: stats.lastModified,
      s3Url: `s3://${BUCKET}/${prefix}`,
      bbox: meta.bbox,
      tags: meta.tags,
      maintainer: meta.maintainer,
      license: meta.license,
      sourceUrl: meta.sourceUrl,
      timespan: meta.timespan,
      temporalRange: meta.temporalRange,
    });
  }

  // Sort by size descending
  datasets.sort((a, b) => b.sizeBytes - a.sizeBytes);

  const output = {
    generatedAt: new Date().toISOString(),
    bucket: BUCKET,
    datasetCount: datasets.length,
    totalSizeBytes: datasets.reduce((s, d) => s + d.sizeBytes, 0),
    datasets,
  };

  console.log();
  console.log(`Total: ${datasets.length} datasets, ${formatBytes(output.totalSizeBytes)}`);
  console.log();

  // Upload to S3
  console.log(`Uploading to s3://${BUCKET}/${METADATA_KEY} ...`);
  const body = JSON.stringify(output, null, 2);

  await s3.send(
    new PutObjectCommand({
      Bucket: BUCKET,
      Key: METADATA_KEY,
      Body: body,
      ContentType: "application/json",
    })
  );

  console.log("Done!");
}

// ---------------------------------------------------------------------------
// Util
// ---------------------------------------------------------------------------

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

// ---------------------------------------------------------------------------

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
