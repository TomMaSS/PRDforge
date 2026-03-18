"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useSession } from "@/lib/auth-client";
import { LoadingOverlay } from "@/components/loading-overlay";

const PUBLIC_PATHS = ["/signin", "/reset"];

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { data: session, isPending } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  useEffect(() => {
    if (!isPending && !session && !isPublic) {
      router.push("/signin");
    }
  }, [session, isPending, isPublic, router]);

  if (isPending) {
    return <LoadingOverlay />;
  }

  if (!session && !isPublic) {
    return <LoadingOverlay />;
  }

  return <>{children}</>;
}
