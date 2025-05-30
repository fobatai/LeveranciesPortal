"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

export default function SupplierLoginPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setMessage(null);
    setError(null);
    setIsLoading(true);

    try {
      const result = await signIn("email", {
        email,
        redirect: false, // Important: handle success/error messages on this page
        // callbackUrl: '/dashboard', // Optional: NextAuth will handle redirect after link click
      });

      if (result?.error) {
        setError(result.error === "EmailSignIn" ? "Could not send login email. Please try again." : result.error);
      } else if (result?.ok) {
        setMessage("Check your email (or console in dev mode) for the login link. The link will redirect you to your dashboard upon successful verification.");
      }
    } catch (err) {
      setError("An unexpected error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-muted/40">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Supplier Portal Login</CardTitle>
          <CardDescription>Enter your email address to receive a magic link to login.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="your.email@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>
            {message && (
              <p className="text-sm text-green-600 bg-green-50 p-2 rounded-md">
                {message}
              </p>
            )}
            {error && (
              <p className="text-sm text-destructive bg-destructive/10 p-2 rounded-md">
                {error}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? "Sending link..." : "Send Login Link"}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="text-center text-sm">
          <Link href="/login/admin" className="hover:underline">
            Login as Admin
          </Link>
        </CardFooter>
      </Card>
    </div>
  );
}
