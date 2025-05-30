import { NextResponse, NextRequest } from "next/server";
import prisma from "@/lib/db";
import { withAuth, getAuthenticatedUser } from "@/lib/authHelpers";
import { updateErpJobStatus, ErpApiError } from "@/lib/erpService"; // Import ERP service
// import { JsonValue } from "@prisma/client/runtime/library"; // May not be needed if JobCacheData is well-defined

interface RouteParams {
  params: {
    jobId: string;
  };
}

interface JobCacheData {
  Vendor?: {
    ObjectContacts?: {
      Employee?: { EmailAddress?: string } | { EmailAddress?: string }[];
    };
  };
}

// Helper function to verify user authorization for a job
async function isUserAuthorizedForJob(jobId: string, userEmail: string): Promise<boolean> {
  const job = await prisma.jobsCache.findUnique({ where: { id: jobId } });
  if (!job) return false;

  const data = job.data as JobCacheData;
  const contacts = data?.Vendor?.ObjectContacts?.Employee;
  if (contacts) {
    if (Array.isArray(contacts)) {
      return contacts.some(contact => contact?.EmailAddress === userEmail);
    } else {
      return contacts?.EmailAddress === userEmail;
    }
  }
  return false;
}

export const PATCH = withAuth(async (req: NextRequest, { params }: RouteParams) => {
  const { jobId } = params;
  const user = await getAuthenticatedUser(req);

  if (!user || !user.email) {
    return NextResponse.json({ message: "User email not found in session." }, { status: 401 });
  }

  try {
    const isAuthorized = await isUserAuthorizedForJob(jobId, user.email);
    if (!isAuthorized) {
      return NextResponse.json({ message: "Forbidden: You are not authorized to update this job." }, { status: 403 });
    }

    const body = await req.json();
    const { feedbackText, newProgressStatus } = body; // image_files_base64_array handled separately

    if (!newProgressStatus) {
      return NextResponse.json({ message: "Missing newProgressStatus in request body." }, { status: 400 });
    }

    const job = await prisma.jobsCache.findUnique({
      where: { id: jobId },
      include: { klant: true },
    });

    if (!job) {
      return NextResponse.json({ message: "Job not found in cache." }, { status: 404 });
    }

    const { klant } = job;
    if (!klant || !klant.domein || !klant.api_key) {
      return NextResponse.json({ message: "ERP system configuration missing for this job." }, { status: 500 });
    }
    
    // --- External API Call to ERP ---
    const erpPayload = {
      ProgressStatus: newProgressStatus,
      StatusCompletedDate: new Date().toISOString(), // Current UTC time
      FeedbackText: feedbackText || undefined, // erpService will handle undefined
    };

    try {
      console.log("Calling ERP API via erpService.updateErpJobStatus for job:", jobId);
      const erpResponseData = await updateErpJobStatus(klant.domein, klant.api_key, jobId, erpPayload);
      console.log("ERP API Success (updateErpJobStatus):", erpResponseData);
    } catch (error) {
      console.error(`ERP API Error via erpService for job ${jobId}:`, error);
      if (error instanceof ErpApiError) {
        return NextResponse.json({ message: `Failed to update job status in ERP: ${error.message}`, erpError: error.erpError }, { status: error.status });
      }
      // Generic error if not ErpApiError
      return NextResponse.json({ message: "Failed to update job status in ERP due to an unexpected error." }, { status: 500 });
    }
    
    // --- Update JobsCache locally ---
    const updatedJobInCache = await prisma.jobsCache.update({
      where: { id: jobId },
      data: {
        voortgang_status: newProgressStatus,
        // Optionally update `data` field if it stores feedbackText or other relevant info
        // data: { ...job.data, FeedbackText: feedbackText } // Example, ensure type safety
        updatedAt: new Date(),
      },
    });

    return NextResponse.json({ message: "Job status updated successfully.", job: updatedJobInCache });

  } catch (error: any) {
    console.error(`Error updating job status for job ID ${jobId}:`, error);
    // No specific check for "ERP system configuration missing" here as it's caught before erpService call
    // or would be part of a more generic error if it happened unexpectedly.
    return NextResponse.json({ message: "Internal Server Error while processing job update." }, { status: 500 });
  }
});
