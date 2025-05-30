"use client";

import { useEffect, useState } from "react";
import AdminPageLayout from "../AdminPageLayout";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableCaption,
} from "@/components/ui/table";
import { useToast } from "@/components/ui/use-toast";
import { AlertTriangle, Users } from "lucide-react";
import { Klant } from "@prisma/client"; // Not directly used here, but for context
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";


interface SupplierAccessInfo {
  email: string;
  vendorName?: string;
  jobCount: number;
}

export default function SupplierAccessPage() {
  const { toast } = useToast();
  const [supplierAccessList, setSupplierAccessList] = useState<SupplierAccessInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSupplierAccess = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/admin/supplier-access");
      if (!response.ok) {
        throw new Error(`Failed to fetch supplier access data: ${response.statusText}`);
      }
      const data = await response.json();
      setSupplierAccessList(data);
    } catch (err: any) {
      setError(err.message);
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSupplierAccess();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps 
  // toast is stable, fetchSupplierAccess is not memoized due to toast dependency but effect runs once.

  if (isLoading) {
    return (
      <AdminPageLayout title="Supplier Access Overview">
        <Card>
          <CardHeader>
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-4 w-1/2 mt-2" />
          </CardHeader>
          <CardContent className="space-y-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </CardContent>
        </Card>
      </AdminPageLayout>
    );
  }

  if (error) {
     return (
      <AdminPageLayout title="Supplier Access Overview">
        <div className="flex flex-col items-center justify-center h-64 border rounded-md bg-card">
          <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
          <p className="text-xl text-destructive">Error loading supplier access data.</p>
          <p className="text-sm text-muted-foreground">{error}</p>
          <Button onClick={fetchSupplierAccess} variant="outline" className="mt-4">Try Again</Button>
        </div>
      </AdminPageLayout>
    );
  }

  return (
    <AdminPageLayout title="Supplier Access Overview">
      <Card>
        <CardHeader>
            <CardTitle className="flex items-center"><Users className="mr-2 h-5 w-5" /> Supplier Access List</CardTitle>
            <CardDescription>
                This list shows unique supplier emails found in job data, along with associated vendor names and job counts.
                It indicates which suppliers might need portal access.
            </CardDescription>
        </CardHeader>
        <CardContent>
            <Table>
            <TableCaption>
                {supplierAccessList.length === 0 
                ? "No supplier access data found in job cache." 
                : "Overview of supplier emails found in job data."}
            </TableCaption>
            <TableHeader>
                <TableRow>
                <TableHead>Supplier Email</TableHead>
                <TableHead>Associated Vendor(s)</TableHead>
                <TableHead className="text-right">Job Count</TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {supplierAccessList.map((supplier) => (
                <TableRow key={supplier.email}>
                    <TableCell className="font-medium">{supplier.email}</TableCell>
                    <TableCell>{supplier.vendorName || "N/A"}</TableCell>
                    <TableCell className="text-right">{supplier.jobCount}</TableCell>
                </TableRow>
                ))}
            </TableBody>
            </Table>
        </CardContent>
      </Card>
    </AdminPageLayout>
  );
}
