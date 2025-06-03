import React from 'react';
import AuthenticatedPageLayout from './AuthenticatedPageLayout'; // Assuming it's in the same directory

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthenticatedPageLayout>
      {children}
    </AuthenticatedPageLayout>
  );
}
