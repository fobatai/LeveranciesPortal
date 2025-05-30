import { NextResponse, NextRequest } from "next/server";
import prisma from "@/lib/db";
import { withAdminAuth } from "@/lib/authHelpers";
import { getErpProgressStatuses, ErpApiError } from "@/lib/erpService";

interface RouteParams {
  params: {
    id: string; // Klant ID
  };
}

export const GET = withAdminAuth(async (req: NextRequest, { params }: RouteParams) => {
  const klantId = parseInt(params.id, 10);
  if (isNaN(klantId)) {
    return NextResponse.json({ message: "Invalid Klant ID format" }, { status: 400 });
  }

  try {
    const klant = await prisma.klant.findUnique({
      where: { id: klantId },
    });

    if (!klant) {
      return NextResponse.json({ message: "ERP System (Klant) not found" }, { status: 404 });
    }

    if (!klant.domein || !klant.api_key) {
      return NextResponse.json({ message: "ERP system domain or API key is not configured." }, { status: 400 });
    }

    const statuses = await getErpProgressStatuses(klant.domein, klant.api_key);
    return NextResponse.json(statuses);

  } catch (error: any) {
    console.error(`Error fetching statuses for Klant ID ${klantId}:`, error);
    if (error instanceof ErpApiError) {
      return NextResponse.json(
        { message: `Failed to fetch statuses from ERP: ${error.message}`, erpError: error.erpError },
        { status: error.status }
      );
    }
    if (error.message.includes("ERP system domain or API key is not configured")) {
        return NextResponse.json({ message: error.message }, { status: 400 });
    }
    return NextResponse.json({ message: "Internal Server Error" }, { status: 500 });
  }
});
