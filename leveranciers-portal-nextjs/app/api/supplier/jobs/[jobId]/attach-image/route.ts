import { NextResponse, NextRequest } from "next/server";
import prisma from "@/lib/db";
import { withAuth, getAuthenticatedUser } from "@/lib/authHelpers";
import { attachImageToErpJob, ErpApiError } from "@/lib/erpService"; // Import ERP service
// import { JsonValue } from "@prisma/client/runtime/library"; // May not be needed

interface RouteParams {
  params: {
    jobId: string;
  };
}

interface JobCacheData { // For checking authorization
  Vendor?: {
    ObjectContacts?: {
      Employee?: { EmailAddress?: string } | { EmailAddress?: string }[];
    };
  };
}

// Helper function to verify user authorization for a job (can be refactored to a shared util)
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

export const POST = withAuth(async (req: NextRequest, { params }: RouteParams) => {
  const { jobId } = params;
  const user = await getAuthenticatedUser(req);

  if (!user || !user.email) {
    return NextResponse.json({ message: "User email not found in session." }, { status: 401 });
  }

  try {
    const isAuthorized = await isUserAuthorizedForJob(jobId, user.email);
    if (!isAuthorized) {
      return NextResponse.json({ message: "Forbidden: You are not authorized to attach images to this job." }, { status: 403 });
    }

    const body = await req.json();
    const { imageBase64, imageExtension } = body;

    if (!imageBase64 || !imageExtension) {
      return NextResponse.json({ message: "Missing imageBase64 or imageExtension in request body." }, { status: 400 });
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

    // --- External API Call to ERP for attaching image ---
    const erpPayload = {
      JobId: jobId,
      ImageFileBase64: imageBase64,
      ImageFileBase64Extension: imageExtension,
      // ApplicationElementId will be handled by erpService using the default or one passed if needed
    };

    let erpResponseData;
    try {
      console.log("Calling ERP AttachImage API via erpService for job:", jobId);
      erpResponseData = await attachImageToErpJob(klant.domein, klant.api_key, erpPayload);
      console.log("ERP API Success (attachImageToErpJob):", erpResponseData);
    } catch (error) {
      console.error(`ERP API AttachImage Error via erpService for job ${jobId}:`, error);
      if (error instanceof ErpApiError) {
        return NextResponse.json({ message: `Failed to attach image in ERP: ${error.message}`, erpError: error.erpError }, { status: error.status });
      }
      return NextResponse.json({ message: "Failed to attach image in ERP due to an unexpected error." }, { status: 500 });
    }

    // Touch the local record
    await prisma.jobsCache.update({
        where: { id: jobId },
        data: { updatedAt: new Date() } 
    });

    return NextResponse.json({ message: "Image attached successfully.", erpResponse: erpResponseData });

  } catch (error: any) {
    console.error(`Error processing image attachment for job ID ${jobId}:`, error);
    // Generic error for issues outside the direct ERP call
    return NextResponse.json({ message: "Internal Server Error while processing image attachment." }, { status: 500 });
  }
});
