import { NextResponse, NextRequest } from "next/server";
import prisma from "@/lib/db";
import { withAdminAuth } from "@/lib/authHelpers";

const SYNC_CONTROL_ID = 1; // Assuming a single row with ID 1 for sync settings

// Helper to get or create the sync control record
async function getOrCreateSyncControl() {
  let syncControl = await prisma.syncControl.findUnique({
    where: { id: SYNC_CONTROL_ID },
  });

  if (!syncControl) {
    syncControl = await prisma.syncControl.create({
      data: {
        id: SYNC_CONTROL_ID, // Explicitly set ID if your model allows/requires it for the first record
        force_sync: false,
        sync_interval: 3600, // Default interval
      },
    });
  }
  return syncControl;
}

// GET current sync settings
export const GET = withAdminAuth(async (req: NextRequest) => {
  try {
    const syncControl = await getOrCreateSyncControl();
    return NextResponse.json(syncControl);
  } catch (error) {
    console.error("Error fetching sync control settings:", error);
    return NextResponse.json({ message: "Internal Server Error" }, { status: 500 });
  }
});

// PUT (Update) sync settings (specifically sync_interval)
export const PUT = withAdminAuth(async (req: NextRequest) => {
  try {
    const body = await req.json();
    const { sync_interval } = body;

    if (sync_interval === undefined || typeof sync_interval !== 'number' || sync_interval <= 0) {
      return NextResponse.json({ message: "Invalid sync_interval provided. Must be a positive number." }, { status: 400 });
    }

    // Ensure the record exists before trying to update
    await getOrCreateSyncControl(); 

    const updatedSyncControl = await prisma.syncControl.update({
      where: { id: SYNC_CONTROL_ID },
      data: {
        sync_interval,
      },
    });
    return NextResponse.json(updatedSyncControl);
  } catch (error) {
    console.error("Error updating sync control settings:", error);
    return NextResponse.json({ message: "Internal Server Error" }, { status: 500 });
  }
});
