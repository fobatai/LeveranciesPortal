import { NextResponse, NextRequest } from "next/server";
import prisma from "@/lib/db";
import { withAuth, getAuthenticatedUser } from "@/lib/authHelpers";
import { JsonValue } from "@prisma/client/runtime/library";

// Define expected structure of the 'data' field in JobsCache for type safety
interface JobCacheData {
  Vendor?: {
    ObjectContacts?: {
      Employee?: { EmailAddress?: string } | { EmailAddress?: string }[]; // Can be single or array
    };
  };
  // Add other fields from 'data' that you might need to access directly
}


export const GET = withAuth(async (req: NextRequest) => {
  const user = await getAuthenticatedUser(req);

  if (!user || !user.email) {
    // This should technically be caught by withAuth, but defensive check for email
    return NextResponse.json({ message: "User email not found in session." }, { status: 401 });
  }
  const userEmail = user.email;

  try {
    const allJobs = await prisma.jobsCache.findMany({
      include: {
        klant: true, // Include related Klant details
      },
    });

    // Filter jobs in application code because querying JSON fields for a specific email
    // within an array or nested structure is complex and not universally supported in Prisma for all DBs.
    // For SQLite, direct JSON path queries are limited.
    const supplierJobs = allJobs.filter(job => {
      const data = job.data as JobCacheData; // Type assertion
      const contacts = data?.Vendor?.ObjectContacts?.Employee;
      if (contacts) {
        if (Array.isArray(contacts)) {
          return contacts.some(contact => contact?.EmailAddress === userEmail);
        } else {
          return contacts?.EmailAddress === userEmail;
        }
      }
      return false;
    });

    if (supplierJobs.length === 0) {
      return NextResponse.json([]); // Return empty array if no jobs found
    }

    // Fetch status mappings for all relevant klant_ids and voortgang_statuses
    const klantIds = [...new Set(supplierJobs.map(job => job.klant_id))];
    const voortgangStatuses = [...new Set(supplierJobs.map(job => job.voortgang_status))];
    
    const statusMappings = await prisma.statusToewijzing.findMany({
      where: {
        klant_id: { in: klantIds },
        van_status: { in: voortgangStatuses },
      },
    });

    // Create a map for quick lookup: "klantId-van_status" -> "naar_status"
    const mappingMap = new Map<string, string>();
    statusMappings.forEach(m => {
      mappingMap.set(`${m.klant_id}-${m.van_status}`, m.naar_status);
    });

    const resultJobs = supplierJobs.map(job => {
      const { api_key, ...klantDetailsWithoutApiKey } = job.klant; // Exclude api_key
      const naar_status = mappingMap.get(`${job.klant_id}-${job.voortgang_status}`);
      
      return {
        id: job.id,
        omschrijving: job.omschrijving,
        apparatuur_omschrijving: job.apparatuur_omschrijving,
        processfunctie_omschrijving: job.processfunctie_omschrijving,
        voortgang_status: job.voortgang_status,
        klant_naam: klantDetailsWithoutApiKey.naam, // Add klant_naam
        klant_domein: klantDetailsWithoutApiKey.domein, // Needed for context, not for API key
        naar_status: naar_status || null, // Mapped status
        // Do NOT include job.data or full job.klant in the final response unless necessary and sanitized
      };
    });

    return NextResponse.json(resultJobs);

  } catch (error) {
    console.error("Error fetching supplier jobs:", error);
    return NextResponse.json({ message: "Internal Server Error" }, { status: 500 });
  }
});
