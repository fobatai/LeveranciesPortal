import { NextResponse, NextRequest } from 'next/server';
import prisma from '@/lib/db';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const {
      erpSystemId,
      sourceStatusId,
      sourceStatusDescription,
      targetStatusId,
      targetStatusDescription
    } = body;

    // Basic validation
    if (!erpSystemId || !sourceStatusId || !sourceStatusDescription || !targetStatusId || !targetStatusDescription) {
      return NextResponse.json({
        message: 'Missing required fields (erpSystemId, sourceStatusId, sourceStatusDescription, targetStatusId, targetStatusDescription)'
      }, { status: 400 });
    }

    // Check if the referenced ErpSystem actually exists
    const erpSystemExists = await prisma.erpSystem.findUnique({
      where: { id: erpSystemId },
    });
    if (!erpSystemExists) {
      return NextResponse.json({ message: `ERP system with ID ${erpSystemId} not found.` }, { status: 404 });
    }

    const newStatusMapping = await prisma.statusMapping.create({
      data: {
        erpSystemId,
        sourceStatusId,
        sourceStatusDescription,
        targetStatusId,
        targetStatusDescription,
      },
    });

    return NextResponse.json(newStatusMapping, { status: 201 });
  } catch (error: any) {
    console.error('Error creating status mapping:', error);
    if (error.code === 'P2002' && error.meta?.target?.includes('erpSystemId') && error.meta?.target?.includes('sourceStatusId')) {
      // This specific check for P2002 might need adjustment based on the exact target fields in @@unique
      return NextResponse.json({ message: 'This status mapping (ERP System ID and Source Status ID combination) already exists.' }, { status: 409 });
    }
    return NextResponse.json({ message: 'Internal Server Error' }, { status: 500 });
  }
}

export async function GET(request: NextRequest) {
  try {
    const erpSystemId = request.nextUrl.searchParams.get('erpSystemId');

    if (!erpSystemId) {
      return NextResponse.json({ message: 'erpSystemId query parameter is required' }, { status: 400 });
    }

    const statusMappings = await prisma.statusMapping.findMany({
      where: { erpSystemId },
      orderBy: {
        createdAt: 'desc', // Optional: order them, e.g., by creation date or source description
      },
    });

    return NextResponse.json(statusMappings, { status: 200 });
  } catch (error) {
    console.error('Error fetching status mappings:', error);
    return NextResponse.json({ message: 'Internal Server Error' }, { status: 500 });
  }
}
