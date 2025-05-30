"use client";

import { useEffect, useState, useCallback } from "react";
import AdminPageLayout from "../AdminPageLayout";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StatusMappingForm, StatusMappingFormValues } from "@/components/admin/status-mappings/StatusMappingForm";
import { useToast } from "@/components/ui/use-toast";
import { PlusCircle, Edit, Trash2, MoreHorizontal, AlertTriangle, ListFilter } from "lucide-react";
import { Klant, StatusToewijzing } from "@prisma/client";
import { Skeleton } from "@/components/ui/skeleton";

type DisplayKlant = Omit<Klant, "api_key">;

export default function StatusMappingsPage() {
  const { toast } = useToast();
  const [erpSystems, setErpSystems] = useState<DisplayKlant[]>([]);
  const [selectedKlantId, setSelectedKlantId] = useState<string | null>(null);
  const [statusMappings, setStatusMappings] = useState<StatusToewijzing[]>([]);
  
  const [isLoadingErps, setIsLoadingErps] = useState(true);
  const [isLoadingMappings, setIsLoadingMappings] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedMapping, setSelectedMapping] = useState<StatusToewijzing | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchErpSystems = useCallback(async () => {
    setIsLoadingErps(true);
    try {
      const response = await fetch("/api/admin/erp-systems");
      if (!response.ok) throw new Error("Failed to fetch ERP systems");
      const data = await response.json();
      setErpSystems(data);
      if (data.length > 0 && !selectedKlantId) {
        // setSelectedKlantId(data[0].id.toString()); // Auto-select first ERP
      }
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
      setError(err.message);
    } finally {
      setIsLoadingErps(false);
    }
  }, [toast, selectedKlantId]);

  const fetchStatusMappings = useCallback(async (klantId: string) => {
    if (!klantId) {
      setStatusMappings([]);
      return;
    }
    setIsLoadingMappings(true);
    setError(null);
    try {
      const response = await fetch(`/api/admin/status-mappings?klant_id=${klantId}`);
      if (!response.ok) throw new Error("Failed to fetch status mappings");
      const data = await response.json();
      setStatusMappings(data);
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
      setError(err.message); // Set error for mappings loading
    } finally {
      setIsLoadingMappings(false);
    }
  }, [toast]);

  useEffect(() => {
    fetchErpSystems();
  }, [fetchErpSystems]);

  useEffect(() => {
    if (selectedKlantId) {
      fetchStatusMappings(selectedKlantId);
    } else {
      setStatusMappings([]); // Clear mappings if no Klant is selected
    }
  }, [selectedKlantId, fetchStatusMappings]);

  const handleAddSubmit = async (values: StatusMappingFormValues) => {
    if (!selectedKlantId) {
      toast({ title: "Error", description: "Please select an ERP system first.", variant: "destructive" });
      return;
    }
    setIsSubmitting(true);
    try {
      const response = await fetch("/api/admin/status-mappings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...values, klant_id: parseInt(selectedKlantId) }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || "Failed to create status mapping");
      }
      toast({ title: "Success", description: "Status mapping created." });
      fetchStatusMappings(selectedKlantId);
      setIsAddDialogOpen(false);
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditSubmit = async (values: StatusMappingFormValues) => {
    if (!selectedMapping || !selectedKlantId) return;
    setIsSubmitting(true);
    try {
      const response = await fetch(`/api/admin/status-mappings/${selectedMapping.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || "Failed to update status mapping");
      }
      toast({ title: "Success", description: "Status mapping updated." });
      fetchStatusMappings(selectedKlantId);
      setIsEditDialogOpen(false);
      setSelectedMapping(null);
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!selectedMapping || !selectedKlantId) return;
    setIsSubmitting(true);
    try {
      const response = await fetch(`/api/admin/status-mappings/${selectedMapping.id}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || "Failed to delete status mapping");
      }
      toast({ title: "Success", description: "Status mapping deleted." });
      fetchStatusMappings(selectedKlantId);
      setIsDeleteDialogOpen(false);
      setSelectedMapping(null);
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const openEditDialog = (mapping: StatusToewijzing) => {
    setSelectedMapping(mapping);
    setIsEditDialogOpen(true);
  };

  const openDeleteDialog = (mapping: StatusToewijzing) => {
    setSelectedMapping(mapping);
    setIsDeleteDialogOpen(true);
  };

  return (
    <AdminPageLayout title="Manage Status Mappings">
      <div className="mb-6 space-y-4 md:flex md:items-end md:space-x-4 md:space-y-0">
        <div className="flex-1 min-w-[200px]">
          <label htmlFor="erp-select" className="block text-sm font-medium text-muted-foreground mb-1">
            Select ERP System
          </label>
          {isLoadingErps ? (
            <Skeleton className="h-10 w-full" />
          ) : (
            <Select onValueChange={setSelectedKlantId} value={selectedKlantId || ""}>
              <SelectTrigger id="erp-select">
                <SelectValue placeholder="Select an ERP System..." />
              </SelectTrigger>
              <SelectContent>
                {erpSystems.map((erp) => (
                  <SelectItem key={erp.id} value={erp.id.toString()}>
                    {erp.naam} ({erp.domein})
                  </SelectItem>
                ))}
                {erpSystems.length === 0 && <p className="p-4 text-sm text-muted-foreground">No ERP systems found.</p>}
              </SelectContent>
            </Select>
          )}
        </div>
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogTrigger asChild>
            <Button disabled={!selectedKlantId || isLoadingErps}>
              <PlusCircle className="mr-2 h-4 w-4" /> Add Mapping
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[480px]">
            <DialogHeader>
              <DialogTitle>Add New Status Mapping</DialogTitle>
              <DialogDescription>
                Define a new status mapping for the selected ERP system.
              </DialogDescription>
            </DialogHeader>
            <StatusMappingForm onSubmit={handleAddSubmit} isLoading={isSubmitting} />
          </DialogContent>
        </Dialog>
      </div>

      {selectedKlantId && (
        isLoadingMappings ? (
          <div className="space-y-2 mt-4">
            <Skeleton className="h-10 w-1/3" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : error && statusMappings.length === 0 ? (
             <div className="flex flex-col items-center justify-center h-64 border rounded-md bg-card mt-4">
                <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
                <p className="text-xl text-destructive">Error loading status mappings.</p>
                <p className="text-sm text-muted-foreground">{error}</p>
                <Button onClick={() => fetchStatusMappings(selectedKlantId)} variant="outline" className="mt-4">Try Again</Button>
            </div>
        ) : (
          <Card className="mt-4">
            <Table>
              <TableCaption>
                {statusMappings.length === 0 ? "No status mappings found for this ERP system." : "Configured status mappings."}
              </TableCaption>
              <TableHeader>
                <TableRow>
                  <TableHead>From Status (ERP)</TableHead>
                  <TableHead>To Status (Portal)</TableHead>
                  <TableHead>Created At</TableHead>
                  <TableHead className="text-right w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {statusMappings.map((mapping) => (
                  <TableRow key={mapping.id}>
                    <TableCell className="font-medium">{mapping.van_status}</TableCell>
                    <TableCell>{mapping.naar_status}</TableCell>
                    <TableCell>{new Date(mapping.createdAt).toLocaleDateString()}</TableCell>
                    <TableCell className="text-right">
                       <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" className="h-8 w-8 p-0">
                            <span className="sr-only">Open menu</span>
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Actions</DropdownMenuLabel>
                          <DropdownMenuItem onClick={() => openEditDialog(mapping)}>
                            <Edit className="mr-2 h-4 w-4" /> Edit
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => openDeleteDialog(mapping)} className="text-destructive focus:text-destructive focus:bg-destructive/10">
                            <Trash2 className="mr-2 h-4 w-4" /> Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        )
      )}
      {!selectedKlantId && !isLoadingErps && (
        <div className="flex flex-col items-center justify-center h-64 border rounded-md bg-card mt-4">
            <ListFilter className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg text-muted-foreground">Please select an ERP system to view its status mappings.</p>
        </div>
      )}


      {/* Edit Dialog */}
      {selectedMapping && (
        <Dialog open={isEditDialogOpen} onOpenChange={(isOpen) => { if(!isOpen) setSelectedMapping(null); setIsEditDialogOpen(isOpen);}}>
          <DialogContent className="sm:max-w-[480px]">
            <DialogHeader>
              <DialogTitle>Edit Status Mapping</DialogTitle>
            </DialogHeader>
            <StatusMappingForm
              onSubmit={handleEditSubmit}
              defaultValues={selectedMapping}
              isLoading={isSubmitting}
              isEditMode={true}
            />
          </DialogContent>
        </Dialog>
      )}

      {/* Delete Confirmation Dialog */}
      {selectedMapping && (
         <AlertDialog open={isDeleteDialogOpen} onOpenChange={(isOpen) => { if(!isOpen) setSelectedMapping(null); setIsDeleteDialogOpen(isOpen);}}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
              <AlertDialogDescription>
                This action cannot be undone. This will permanently delete the status mapping
                (&quot;{selectedMapping.van_status}&quot; to &quot;{selectedMapping.naar_status}&quot;).
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={isSubmitting}>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleDeleteConfirm} disabled={isSubmitting} className="bg-destructive hover:bg-destructive/90 text-destructive-foreground">
                {isSubmitting ? "Deleting..." : "Yes, delete mapping"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </AdminPageLayout>
  );
}
