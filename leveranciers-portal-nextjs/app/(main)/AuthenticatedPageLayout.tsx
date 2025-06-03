'use client';

import React, { useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

interface AuthenticatedPageLayoutProps {
  children: ReactNode;
}

export default function AuthenticatedPageLayout({ children }: AuthenticatedPageLayoutProps) {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    const email = localStorage.getItem('userEmail');
    if (!email) {
      router.push('/login');
    } else {
      setUserEmail(email);
      setIsAuthenticated(true);
    }
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem('userEmail');
    setUserEmail(null);
    setIsAuthenticated(false);
    router.push('/login');
  };

  if (!isAuthenticated) {
    // You can return a loader here if you want
    return null;
  }

  return (
    <div>
      <nav style={{ padding: '1rem', backgroundColor: '#f0f0f0', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between' }}>
        <div>
          {userEmail ? `Logged in as: ${userEmail}` : 'Not logged in'}
        </div>
        <button onClick={handleLogout}>Logout</button>
      </nav>
      {children}
    </div>
  );
}
