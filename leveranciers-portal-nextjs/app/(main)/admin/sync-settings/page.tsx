"use client";

import { useEffect, useState, useCallback } from "react";
import AdminPageLayout from "../AdminPageLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import { Sync, AlertTriangle, Save, Settings, Zap } from "lucide-react";
import { SyncControl } from "@prisma/client";
import { Skeleton } from "@/components/ui/skeleton";

export default function SyncSettingsPage() {
  const { toast } = useToast();
  const [syncSettings, setSyncSettings] = useState<SyncControl | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdatingInterval, setIsUpdatingInterval] = useState(false);
  const [isTriggeringSync, setIsTriggeringSync] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newSyncInterval, setNewSyncInterval] = useState<number>(3600);

  const fetchSyncSettings = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/admin/sync-control");
      if (!response.ok) {
        throw new Error(`Failed to fetch sync settings: ${response.statusText}`);
      }
      const data: SyncControl = await response.json();
      setSyncSettings(data);
      setNewSyncInterval(data.sync_interval);
    } catch (err: any) {
      setError(err.message);
      toast({ title: "Error", description: `Could not load sync settings: ${err.message}`, variant: "destructive" });
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    fetchSyncSettings();
  }, [fetchSyncSettings]);

  const handleUpdateInterval = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsUpdatingInterval(true);
    try {
      const response = await fetch("/api/admin/sync-control", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sync_interval: newSyncInterval }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || "Failed to update sync interval");
      }
      const updatedSettings = await response.json();
      setSyncSettings(updatedSettings);
      setNewSyncInterval(updatedSettings.sync_interval);
      toast({ title: "Success", description: "Sync interval updated successfully." });
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setIsUpdatingInterval(false);
    }
  };

  const handleForceSync = async () => {
    setIsTriggeringSync(true);
    try {
      const response = await fetch("/api/admin/sync-control/trigger", {
        method: "POST",
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || "Failed to trigger force sync");
      }
      const result = await response.json();
      setSyncSettings(result.syncControl); // Update local state with new sync status
      toast({ title: "Success", description: "Force sync triggered successfully. The system will sync soon." });
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setIsTriggeringSync(false);
    }
  };

  if (isLoading) {
    return (
        <AdminPageLayout title="Synchronization Settings">
            <div className="grid gap-6 md:grid-cols-2">
                <Card>
                    <CardHeader><Skeleton className="h-7 w-3/4" /></CardHeader>
                    <CardContent className="space-y-3">
                        <Skeleton className="h-5 w-1/2" />
                        <Skeleton className="h-5 w-2/3" />
                        <Skeleton className="h-5 w-1/2" />
                        <Skeleton className="h-10 w-full mt-2" />
                    </CardContent>
                </Card>
                 <Card>
                    <CardHeader><Skeleton className="h-7 w-3/4" /></CardHeader>
                    <CardContent className="space-y-3">
                        <Skeleton className="h-5 w-full" />
                        <Skeleton className="h-10 w-1/2 mt-2" />
                    </CardContent>
                </Card>
            </div>
        </AdminPageLayout>
    );
  }

  if (error || !syncSettings) {
    return (
      <AdminPageLayout title="Synchronization Settings">
         <div className="flex flex-col items-center justify-center h-64 border rounded-md bg-card">
          <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
          <p className="text-xl text-destructive">Error loading synchronization settings.</p>
          <p className="text-sm text-muted-foreground">{error || "Could not load settings."}</p>
          <Button onClick={fetchSyncSettings} variant="outline" className="mt-4">Try Again</Button>
        </div>
      </AdminPageLayout>
    );
  }

  return (
    <AdminPageLayout title="Synchronization Settings">
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center"><Settings className="mr-2 h-5 w-5" /> Sync Interval</CardTitle>
            <CardDescription>Configure how often the portal automatically syncs data with ERP systems.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleUpdateInterval} className="space-y-4">
              <div>
                <Label htmlFor="syncInterval">Sync Interval (seconds)</Label>
                <Input
                  id="syncInterval"
                  type="number"
                  value={newSyncInterval}
                  onChange={(e) => setNewSyncInterval(parseInt(e.target.value, 10))}
                  min="60" // Example: minimum 1 minute
                  required
                  className="mt-1"
                  disabled={isUpdatingInterval}
                />
                <p className="text-sm text-muted-foreground mt-1">
                  Current interval: {syncSettings.sync_interval} seconds (approx. {Math.round(syncSettings.sync_interval/60)} minutes).
                </p>
              </div>
              <Button type="submit" disabled={isUpdatingInterval || newSyncInterval === syncSettings.sync_interval}>
                {isUpdatingInterval ? <><Sync className="mr-2 h-4 w-4 animate-spin" /> Saving...</> : <><Save className="mr-2 h-4 w-4" /> Save Interval</>}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center"><Zap className="mr-2 h-5 w-5" /> Manual Sync Control</CardTitle>
            <CardDescription>Manually trigger a data synchronization cycle.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm">
                Last sync attempt: {syncSettings.last_sync ? new Date(syncSettings.last_sync).toLocaleString() : "Never"}
              </p>
              <p className={`text-sm font-medium ${syncSettings.force_sync ? 'text-orange-600' : 'text-green-600'}`}>
                Force sync requested: {syncSettings.force_sync ? "Yes (Pending)" : "No"}
              </p>
            </div>
            <Button onClick={handleForceSync} disabled={isTriggeringSync || syncSettings.force_sync} variant="outline">
              {isTriggeringSync ? <><Sync className="mr-2 h-4 w-4 animate-spin" /> Triggering...</> : "Trigger Force Sync"}
            </Button>
            {syncSettings.force_sync && (
                <p className="text-sm text-muted-foreground">
                    A manual sync is already pending. The system will process it shortly.
                </p>
            )}
          </CardContent>
        </Card>
      </div>
    </AdminPageLayout>
  );
}
