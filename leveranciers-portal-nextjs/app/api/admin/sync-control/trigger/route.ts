import { NextResponse, NextRequest } from "next/server";
import prisma from "@/lib/db";
import { withAdminAuth } from "@/lib/authHelpers";

const SYNC_CONTROL_ID = 1; // Assuming a single row with ID 1 for sync settings

// Helper to get or create the sync control record (can be imported if refactored)
async function getOrCreateSyncControl() {
  let syncControl = await prisma.syncControl.findUnique({
    where: { id: SYNC_CONTROL_ID },
  });

  if (!syncControl) {
    syncControl = await prisma.syncControl.create({
      data: {
        id: SYNC_CONTROL_ID,
        force_sync: false,
        sync_interval: 3600, // Default interval
      },
    });
  }
  return syncControl;
}

// POST to trigger a forced sync
export const POST = withAdminAuth(async (req: NextRequest) => {
  try {
    // Ensure the record exists
    await getOrCreateSyncControl();

    const updatedSyncControl = await prisma.syncControl.update({
      where: { id: SYNC_CONTROL_ID },
      data: {
        force_sync: true,
      },
    });
    return NextResponse.json({ message: "Sync triggered successfully.", syncControl: updatedSyncControl });
  } catch (error) {
    console.error("Error triggering sync:", error);
    return NextResponse.json({ message: "Internal Server Error" }, { status: 500 });
  }
});
