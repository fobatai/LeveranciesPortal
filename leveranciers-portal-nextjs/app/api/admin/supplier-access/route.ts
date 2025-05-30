import { NextResponse, NextRequest } from "next/server";
import prisma from "@/lib/db";
import { withAdminAuth } from "@/lib/authHelpers";
import { JsonValue } from "@prisma/client/runtime/library"; // Import for type safety

interface JobData {
  Vendor?: {
    Name?: string; // For context
    ObjectContacts?: {
      Employee?: {
        EmailAddress?: string;
      };
    };
  };
}

interface SupplierInfo {
  email: string;
  vendorName?: string;
  jobCount: number;
}

export const GET = withAdminAuth(async (req: NextRequest) => {
  try {
    const jobs = await prisma.jobsCache.findMany({
      select: {
        data: true, // Select only the JSON data field
      },
    });

    const supplierEmailMap = new Map<string, { vendorNames: Set<string>; jobCount: number }>();

    jobs.forEach((job) => {
      const jobData = job.data as JsonValue as JobData; // Cast to known structure
      const email = jobData?.Vendor?.ObjectContacts?.Employee?.EmailAddress;
      const vendorName = jobData?.Vendor?.Name;

      if (email) {
        if (supplierEmailMap.has(email)) {
          const current = supplierEmailMap.get(email)!;
          current.jobCount += 1;
          if (vendorName) {
            current.vendorNames.add(vendorName);
          }
        } else {
          const vendorNames = new Set<string>();
          if (vendorName) {
            vendorNames.add(vendorName);
          }
          supplierEmailMap.set(email, { vendorNames, jobCount: 1 });
        }
      }
    });

    const supplierAccessInfo: SupplierInfo[] = [];
    supplierEmailMap.forEach(({ vendorNames, jobCount }, email) => {
      supplierAccessInfo.push({
        email,
        vendorName: vendorNames.size > 0 ? Array.from(vendorNames).join(", ") : "N/A", // Consolidate vendor names
        jobCount,
      });
    });
    
    // Sort by email for consistent output
    supplierAccessInfo.sort((a, b) => a.email.localeCompare(b.email));

    return NextResponse.json(supplierAccessInfo);
  } catch (error) {
    console.error("Error fetching supplier access overview:", error);
    return NextResponse.json({ message: "Internal Server Error" }, { status: 500 });
  }
});
