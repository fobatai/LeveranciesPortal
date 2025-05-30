import NextAuth, { type NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import EmailProvider from "next-auth/providers/email";
import { PrismaAdapter } from "@next-auth/prisma-adapter";
import prisma from "@/lib/db"; // My Prisma client instance
import nodemailer from "nodemailer";
import { randomBytes } from "crypto"; // For generating secure random strings

// Placeholder for password hashing and comparison
// In a real app, use bcrypt or argon2
// async function verifyPassword(password: string, hash: string): Promise<boolean> {
//   // For now, simple comparison. Replace with actual hash comparison.
//   // This is NOT secure for production.
//   // Example: return await bcrypt.compare(password, hash);
//   return password === hash; // Placeholder
// }
// async function hashPassword(password: string): Promise<string> {
//     // For now, simple return. Replace with actual hashing.
//     // This is NOT secure for production.
//     // Example: return await bcrypt.hash(password, 10);
//     return password; // Placeholder
// }


export const authOptions: NextAuthOptions = {
  // adapter: PrismaAdapter(prisma), // Prisma Adapter disabled
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
        if (credentials.email === "example@admin.com") { // Changed admin email
          // const isValid = await verifyPassword(credentials.password, "adminpassword"); // Original password check
          const isValid = true; // Any password is valid

          if (isValid) {
            return { 
              id: "mockadmin01", 
              email: "example@admin.com", 
              name: "Mock Admin", 
              role: "ADMIN" 
            };
          } else {
            return null; // Password incorrect - though isValid is true now
          }
        }
        return null; 
      },
    }),
    CredentialsProvider({
      name: "SupplierCredentials",
      id: "supplier-credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        // Import prisma client is already at the top of the file.
        
        if (!credentials?.email || !credentials?.password) {
          console.log("Supplier auth: Missing email or password");
          return null;
        }

        // Basic email format validation
        if (!credentials.email.includes("@")) {
          console.log(`Supplier auth: Invalid email format for ${credentials.email}`);
          return null;
        }

        try {
          console.log(`Supplier auth: Checking email ${credentials.email} against UltimoEmployee data...`);
          const employee = await prisma.ultimoEmployee.findUnique({
            where: {
              emailAddress: credentials.email,
            },
          });

          if (employee) {
            console.log(`Supplier auth: Email ${credentials.email} found in UltimoEmployee data. Login successful.`);
            // Any password is valid, email found is enough
            return { 
              id: "supplier_" + employee.id, // Use employee's Ultimo ID
              email: employee.emailAddress, 
              name: employee.description || "Supplier " + employee.emailAddress, 
              role: "SUPPLIER" 
            };
          } else {
            console.log(`Supplier auth: Email ${credentials.email} NOT found in UltimoEmployee data. Login denied.`);
            return null; // Email not found
          }
        } catch (error) {
          console.error(`Supplier auth: Error during database lookup for email ${credentials.email}:`, error);
          return null; // Error during lookup
        }
      },
    }),
    // EmailProvider({ // EmailProvider removed
    //   server: {
    //     host: process.env.EMAIL_SERVER_HOST,
    //     port: Number(process.env.EMAIL_SERVER_PORT),
    //     auth: {
    //       user: process.env.EMAIL_SERVER_USER,
    //       pass: process.env.EMAIL_SERVER_PASSWORD,
    //     },
    //   },
    //   from: process.env.EMAIL_FROM,
    //   async sendVerificationRequest({ identifier: email, url, provider }) {
    //     // For development, log to console instead of sending real emails
    //     if (process.env.NODE_ENV === "development") {
    //       console.log(`Login link for ${email}: ${url}`);
    //       return;
    //     }

    //     // Production email sending (example with nodemailer)
    //     const { host } = new URL(url);
    //     const transport = nodemailer.createTransport(provider.server);
    //     const result = await transport.sendMail({
    //       to: email,
    //       from: provider.from,
    //       subject: `Sign in to ${host}`,
    //       text: `Sign in to ${host}\n${url}\n\n`,
    //       html: `<p>Sign in to <strong>${host}</strong></p><p><a href="${url}">Click here to sign in</a></p>`,
    //     });
    //     const failed = result.rejected.concat(result.pending).filter(Boolean);
    //     if (failed.length) {
    //       throw new Error(`Email(s) (${failed.join(", ")}) could not be sent`);
    //     }
    //   },
    // }),
  ],
  session: {
    strategy: "jwt", // Using JWT for session strategy
  },
  callbacks: {
    async signIn({ user, account, profile, email, credentials }) {
      if (account?.provider === "credentials" || account?.provider === "supplier-credentials") {
        // For admin and supplier credentials, authorization is handled in their respective authorize callbacks
        // User object from authorize callback will be passed here
        return user ? true : false;
      }
      // if (account?.provider === "email") { // Email provider removed
      //   // For email provider (suppliers)
      //   // Check if the email exists in your system, e.g., in JobsCache or a dedicated Supplier table
      //   // For now, just allow if email is present (basic check)
      //   if (user?.email) {
      //     // Example: Check if supplier exists
      //     // const supplier = await prisma.jobsCache.findFirst({ where: { leverancier_email_field: user.email }});
      //     // if (!supplier) return false; // Or redirect to a "not registered" page

      //     // For this setup, we allow any email that receives a link.
      //     // The Prisma adapter will create a user if one doesn't exist.
      //     return true;
      //   }
      //   return false;
      // }
      return false; // Deny sign-in for other providers or conditions
    },
    async jwt({ token, user, account, profile }) {
      // Persist user id and role to the JWT
      if (user) { // User object is available on first sign in / when new user object is returned from authorize
        token.id = user.id;
        token.role = (user as any).role; // role is part of our user object
        token.email = user.email; // ensure email is passed through
        token.name = user.name; // ensure name is passed through
      }
      return token;
    },
    async session({ session, token }) {
      // Add id and role to the session object
      if (token?.id && session.user) { // Ensure session.user exists
        (session.user as any).id = token.id as string;
      }
      if (token?.role && session.user) { // Ensure session.user exists
        (session.user as any).role = token.role as string;
      }
      if (token?.email && session.user) { // Ensure email is passed to session
          session.user.email = token.email as string;
      }
      if (token?.name && session.user) { // Ensure name is passed to session
          session.user.name = token.name as string;
      }
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
