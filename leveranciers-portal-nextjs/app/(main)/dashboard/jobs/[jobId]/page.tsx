"use client";

import { useEffect, useState, FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import AuthenticatedPageLayout from "../../AuthenticatedPageLayout";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input"; // For file input
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import { AlertTriangle, ArrowLeft, Briefcase, Upload, CheckCircle, XCircle, Info, Send } from "lucide-react";
import { fileToBase64, getFileExtension } from "@/lib/fileHelpers";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

// Re-define SupplierJob interface here or import from a shared types file
interface SupplierJob {
  id: string;
  omschrijving: string;
  apparatuur_omschrijving: string | null;
  processfunctie_omschrijving: string | null;
  voortgang_status: string;
  klant_naam: string;
  klant_domein: string; // Not displayed but good to have if job object passed around
  naar_status: string | null;
}

interface ImageFile {
  id: string; // For unique key in React list
  file: File;
  base64: string;
  extension: string;
  name: string;
  previewUrl: string; // For client-side preview
  status?: "pending" | "uploading" | "success" | "error";
  errorMessage?: string;
}

const MAX_FILES = 4;
const MAX_FILE_SIZE_MB = 5; // Max 5MB per file

export default function JobDetailPage() {
  const { toast } = useToast();
  const router = useRouter();
  const params = useParams();
  const jobId = params.jobId as string;

  const [job, setJob] = useState<SupplierJob | null>(null);
  const [isLoadingJob, setIsLoadingJob] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [feedbackText, setFeedbackText] = useState("");
  const [imageFiles, setImageFiles] = useState<ImageFile[]>([]);
  
  const [isSubmittingStatus, setIsSubmittingStatus] = useState(false);
  const [isUploadingImages, setIsUploadingImages] = useState(false);

  useEffect(() => {
    const fetchJobDetails = async () => {
      if (!jobId) return;
      setIsLoadingJob(true);
      setError(null);
      try {
        // In a real app, you might have a /api/supplier/jobs/[jobId] endpoint.
        // For now, fetching all and filtering. This is not efficient for many jobs.
        const response = await fetch("/api/supplier/jobs");
        if (!response.ok) {
          throw new Error("Failed to fetch job details");
        }
        const jobs: SupplierJob[] = await response.json();
        const currentJob = jobs.find(j => j.id === jobId);
        if (currentJob) {
          setJob(currentJob);
        } else {
          throw new Error("Job not found or not assigned to you.");
        }
      } catch (err: any) {
        setError(err.message);
        toast({ title: "Error", description: `Could not load job details: ${err.message}`, variant: "destructive" });
      } finally {
        setIsLoadingJob(false);
      }
    };
    fetchJobDetails();
  }, [jobId, toast]);

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      const newFiles = Array.from(event.target.files);
      if (imageFiles.length + newFiles.length > MAX_FILES) {
        toast({ title: "Too many files", description: `You can upload a maximum of ${MAX_FILES} images.`, variant: "destructive" });
        return;
      }

      const processedFiles: ImageFile[] = [];
      for (const file of newFiles) {
        if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
            toast({ title: "File too large", description: `File "${file.name}" exceeds ${MAX_FILE_SIZE_MB}MB limit.`, variant: "destructive" });
            continue;
        }
        try {
          const base64 = await fileToBase64(file);
          const extension = getFileExtension(file.name);
          processedFiles.push({ 
            id: crypto.randomUUID(), 
            file, 
            base64, 
            extension, 
            name: file.name,
            previewUrl: URL.createObjectURL(file),
            status: "pending"
          });
        } catch (err) {
          toast({ title: "File processing error", description: `Could not process file ${file.name}.`, variant: "destructive" });
        }
      }
      setImageFiles(prev => [...prev, ...processedFiles]);
    }
  };
  
  const removeImage = (id: string) => {
    const removedFile = imageFiles.find(img => img.id === id);
    if (removedFile) {
        URL.revokeObjectURL(removedFile.previewUrl); // Clean up object URL
    }
    setImageFiles(prev => prev.filter(img => img.id !== id));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!job || !job.naar_status) {
      toast({ title: "Cannot update", description: "This job is not currently actionable or has no target status.", variant: "destructive" });
      return;
    }

    setIsSubmittingStatus(true);
    try {
      const statusResponse = await fetch(`/api/supplier/jobs/${jobId}/update-status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          feedbackText: feedbackText,
          newProgressStatus: job.naar_status, // This is the target status
        }),
      });

      if (!statusResponse.ok) {
        const errorData = await statusResponse.json();
        throw new Error(errorData.message || "Failed to update job status.");
      }
      toast({ title: "Status Updated", description: "Job status successfully updated in ERP.", variant: "success" });
      
      // If status update is successful, proceed to upload images
      if (imageFiles.length > 0) {
        setIsUploadingImages(true);
        let allImagesUploadedSuccessfully = true;
        
        for (const imgFile of imageFiles.filter(f => f.status === 'pending')) {
            setImageFiles(prev => prev.map(f => f.id === imgFile.id ? {...f, status: 'uploading'} : f));
            try {
                const imageResponse = await fetch(`/api/supplier/jobs/${jobId}/attach-image`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        imageBase64: imgFile.base64,
                        imageExtension: imgFile.extension,
                    }),
                });
                if (!imageResponse.ok) {
                    const errorData = await imageResponse.json();
                    throw new Error(errorData.message || `Failed to upload image ${imgFile.name}.`);
                }
                setImageFiles(prev => prev.map(f => f.id === imgFile.id ? {...f, status: 'success'} : f));
                toast({ title: "Image Uploaded", description: `${imgFile.name} uploaded successfully.`, variant: "success" });
            } catch (imgErr: any) {
                allImagesUploadedSuccessfully = false;
                setImageFiles(prev => prev.map(f => f.id === imgFile.id ? {...f, status: 'error', errorMessage: imgErr.message } : f));
                toast({ title: "Image Upload Failed", description: imgErr.message, variant: "destructive" });
            }
        }
        setIsUploadingImages(false);
        if (allImagesUploadedSuccessfully) {
          toast({ title: "All Done!", description: "Job status updated and all images uploaded.", variant: "success" });
          // Optionally reset form or redirect
          setImageFiles([]); // Clear uploaded files
          setFeedbackText("");
          // router.push("/dashboard"); // Or refresh current job data
        } else {
          toast({ title: "Partial Success", description: "Job status updated, but some images failed to upload. Check image statuses.", variant: "warning" });
        }
      } else {
         // No images to upload, status update was the final step
         router.push("/dashboard");
      }
      // Refresh job details if staying on page
      // fetchJobDetails(); // If not redirecting

    } catch (err: any) {
      toast({ title: "Update Failed", description: err.message, variant: "destructive" });
    } finally {
      setIsSubmittingStatus(false);
    }
  };


  if (isLoadingJob) {
    return (
      <AuthenticatedPageLayout title="Loading Job Details...">
        <Card>
            <CardHeader><Skeleton className="h-8 w-3/4" /></CardHeader>
            <CardContent className="space-y-3">
                <Skeleton className="h-5 w-1/2" />
                <Skeleton className="h-5 w-2/3" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-10 w-1/3 mt-2" />
            </CardContent>
        </Card>
      </AuthenticatedPageLayout>
    );
  }

  if (error || !job) {
    return (
      <AuthenticatedPageLayout title="Job Details">
        <Card className="w-full">
          <CardHeader>
            <CardTitle className="flex items-center text-destructive">
              <AlertTriangle className="mr-2 h-6 w-6" /> Error Loading Job
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p>{error || "Job data could not be loaded."}</p>
            <Button onClick={() => router.back()} variant="outline" className="mt-4 mr-2"><ArrowLeft className="mr-2 h-4 w-4"/> Back to Dashboard</Button>
          </CardContent>
        </Card>
      </AuthenticatedPageLayout>
    );
  }

  const isActionable = !!job.naar_status;

  return (
    <AuthenticatedPageLayout title={`Job Details: ${job.id}`}>
      <Card>
        <CardHeader>
          <div className="flex justify-between items-start">
            <div>
                <CardTitle className="flex items-center"><Briefcase className="mr-2 h-6 w-6 text-primary"/> {job.omschrijving}</CardTitle>
                <CardDescription>Job ID: {job.id} | Customer: {job.klant_naam}</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={() => router.push("/dashboard")}>
                <ArrowLeft className="mr-2 h-4 w-4"/> Back to Dashboard
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div><strong>Equipment:</strong> {job.apparatuur_omschrijving || "N/A"}</div>
            <div><strong>Process Function:</strong> {job.processfunctie_omschrijving || "N/A"}</div>
            <div><strong>Current ERP Status:</strong> <Badge variant="secondary">{job.voortgang_status}</Badge></div>
            <div><strong>Target Portal Status:</strong> 
                {isActionable ? <Badge variant="default">{job.naar_status}</Badge> : <Badge variant="outline">No action mapped</Badge>}
            </div>
          </div>

          <Separator />

          {isActionable ? (
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <Label htmlFor="feedbackText" className="text-base font-semibold">Feedback / Notes</Label>
                <Textarea
                  id="feedbackText"
                  value={feedbackText}
                  onChange={(e) => setFeedbackText(e.target.value)}
                  placeholder="Enter any feedback or notes related to this job update..."
                  rows={4}
                  className="mt-2"
                  disabled={isSubmittingStatus || isUploadingImages}
                />
              </div>

              <div>
                <Label htmlFor="imageUpload" className="text-base font-semibold">Attach Images (Max {MAX_FILES}, up to {MAX_FILE_SIZE_MB}MB each)</Label>
                <Input
                  id="imageUpload"
                  type="file"
                  multiple
                  accept="image/jpeg,image/png,image/gif"
                  onChange={handleFileChange}
                  className="mt-2"
                  disabled={isSubmittingStatus || isUploadingImages || imageFiles.length >= MAX_FILES}
                />
                {imageFiles.length > 0 && (
                  <div className="mt-4 space-y-3">
                    <Label className="text-sm font-medium">Selected files:</Label>
                    {imageFiles.map((imgFile) => (
                      <div key={imgFile.id} className="flex items-center justify-between p-2 border rounded-md bg-muted/30">
                        <div className="flex items-center gap-2 overflow-hidden">
                          <img src={imgFile.previewUrl} alt={imgFile.name} className="h-10 w-10 object-cover rounded-sm" />
                          <span className="text-xs truncate" title={imgFile.name}>{imgFile.name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                            {imgFile.status === 'pending' && <Badge variant="outline" className="text-xs">Pending</Badge>}
                            {imgFile.status === 'uploading' && <Badge variant="default" className="text-xs animate-pulse">Uploading...</Badge>}
                            {imgFile.status === 'success' && <CheckCircle className="h-4 w-4 text-green-500"/>}
                            {imgFile.status === 'error' && <XCircle className="h-4 w-4 text-destructive" title={imgFile.errorMessage}/>}
                            <Button type="button" variant="ghost" size="icon" onClick={() => removeImage(imgFile.id)} disabled={isSubmittingStatus || isUploadingImages}>
                                <XCircle className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                            </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              
              <Button type="submit" className="w-full sm:w-auto" disabled={isSubmittingStatus || isUploadingImages}>
                {isSubmittingStatus ? "Submitting Status..." : (isUploadingImages ? "Uploading Images..." : <><Send className="mr-2 h-4 w-4" /> Submit Update</>)}
              </Button>
            </form>
          ) : (
            <div className="text-center py-4">
              <Info className="mx-auto h-10 w-10 text-muted-foreground mb-2" />
              <p className="text-muted-foreground">This job does not have a mapped action for its current status (&quot;{job.voortgang_status}&quot;).</p>
              <p className="text-xs text-muted-foreground mt-1">No further actions can be taken from the portal at this time.</p>
            </div>
          )}
        </CardContent>
        <CardFooter>
            <p className="text-xs text-muted-foreground">
                If you encounter any issues, please contact support.
            </p>
        </CardFooter>
      </Card>
    </AuthenticatedPageLayout>
  );
}
