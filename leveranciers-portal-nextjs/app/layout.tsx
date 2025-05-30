import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";
import { ThemeProvider } from "@/components/theme-provider";
import { NextAuthProvider } from "@/components/auth-provider";
import UserNav from "@/components/layout/UserNav"; // Import UserNav

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "Leveranciers Portal",
  description: "Portal voor leveranciers",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={cn(
          "min-h-screen bg-background font-sans antialiased",
          inter.variable
        )}
      >
        <NextAuthProvider>
          <ThemeProvider
            attribute="class"
            defaultTheme="system"
            enableSystem
            disableTransitionOnChange
          >
            <div className="flex flex-col min-h-screen">
              <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
                <div className="container flex h-14 max-w-screen-2xl items-center justify-between"> {/* Added justify-between */}
                  <p className="font-bold">Leveranciers Portal</p>
                  <UserNav /> {/* Add UserNav component here */}
                </div>
              </header>
              <div className="flex flex-1 container max-w-screen-2xl">
                <aside className="hidden md:block w-64 py-6 pr-6 border-r border-border/40">
                  <p className="p-4 border rounded-md">Sidebar (Placeholder)</p>
                </aside>
                <main className="flex-1 py-6 pl-0 md:pl-6">
                  <div className="p-4 border rounded-md min-h-[calc(100vh-10rem)]">
                    {children}
                  </div>
                </main>
              </div>
              <footer className="py-6 md:px-8 md:py-0 border-t border-border/40 bg-background">
                <div className="container flex flex-col items-center justify-between gap-4 md:h-24 md:flex-row">
                  <p className="text-balance text-center text-sm leading-loose text-muted-foreground md:text-left">
                    © {new Date().getFullYear()} Bedrijfsnaam. Alle rechten voorbehouden.
                  </p>
                </div>
              </footer>
            </div>
          </ThemeProvider>
        </NextAuthProvider>
      </body>
    </html>
  );
}
