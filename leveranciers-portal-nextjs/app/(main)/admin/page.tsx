"use client";

import AdminPageLayout from "../AdminPageLayout";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ListChecks, Settings, Users, ServerCog } from "lucide-react";

const adminSections = [
  {
    title: "ERP Systems",
    description: "Manage customer ERP system configurations and API keys.",
    href: "/admin/erp-systems",
    icon: <ServerCog className="h-6 w-6" />,
  },
  {
    title: "Status Mappings",
    description: "Configure status mappings for each ERP system.",
    href: "/admin/status-mappings",
    icon: <ListChecks className="h-6 w-6" />,
  },
  {
    title: "Supplier Access",
    description: "View an overview of supplier email access based on job data.",
    href: "/admin/supplier-access",
    icon: <Users className="h-6 w-6" />,
  },
  {
    title: "Sync Settings",
    description: "Manage data synchronization settings and trigger manual syncs.",
    href: "/admin/sync-settings",
    icon: <Settings className="h-6 w-6" />,
  },
];

export default function AdminDashboardPage() {
  return (
    <AdminPageLayout title="Admin Dashboard">
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-2">
        {adminSections.map((section) => (
          <Card key={section.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-lg font-medium">
                {section.title}
              </CardTitle>
              {section.icon}
            </CardHeader>
            <CardContent>
              <CardDescription className="mb-4">{section.description}</CardDescription>
              <Button asChild variant="outline">
                <Link href={section.href}>Go to {section.title}</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
      {/* More dashboard widgets can be added here */}
    </AdminPageLayout>
  );
}
