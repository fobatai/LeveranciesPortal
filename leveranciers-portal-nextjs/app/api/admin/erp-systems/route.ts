import { NextResponse, NextRequest } from "next/server";
import prisma from "@/lib/db";
import { withAdminAuth } from "@/lib/authHelpers";

// GET all ERP systems
export const GET = withAdminAuth(async (req: NextRequest) => {
  try {
    const erpSystems = await prisma.klant.findMany({
      select: {
        id: true,
        naam: true,
        domein: true,
        createdAt: true,
        updatedAt: true,
        // Exclude api_key for security
      },
      orderBy: {
        naam: "asc",
      },
    });
    return NextResponse.json(erpSystems);
  } catch (error) {
    console.error("Error fetching ERP systems:", error);
    return NextResponse.json({ message: "Internal Server Error" }, { status: 500 });
  }
});

// POST a new ERP system
export const POST = withAdminAuth(async (req: NextRequest) => {
  try {
    const body = await req.json();
    const { naam, domein, api_key } = body;

    if (!naam || !domein || !api_key) {
      return NextResponse.json({ message: "Missing required fields (naam, domein, api_key)" }, { status: 400 });
    }

    // TODO: Implement API key encryption before storing in production.
    // For now, storing as plain text as per subtask instructions.
    // const encryptedApiKey = encrypt(api_key); 

    const existingKlantByDomain = await prisma.klant.findUnique({
      where: { domein },
    });

    if (existingKlantByDomain) {
      return NextResponse.json({ message: "Domain already in use." }, { status: 409 }); // 409 Conflict
    }
    
    const newErpSystem = await prisma.klant.create({
      data: {
        naam,
        domein,
        api_key, // Store plain text api_key for now
      },
    });

    // Exclude api_key from the response
    const { api_key: _, ...responseSystem } = newErpSystem;
    return NextResponse.json(responseSystem, { status: 201 });

  } catch (error: any) {
    console.error("Error creating ERP system:", error);
    if (error.code === 'P2002' && error.meta?.target?.includes('domein')) {
      return NextResponse.json({ message: "Domain already in use." }, { status: 409 });
    }
    return NextResponse.json({ message: "Internal Server Error" }, { status: 500 });
  }
});
