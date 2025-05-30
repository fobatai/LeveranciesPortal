import { NextResponse, NextRequest } from "next/server";
import prisma from "@/lib/db";
import { withAdminAuth } from "@/lib/authHelpers";

// GET status mappings, optionally filtered by klant_id
export const GET = withAdminAuth(async (req: NextRequest) => {
  const { searchParams } = new URL(req.url);
  const klantIdParam = searchParams.get("klant_id");

  if (!klantIdParam) {
    return NextResponse.json({ message: "Missing klant_id query parameter" }, { status: 400 });
  }

  const klant_id = parseInt(klantIdParam, 10);
  if (isNaN(klant_id)) {
    return NextResponse.json({ message: "Invalid klant_id format" }, { status: 400 });
  }

  try {
    const statusMappings = await prisma.statusToewijzing.findMany({
      where: { klant_id },
      orderBy: {
        van_status: "asc",
      },
    });
    return NextResponse.json(statusMappings);
  } catch (error) {
    console.error(`Error fetching status mappings for klant_id ${klant_id}:`, error);
    return NextResponse.json({ message: "Internal Server Error" }, { status: 500 });
  }
});

// POST a new status mapping
export const POST = withAdminAuth(async (req: NextRequest) => {
  try {
    const body = await req.json();
    const { klant_id, van_status, naar_status } = body;

    if (klant_id === undefined || !van_status || !naar_status) {
      return NextResponse.json({ message: "Missing required fields (klant_id, van_status, naar_status)" }, { status: 400 });
    }
    
    const klantIdInt = parseInt(klant_id, 10);
    if (isNaN(klantIdInt)) {
        return NextResponse.json({ message: "Invalid klant_id format" }, { status: 400 });
    }

    // Check if Klant exists
    const klantExists = await prisma.klant.findUnique({ where: { id: klantIdInt } });
    if (!klantExists) {
      return NextResponse.json({ message: "Klant (ERP System) not found" }, { status: 404 });
    }

    const newStatusMapping = await prisma.statusToewijzing.create({
      data: {
        klant_id: klantIdInt,
        van_status,
        naar_status,
      },
    });
    return NextResponse.json(newStatusMapping, { status: 201 });

  } catch (error) {
    console.error("Error creating status mapping:", error);
    return NextResponse.json({ message: "Internal Server Error" }, { status: 500 });
  }
});
