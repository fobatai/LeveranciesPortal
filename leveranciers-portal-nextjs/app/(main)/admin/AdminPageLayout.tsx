"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Skeleton } from "@/components/ui/skeleton"; // For loading state

interface AdminPageLayoutProps {
  children: React.ReactNode;
  title: string;
}

export default function AdminPageLayout({ children, title }: AdminPageLayoutProps) {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "loading") return; // Do nothing while loading
    if (!session) {
      router.replace("/login?callbackUrl=" + encodeURIComponent(window.location.pathname));
      return;
    }
    if ((session.user as any)?.role !== "ADMIN") {
      // If not admin, redirect to a general access denied page or homepage
      // For now, redirecting to the main dashboard or supplier login might be an option
      // Or create a specific '/access-denied' page
      router.replace("/"); // Or '/unauthorized' or '/login'
      return;
    }
  }, [session, status, router]);

  if (status === "loading" || !session || (session.user as any)?.role !== "ADMIN") {
    // Show a loading state or a blank page while checking session and redirecting
    return (
      <div className="p-4 sm:p-6 lg:p-8">
        <Skeleton className="h-8 w-1/4 mb-4" />
        <Skeleton className="h-screen w-full" />
      </div>
    );
  }

  // User is authenticated and is an ADMIN
  return (
    <div className="p-4 sm:p-6 lg:p-8">
      <h1 className="text-2xl font-bold tracking-tight mb-6">{title}</h1>
      {children}
    </div>
  );
}
