"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AuthenticatedPageLayout from "../AuthenticatedPageLayout";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableCaption,
} from "@/components/ui/table";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import { AlertTriangle, Briefcase, ExternalLink, CheckCircle2, Zap } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

interface SupplierJob {
  id: string;
  omschrijving: string;
  apparatuur_omschrijving: string | null;
  processfunctie_omschrijving: string | null;
  voortgang_status: string;
  klant_naam: string;
  klant_domein: string;
  naar_status: string | null; // Mapped status
}

export default function SupplierDashboardPage() {
  const { toast } = useToast();
  const [jobs, setJobs] = useState<SupplierJob[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSupplierJobs = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/supplier/jobs");
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || `Failed to fetch supplier jobs: ${response.statusText}`);
      }
      const data = await response.json();
      setJobs(data);
    } catch (err: any) {
      setError(err.message);
      toast({ title: "Error Loading Jobs", description: err.message, variant: "destructive" });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSupplierJobs();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  // toast is stable, fetchSupplierJobs is not memoized but effect runs once.

  if (isLoading) {
    return (
      <AuthenticatedPageLayout title="My Dashboard - Assigned Jobs">
        <div className="space-y-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      </AuthenticatedPageLayout>
    );
  }

  if (error) {
    return (
      <AuthenticatedPageLayout title="My Dashboard - Assigned Jobs">
        <Card className="w-full">
          <CardHeader>
            <CardTitle className="flex items-center text-destructive">
              <AlertTriangle className="mr-2 h-6 w-6" /> Error Loading Jobs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p>{error}</p>
            <Button onClick={fetchSupplierJobs} variant="outline" className="mt-4">
              Try Again
            </Button>
          </CardContent>
        </Card>
      </AuthenticatedPageLayout>
    );
  }
  
  return (
    <AuthenticatedPageLayout title="My Dashboard - Assigned Jobs">
      {jobs.length === 0 ? (
        <Card className="w-full text-center">
            <CardHeader>
                <CardTitle className="flex items-center justify-center">
                    <Briefcase className="mr-2 h-6 w-6 text-muted-foreground" /> No Assigned Jobs
                </CardTitle>
            </CardHeader>
            <CardContent>
                <p className="text-muted-foreground">You currently have no jobs assigned to you, or there was an issue fetching them.</p>
                <p className="text-sm text-muted-foreground mt-1">If you believe this is an error, please contact support or try again later.</p>
                <Button onClick={fetchSupplierJobs} variant="outline" className="mt-6">
                    Refresh Jobs
                </Button>
            </CardContent>
        </Card>
      ) : (
        <Card>
            <CardHeader>
                <CardTitle>Assigned Jobs</CardTitle>
                <CardDescription>Overview of jobs assigned to you. Actionable jobs have a target status and an update button.</CardDescription>
            </CardHeader>
            <CardContent>
                <Table>
                    <TableCaption>A list of your assigned jobs.</TableCaption>
                    <TableHeader>
                    <TableRow>
                        <TableHead>Job ID</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead>Customer</TableHead>
                        <TableHead>Current ERP Status</TableHead>
                        <TableHead>Target Portal Status</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                    </TableHeader>
                    <TableBody>
                    {jobs.map((job) => (
                        <TableRow key={job.id}>
                        <TableCell className="font-mono text-xs">{job.id}</TableCell>
                        <TableCell className="font-medium max-w-xs truncate" title={job.omschrijving}>{job.omschrijving}</TableCell>
                        <TableCell>{job.klant_naam}</TableCell>
                        <TableCell>{job.voortgang_status}</TableCell>
                        <TableCell>
                            {job.naar_status ? (
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                                    {job.naar_status}
                                </span>
                            ) : (
                                <span className="text-xs text-muted-foreground italic">No action mapped</span>
                            )}
                        </TableCell>
                        <TableCell className="text-right">
                            {job.naar_status ? (
                            <Button asChild variant="default" size="sm">
                                <Link href={`/dashboard/jobs/${job.id}`}>
                                    <Zap className="mr-1.5 h-4 w-4" /> Update Job
                                </Link>
                            </Button>
                            ) : (
                            <Button variant="outline" size="sm" disabled>
                                No Action
                            </Button>
                            )}
                        </TableCell>
                        </TableRow>
                    ))}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
      )}
    </AuthenticatedPageLayout>
  );
}
