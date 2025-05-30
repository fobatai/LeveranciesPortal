import NextAuth, { type NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import EmailProvider from "next-auth/providers/email";
import { PrismaAdapter } from "@next-auth/prisma-adapter";
import prisma from "@/lib/db"; // My Prisma client instance
import nodemailer from "nodemailer";
import { randomBytes } from "crypto"; // For generating secure random strings

// Placeholder for password hashing and comparison
// In a real app, use bcrypt or argon2
async function verifyPassword(password: string, hash: string): Promise<boolean> {
  // For now, simple comparison. Replace with actual hash comparison.
  // This is NOT secure for production.
  // Example: return await bcrypt.compare(password, hash);
  return password === hash; // Placeholder
}
async function hashPassword(password: string): Promise<string> {
    // For now, simple return. Replace with actual hashing.
    // This is NOT secure for production.
    // Example: return await bcrypt.hash(password, 10);
    return password; // Placeholder
}


export const authOptions: NextAuthOptions = {
  adapter: PrismaAdapter(prisma),
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null;
        }

        // Admin login logic
        if (credentials.email === "admin@example.com") {
          // In a real app, fetch user from DB by email
          // const user = await prisma.user.findUnique({ where: { email: credentials.email }});
          // For this placeholder, we assume admin user exists or compare directly
          // const storedPasswordHash = user?.password_hash || await hashPassword("adminpassword"); // Fetch/store this securely

          // Placeholder: In a real app, password_hash should be stored for admin@example.com
          // For now, let's assume we expect "adminpassword"
          const isValid = await verifyPassword(credentials.password, "adminpassword"); // Compare with the expected password

          if (isValid) {
            // Return a user object that NextAuth expects
            // Ensure this matches your Prisma User model structure for id (string)
            return { 
              id: "cl_admin_placeholder_id", // Prisma User ID is string (cuid)
              email: "admin@example.com", 
              role: "ADMIN",
              name: "Admin User" 
            };
          } else {
            return null; // Password incorrect
          }
        }
        return null; // Not an admin or other credential-based user
      },
    }),
    EmailProvider({
      server: {
        host: process.env.EMAIL_SERVER_HOST,
        port: Number(process.env.EMAIL_SERVER_PORT),
        auth: {
          user: process.env.EMAIL_SERVER_USER,
          pass: process.env.EMAIL_SERVER_PASSWORD,
        },
      },
      from: process.env.EMAIL_FROM,
      async sendVerificationRequest({ identifier: email, url, provider }) {
        // For development, log to console instead of sending real emails
        if (process.env.NODE_ENV === "development") {
          console.log(`Login link for ${email}: ${url}`);
          return;
        }

        // Production email sending (example with nodemailer)
        const { host } = new URL(url);
        const transport = nodemailer.createTransport(provider.server);
        const result = await transport.sendMail({
          to: email,
          from: provider.from,
          subject: `Sign in to ${host}`,
          text: `Sign in to ${host}\n${url}\n\n`,
          html: `<p>Sign in to <strong>${host}</strong></p><p><a href="${url}">Click here to sign in</a></p>`,
        });
        const failed = result.rejected.concat(result.pending).filter(Boolean);
        if (failed.length) {
          throw new Error(`Email(s) (${failed.join(", ")}) could not be sent`);
        }
      },
    }),
  ],
  session: {
    strategy: "jwt", // Using JWT for session strategy
  },
  callbacks: {
    async signIn({ user, account, profile, email, credentials }) {
      if (account?.provider === "credentials") {
        // For admin credentials, authorization is handled in the authorize callback
        // User object from authorize callback will be passed here
        return user ? true : false;
      }
      if (account?.provider === "email") {
        // For email provider (suppliers)
        // Check if the email exists in your system, e.g., in JobsCache or a dedicated Supplier table
        // For now, just allow if email is present (basic check)
        if (user?.email) {
          // Example: Check if supplier exists
          // const supplier = await prisma.jobsCache.findFirst({ where: { leverancier_email_field: user.email }});
          // if (!supplier) return false; // Or redirect to a "not registered" page

          // For this setup, we allow any email that receives a link.
          // The Prisma adapter will create a user if one doesn't exist.
          return true;
        }
        return false;
      }
      return false; // Deny sign-in for other providers or conditions
    },
    async jwt({ token, user, account, profile }) {
      // Persist user id and role to the JWT
      if (user?.id) {
        token.id = user.id;
      }
      if (user?.role) {
        token.role = user.role;
      }
      // if (user) { // User object is available on first sign in
      //   token.id = user.id;
      //   token.role = (user as any).role || "SUPPLIER"; // Cast if role is not directly on User type from NextAuth
      // }
      return token;
    },
    async session({ session, token }) {
      // Add id and role to the session object
      if (token?.id && session.user) {
        (session.user as any).id = token.id as string;
      }
      if (token?.role && session.user) {
        (session.user as any).role = token.role as string;
      }
      // session.user.id = token.id as string;
      // session.user.role = token.role as string; // Ensure your Session type expects role
      return session;
    },
  },
  pages: {
    signIn: '/auth/signin', // Optional: custom sign-in page
    // verifyRequest: '/auth/verify-request', // For Email provider: page shown after email is sent
    // error: '/auth/error', // Error page
  },
  secret: process.env.NEXTAUTH_SECRET, // Already set in .env
  // debug: process.env.NODE_ENV === 'development', // Optional: for debugging
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
