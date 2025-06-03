import { NextResponse, NextRequest } from 'next/server';
import prisma from '@/lib/db'; // Assumes prisma client is exported from @/lib/db

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { name, domain, apiKey } = body;

    // Basic validation
    if (!name || !domain || !apiKey) {
      return NextResponse.json({ message: 'Missing required fields (name, domain, apiKey)' }, { status: 400 });
    }

    // Check if an ERP system with the same name already exists
    const existingErpSystem = await prisma.erpSystem.findUnique({
      where: { name },
    });

    if (existingErpSystem) {
      return NextResponse.json({ message: `An ERP system with the name '${name}' already exists.` }, { status: 409 }); // 409 Conflict
    }

    const newErpSystem = await prisma.erpSystem.create({
      data: {
        name,
        domain,
        apiKey, // Storing apiKey as plain text as per current requirements
      },
    });

    return NextResponse.json(newErpSystem, { status: 201 });
  } catch (error: any) {
    console.error('Error creating ERP system:', error);
    // Handle specific Prisma unique constraint error for name
    if (error.code === 'P2002' && error.meta?.target?.includes('name')) {
      return NextResponse.json({ message: `An ERP system with the name '${error.meta?.target?.[0] || 'provided'}' already exists.` }, { status: 409 });
    }
    return NextResponse.json({ message: 'Internal Server Error' }, { status: 500 });
  }
}

export async function GET() {
  try {
    const erpSystems = await prisma.erpSystem.findMany({
      orderBy: {
        createdAt: 'desc', // Optional: order by creation date
      },
    });
    return NextResponse.json(erpSystems, { status: 200 });
  } catch (error) {
    console.error('Error fetching ERP systems:', error);
    return NextResponse.json({ message: 'Internal Server Error' }, { status: 500 });
  }
}
