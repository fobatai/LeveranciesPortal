import { getServerSession } from "next-auth/next";
import { authOptions } from "@/app/api/auth/[...nextauth]/route"; // Adjust path as necessary
import { NextRequest, NextResponse } from "next/server";

interface AuthenticatedUser {
  id: string;
  role: string;
  email?: string | null; // Add other fields you expect in your session user
  name?: string | null;
}

export async function getAuthenticatedUser(req: NextRequest): Promise<AuthenticatedUser | null> {
  const session = await getServerSession(authOptions);
  if (session && session.user) {
    // Ensure the user object in the session has the expected structure
    // The 'id' and 'role' might be on token, then copied to session.user in callbacks
    return session.user as AuthenticatedUser;
  }
  return null;
}

export async function isAdmin(req: NextRequest): Promise<boolean> {
  const user = await getAuthenticatedUser(req);
  return user?.role === "ADMIN";
}

// Higher-order function for route handlers to protect them for ADMIN access
export function withAdminAuth(handler: (req: NextRequest, params?: { params: any }) => Promise<NextResponse>) {
  return async (req: NextRequest, params?: { params: any }): Promise<NextResponse> => {
    const user = await getAuthenticatedUser(req);
    if (!user) {
      return NextResponse.json({ message: "Unauthorized: Not authenticated." }, { status: 401 });
    }
    if (user.role !== "ADMIN") {
      return NextResponse.json({ message: "Forbidden: Administrator access required." }, { status: 403 });
    }
    return handler(req, params);
  };
}

// Higher-order function for route handlers to protect them for any authenticated user
export function withAuth(handler: (req: NextRequest, params?: { params: any }) => Promise<NextResponse>) {
  return async (req: NextRequest, params?: { params: any }): Promise<NextResponse> => {
    const user = await getAuthenticatedUser(req);
    if (!user) {
      return NextResponse.json({ message: "Unauthorized: Not authenticated." }, { status: 401 });
    }
    // For supplier routes, we might not strictly check for 'SUPPLIER' role yet,
    // as long as they are authenticated. Specific checks can be added inside the handler if needed.
    return handler(req, params);
  };
}
