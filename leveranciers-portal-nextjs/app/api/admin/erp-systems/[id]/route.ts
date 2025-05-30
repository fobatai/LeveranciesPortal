import { NextResponse, NextRequest } from "next/server";
import prisma from "@/lib/db";
import { withAdminAuth } from "@/lib/authHelpers";

interface RouteParams {
  params: {
    id: string;
  };
}

// GET a single ERP system by ID
export const GET = withAdminAuth(async (req: NextRequest, { params }: RouteParams) => {
  const id = parseInt(params.id, 10);
  if (isNaN(id)) {
    return NextResponse.json({ message: "Invalid ID format" }, { status: 400 });
  }

  try {
    const erpSystem = await prisma.klant.findUnique({
      where: { id },
      select: {
        id: true,
        naam: true,
        domein: true,
        createdAt: true,
        updatedAt: true,
        // Exclude api_key
      },
    });

    if (!erpSystem) {
      return NextResponse.json({ message: "ERP System not found" }, { status: 404 });
    }
    return NextResponse.json(erpSystem);
  } catch (error) {
    console.error(`Error fetching ERP system with ID ${id}:`, error);
    return NextResponse.json({ message: "Internal Server Error" }, { status: 500 });
  }
});

// PUT (Update) an ERP system by ID
export const PUT = withAdminAuth(async (req: NextRequest, { params }: RouteParams) => {
  const id = parseInt(params.id, 10);
  if (isNaN(id)) {
    return NextResponse.json({ message: "Invalid ID format" }, { status: 400 });
  }

  try {
    const body = await req.json();
    const { naam, domein, api_key } = body;

    // Basic validation: ensure at least one updatable field is provided
    if (!naam && !domein && !api_key) {
      return NextResponse.json({ message: "No fields provided for update." }, { status: 400 });
    }
    
    const dataToUpdate: { naam?: string; domein?: string; api_key?: string } = {};
    if (naam) dataToUpdate.naam = naam;
    if (domein) dataToUpdate.domein = domein;
    if (api_key) {
      // TODO: Implement API key encryption before storing in production.
      dataToUpdate.api_key = api_key; // Store plain text for now
    }

    // Check if the new domain is already in use by another Klant
    if (domein) {
      const existingKlantByDomain = await prisma.klant.findFirst({
        where: {
          domein: domein,
          id: { not: id }, // Exclude the current Klant being updated
        },
      });
      if (existingKlantByDomain) {
        return NextResponse.json({ message: "Domain already in use by another ERP system." }, { status: 409 });
      }
    }

    const updatedErpSystem = await prisma.klant.update({
      where: { id },
      data: dataToUpdate,
    });

    // Exclude api_key from the response
    const { api_key: _, ...responseSystem } = updatedErpSystem;
    return NextResponse.json(responseSystem);

  } catch (error: any) {
    console.error(`Error updating ERP system with ID ${id}:`, error);
    if (error.code === 'P2025') { // Prisma error code for record not found
      return NextResponse.json({ message: "ERP System not found" }, { status: 404 });
    }
    if (error.code === 'P2002' && error.meta?.target?.includes('domein')) {
      return NextResponse.json({ message: "Domain already in use." }, { status: 409 });
    }
    return NextResponse.json({ message: "Internal Server Error" }, { status: 500 });
  }
});

// DELETE an ERP system by ID
export const DELETE = withAdminAuth(async (req: NextRequest, { params }: RouteParams) => {
  const id = parseInt(params.id, 10);
  if (isNaN(id)) {
    return NextResponse.json({ message: "Invalid ID format" }, { status: 400 });
  }

  try {
    // Transaction to delete Klant and its related entities
    await prisma.$transaction(async (tx) => {
      // Delete related StatusToewijzingen
      await tx.statusToewijzing.deleteMany({
        where: { klant_id: id },
      });

      // Delete related JobsCache entries
      await tx.jobsCache.deleteMany({
        where: { klant_id: id },
      });

      // Delete the Klant itself
      await tx.klant.delete({
        where: { id },
      });
    });

    return NextResponse.json({ message: "ERP System and related data deleted successfully" }, { status: 200 });
  } catch (error: any) {
    console.error(`Error deleting ERP system with ID ${id}:`, error);
    if (error.code === 'P2025') { // Prisma error code for record not found to delete
      return NextResponse.json({ message: "ERP System not found" }, { status: 404 });
    }
    return NextResponse.json({ message: "Internal Server Error" }, { status: 500 });
  }
});
