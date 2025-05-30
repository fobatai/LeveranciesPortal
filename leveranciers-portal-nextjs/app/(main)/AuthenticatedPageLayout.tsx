"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Skeleton } from "@/components/ui/skeleton"; // For loading state

interface AuthenticatedPageLayoutProps {
  children: React.ReactNode;
  title: string;
}

export default function AuthenticatedPageLayout({ children, title }: AuthenticatedPageLayoutProps) {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "loading") return; // Do nothing while loading
    if (!session) {
      // If not authenticated, redirect to login page
      // Pass the current path as callbackUrl to redirect back after login
      router.replace("/login?callbackUrl=" + encodeURIComponent(window.location.pathname));
    }
    // No specific role check here, just authentication.
    // Role-specific logic can be handled within the page if needed,
    // or by API routes.
  }, [session, status, router]);

  if (status === "loading" || !session) {
    // Show a loading state or a blank page while checking session and redirecting
    return (
      <div className="p-4 sm:p-6 lg:p-8">
        <Skeleton className="h-8 w-1/4 mb-4" />
        <Skeleton className="h-screen w-full" />
      </div>
    );
  }

  // User is authenticated
  return (
    <div className="p-4 sm:p-6 lg:p-8">
      <h1 className="text-2xl font-bold tracking-tight mb-6">{title}</h1>
      {children}
    </div>
  );
}
