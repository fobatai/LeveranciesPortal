import { NextResponse, NextRequest } from "next/server";
import prisma from "@/lib/db";
import { getErpJobs } from "@/lib/erpService"; // Assuming erpService is in lib
import type { SyncControl, Klant } from "@prisma/client";
import { JsonValue } from "@prisma/client/runtime/library";

// Define expected structure of an ERP Job for type safety when processing
interface ErpJob {
  Id: string; // Typically, ID from ERP is capitalized
  Description?: string;
  Equipment?: { Description?: string };
  ProcessFunction?: { Description?: string };
  ProgressStatus?: string;
  Vendor?: { Id?: string }; // Assuming Vendor.Id is the leverancier_id
  RecordChangeDate?: string; // Or whatever the change date field is named
  // Include other fields that are part of the raw job data to be stored
  [key: string]: any; // Allow other properties
}


// Helper to check CRON secret
function isValidCronSecret(req: NextRequest): boolean {
  const authHeader = req.headers.get("Authorization");
  const cronSecret = process.env.CRON_SECRET;

  if (!cronSecret) {
    console.warn("CRON_SECRET is not set in environment variables. Denying access.");
    return false;
  }
  if (authHeader && authHeader === `Bearer ${cronSecret}`) {
    return true;
  }
  // Also check for query parameter as an alternative (less secure for GET, but POST is fine)
  const secretFromQuery = req.nextUrl.searchParams.get("secret");
  if (secretFromQuery && secretFromQuery === cronSecret) {
    return true;
  }
  
  return false;
}

const SYNC_CONTROL_ID = 1; // Assuming a single row with ID 1 for sync settings

export async function POST(req: NextRequest) {
  if (!isValidCronSecret(req)) {
    return NextResponse.json({ message: "Unauthorized: Invalid CRON secret." }, { status: 401 });
  }

  let syncLog: string[] = [];
  let totalJobsProcessed = 0;
  let totalJobsUpserted = 0;
  let errorCount = 0;

  try {
    syncLog.push("Cron job triggered.");
    let syncControl = await prisma.syncControl.findUnique({ where: { id: SYNC_CONTROL_ID } });
    if (!syncControl) {
      syncControl = await prisma.syncControl.create({ data: { id: SYNC_CONTROL_ID, force_sync: true } });
      syncLog.push("SyncControl record created as it was missing.");
    }

    const now = new Date();
    const syncIntervalMs = (syncControl.sync_interval || 3600) * 1000;
    const shouldSync = 
      syncControl.force_sync || 
      !syncControl.last_sync || 
      (now.getTime() - new Date(syncControl.last_sync).getTime() > syncIntervalMs);

    if (!shouldSync) {
      syncLog.push("Sync not required at this time based on interval and force_sync flag.");
      return NextResponse.json({ message: "Sync not required at this time.", log: syncLog });
    }

    syncLog.push("Starting synchronization process...");
    const klanten = await prisma.klant.findMany({ where: { api_key: { not: null }, domein: { not: null } } });
    syncLog.push(`Found ${klanten.length} ERP systems (Klanten) to process.`);

    for (const klant of klanten) {
      syncLog.push(`Processing Klant ID: ${klant.id} (${klant.naam}).`);
      if (!klant.domein || !klant.api_key) {
        syncLog.push(`Skipping Klant ID: ${klant.id} due to missing domain or API key.`);
        errorCount++;
        continue;
      }

      try {
        // Define filter for fetching jobs. Example: only jobs changed since last sync.
        // The date format for $filter must match what the ERP API expects (e.g., ISO 8601).
        let filterQuery: string | undefined = undefined;
        if (syncControl.last_sync && !syncControl.force_sync) { // Only filter if not forced and last_sync exists
            // Example: RecordChangeDate gt 2023-01-01T00:00:00Z
            // Adjust field name 'RecordChangeDate' if different in your ERP
            const lastSyncIso = new Date(syncControl.last_sync).toISOString();
            filterQuery = `RecordChangeDate gt ${lastSyncIso}`; 
            syncLog.push(`Using filter for Klant ${klant.id}: ${filterQuery}`);
        } else {
            syncLog.push(`No specific date filter for Klant ${klant.id} (force sync or no previous sync). Fetching relevant active jobs.`);
            // Potentially a default filter for active/open jobs if fetching all is too much
            // filterQuery = "Status ne 'COMPLETED' and Status ne 'CANCELLED'"; // Example
        }
        
        const erpJobs: ErpJob[] = await getErpJobs(klant.domein, klant.api_key, {
          filter: filterQuery,
          // Important: Expand related entities needed for denormalization in JobsCache
          expand: "Vendor/ObjectContacts/Employee,Equipment,ProcessFunction", 
          // Select only necessary fields if possible to reduce payload
          // select: "Id,Description,Equipment/Description,...",
        });
        syncLog.push(`Fetched ${erpJobs.length} jobs from ERP for Klant ${klant.id}.`);
        totalJobsProcessed += erpJobs.length;

        for (const job of erpJobs) {
          const jobDataForCache = {
            id: job.Id, // Ensure this matches Prisma schema (string)
            klant_id: klant.id,
            omschrijving: job.Description || "N/A",
            apparatuur_omschrijving: job.Equipment?.Description,
            processfunctie_omschrijving: job.ProcessFunction?.Description,
            voortgang_status: job.ProgressStatus || "UNKNOWN",
            leverancier_id: job.Vendor?.Id, // Assuming Vendor.Id is the supplier ID
            wijzigingsdatum: job.RecordChangeDate ? new Date(job.RecordChangeDate) : new Date(),
            data: job as unknown as JsonValue, // Store the raw job JSON
          };

          await prisma.jobsCache.upsert({
            where: { id: job.Id },
            update: jobDataForCache,
            create: jobDataForCache,
          });
          totalJobsUpserted++;
        }
      } catch (erpError: any) {
        syncLog.push(`Error processing Klant ID ${klant.id}: ${erpError.message}`);
        errorCount++;
        // Optionally, log erpError.erpError or erpError.status if it's an ErpApiError
        if (erpError.erpError) syncLog.push(`ERP Error Details: ${JSON.stringify(erpError.erpError)}`);
      }
    }

    // Update SyncControl after processing all klanten
    await prisma.syncControl.update({
      where: { id: SYNC_CONTROL_ID },
      data: {
        last_sync: now,
        force_sync: false,
      },
    });
    syncLog.push("Synchronization process completed.");

    return NextResponse.json({
      message: "Synchronization process finished.",
      klanten_processed: klanten.length,
      total_jobs_fetched_from_erp: totalJobsProcessed,
      total_jobs_upserted_in_cache: totalJobsUpserted,
      errors: errorCount,
      log: syncLog,
    });

  } catch (error: any) {
    console.error("Cron job general error:", error);
    syncLog.push(`Fatal error during sync: ${error.message}`);
    // Attempt to update force_sync to false even if there was a major error before loop
    try {
        await prisma.syncControl.update({
            where: { id: SYNC_CONTROL_ID },
            data: { force_sync: false }, // Reset force_sync to prevent immediate re-runs on fatal error
        });
        syncLog.push("Reset force_sync flag due to fatal error.");
    } catch (dbError) {
        syncLog.push(`Could not reset force_sync flag: ${ (dbError as Error).message }`);
    }
    return NextResponse.json({ message: "Internal Server Error during sync.", error: error.message, log: syncLog }, { status: 500 });
  }
}
