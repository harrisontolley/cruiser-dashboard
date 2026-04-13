import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Header skeleton */}
      <div className="sticky top-0 z-50 border-b border-white/[0.06] bg-background/60 backdrop-blur-2xl">
        <div className="mx-auto flex h-14 max-w-[1400px] items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <Skeleton className="h-8 w-8 rounded-lg" />
            <Skeleton className="h-4 w-28" />
          </div>
          <div className="flex items-center gap-3">
            <Skeleton className="h-7 w-40 rounded-full" />
            <Skeleton className="h-8 w-8 rounded-lg" />
          </div>
        </div>
      </div>

      <main className="flex-1">
        <div className="mx-auto max-w-[1400px] space-y-6 px-6 py-6">
          {/* Stats cards */}
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-[100px] rounded-xl" />
            ))}
          </div>

          {/* Coverage map */}
          <Skeleton className="h-[420px] rounded-xl" />

          {/* Charts row */}
          <div className="grid gap-6 lg:grid-cols-2">
            <Skeleton className="h-[300px] rounded-xl" />
            <div className="grid gap-6">
              <Skeleton className="h-[140px] rounded-xl" />
              <Skeleton className="h-[140px] rounded-xl" />
            </div>
          </div>

          {/* Growth chart */}
          <Skeleton className="h-[300px] rounded-xl" />

          {/* Dataset grid */}
          <div className="space-y-6">
            <div>
              <Skeleton className="h-5 w-24 mb-1" />
              <Skeleton className="h-3 w-52" />
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-[200px] rounded-xl" />
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
