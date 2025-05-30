"use client";

import { useEffect, useState } from "react";
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
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { useToast } from "@/components/ui/use-toast"; // Import useToast
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
import { ErpSystemForm, ErpSystemFormValues, erpSystemFormSchema } from "@/components/admin/erp-systems/ErpSystemForm";
import { toast } from "@/components/ui/use-toast"; // Assuming toast is set up, or use a simple alert
import { PlusCircle, Edit, Trash2, MoreHorizontal, AlertTriangle } from "lucide-react";
import { Klant } from "@prisma/client"; // Prisma type for ERP System
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";

// Define the shape of Klant excluding api_key for client-side display
type DisplayKlant = Omit<Klant, "api_key">;

export default function ErpSystemsPage() {
  const { toast } = useToast(); // Get the toast function
  const [erpSystems, setErpSystems] = useState<DisplayKlant[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedErpSystem, setSelectedErpSystem] = useState<DisplayKlant | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchErpSystems = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/admin/erp-systems");
      if (!response.ok) {
        throw new Error(`Failed to fetch ERP systems: ${response.statusText}`);
      }
      const data = await response.json();
      setErpSystems(data);
    } catch (err: any) {
      setError(err.message);
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchErpSystems();
  }, []);

  const handleAddSubmit = async (values: ErpSystemFormValues) => {
    if (!values.api_key || values.api_key.trim() === "") {
        toast({ title: "Validation Error", description: "API Key is required to create an ERP system.", variant: "destructive" });
        return;
    }
    setIsSubmitting(true);
    try {
      const response = await fetch("/api/admin/erp-systems", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || "Failed to create ERP system");
      }
      toast({ title: "Success", description: "ERP system created successfully." });
      fetchErpSystems(); // Refresh data
      setIsAddDialogOpen(false);
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditSubmit = async (values: ErpSystemFormValues) => {
    if (!selectedErpSystem) return;
    setIsSubmitting(true);
    try {
      const response = await fetch(`/api/admin/erp-systems/${selectedErpSystem.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || "Failed to update ERP system");
      }
      toast({ title: "Success", description: "ERP system updated successfully." });
      fetchErpSystems(); // Refresh data
      setIsEditDialogOpen(false);
      setSelectedErpSystem(null);
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!selectedErpSystem) return;
    setIsSubmitting(true);
    try {
      const response = await fetch(`/api/admin/erp-systems/${selectedErpSystem.id}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || "Failed to delete ERP system");
      }
      toast({ title: "Success", description: "ERP system deleted successfully." });
      fetchErpSystems(); // Refresh data
      setIsDeleteDialogOpen(false);
      setSelectedErpSystem(null);
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setIsSubmitting(false);
    }
  };

  const openEditDialog = (erpSystem: DisplayKlant) => {
    setSelectedErpSystem(erpSystem);
    setIsEditDialogOpen(true);
  };

  const openDeleteDialog = (erpSystem: DisplayKlant) => {
    setSelectedErpSystem(erpSystem);
    setIsDeleteDialogOpen(true);
  };

  if (isLoading && erpSystems.length === 0) {
    return (
      <AdminPageLayout title="Manage ERP Systems">
        <div className="space-y-4">
          <Skeleton className="h-10 w-1/4" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      </AdminPageLayout>
    );
  }
  
  if (error && erpSystems.length === 0) {
    return (
      <AdminPageLayout title="Manage ERP Systems">
        <div className="flex flex-col items-center justify-center h-64">
          <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
          <p className="text-xl text-destructive">Error loading ERP Systems.</p>
          <p className="text-sm text-muted-foreground">{error}</p>
          <Button onClick={fetchErpSystems} variant="outline" className="mt-4">Try Again</Button>
        </div>
      </AdminPageLayout>
    );
  }


  return (
    <AdminPageLayout title="Manage ERP Systems">
      <div className="flex justify-end mb-4">
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <PlusCircle className="mr-2 h-4 w-4" /> Add ERP System
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[480px]">
            <DialogHeader>
              <DialogTitle>Add New ERP System</DialogTitle>
              <DialogDescription>
                Fill in the details for the new ERP system. API key is required.
              </DialogDescription>
            </DialogHeader>
            <ErpSystemForm 
                onSubmit={handleAddSubmit} 
                isLoading={isSubmitting}
                isEditMode={false}
            />
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <Table>
          <TableCaption>{erpSystems.length === 0 ? "No ERP systems found." : "A list of configured ERP systems."}</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Domain</TableHead>
              <TableHead>Created At</TableHead>
              <TableHead className="text-right w-[100px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {erpSystems.map((system) => (
              <TableRow key={system.id}>
                <TableCell className="font-medium">{system.naam}</TableCell>
                <TableCell>{system.domein}</TableCell>
                <TableCell>{new Date(system.createdAt).toLocaleDateString()}</TableCell>
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
                      <DropdownMenuItem onClick={() => openEditDialog(system)}>
                        <Edit className="mr-2 h-4 w-4" /> Edit
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={() => openDeleteDialog(system)} className="text-destructive focus:text-destructive focus:bg-destructive/10">
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

      {/* Edit Dialog */}
      {selectedErpSystem && (
        <Dialog open={isEditDialogOpen} onOpenChange={(isOpen) => { if(!isOpen) setSelectedErpSystem(null); setIsEditDialogOpen(isOpen);}}>
          <DialogContent className="sm:max-w-[480px]">
            <DialogHeader>
              <DialogTitle>Edit ERP System: {selectedErpSystem.naam}</DialogTitle>
              <DialogDescription>
                Update the details for this ERP system. Leave API key blank to keep it unchanged.
              </DialogDescription>
            </DialogHeader>
            <ErpSystemForm
              onSubmit={handleEditSubmit}
              defaultValues={selectedErpSystem}
              isLoading={isSubmitting}
              isEditMode={true}
            />
          </DialogContent>
        </Dialog>
      )}

      {/* Delete Confirmation Dialog */}
      {selectedErpSystem && (
        <AlertDialog open={isDeleteDialogOpen} onOpenChange={(isOpen) => { if(!isOpen) setSelectedErpSystem(null); setIsDeleteDialogOpen(isOpen);}}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
              <AlertDialogDescription>
                This action cannot be undone. This will permanently delete the ERP system &quot;{selectedErpSystem.naam}&quot; 
                and all associated data (status mappings, job cache).
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={isSubmitting}>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleDeleteConfirm} disabled={isSubmitting} className="bg-destructive hover:bg-destructive/90 text-destructive-foreground">
                {isSubmitting ? "Deleting..." : "Yes, delete system"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </AdminPageLayout>
  );
}
