import { NextResponse, NextRequest } from "next/server";
import prisma from "@/lib/db";
import { withAdminAuth } from "@/lib/authHelpers";

interface RouteParams {
  params: {
    id: string;
  };
}

// PUT (Update) a status mapping by ID
export const PUT = withAdminAuth(async (req: NextRequest, { params }: RouteParams) => {
  const id = parseInt(params.id, 10);
  if (isNaN(id)) {
    return NextResponse.json({ message: "Invalid ID format" }, { status: 400 });
  }

  try {
    const body = await req.json();
    const { van_status, naar_status } = body;

    if (!van_status && !naar_status) {
      return NextResponse.json({ message: "No fields provided for update (van_status, naar_status)." }, { status: 400 });
    }
    
    const dataToUpdate: { van_status?: string; naar_status?: string } = {};
    if (van_status) dataToUpdate.van_status = van_status;
    if (naar_status) dataToUpdate.naar_status = naar_status;

    const updatedStatusMapping = await prisma.statusToewijzing.update({
      where: { id },
      data: dataToUpdate,
    });
    return NextResponse.json(updatedStatusMapping);

  } catch (error: any) {
    console.error(`Error updating status mapping with ID ${id}:`, error);
    if (error.code === 'P2025') { // Prisma error code for record not found
      return NextResponse.json({ message: "Status mapping not found" }, { status: 404 });
    }
    return NextResponse.json({ message: "Internal Server Error" }, { status: 500 });
  }
});

// DELETE a status mapping by ID
export const DELETE = withAdminAuth(async (req: NextRequest, { params }: RouteParams) => {
  const id = parseInt(params.id, 10);
  if (isNaN(id)) {
    return NextResponse.json({ message: "Invalid ID format" }, { status: 400 });
  }

  try {
    await prisma.statusToewijzing.delete({
      where: { id },
    });
    return NextResponse.json({ message: "Status mapping deleted successfully" }, { status: 200 });
  } catch (error: any) {
    console.error(`Error deleting status mapping with ID ${id}:`, error);
     if (error.code === 'P2025') { // Prisma error code for record not found
      return NextResponse.json({ message: "Status mapping not found" }, { status: 404 });
    }
    return NextResponse.json({ message: "Internal Server Error" }, { status: 500 });
  }
});
