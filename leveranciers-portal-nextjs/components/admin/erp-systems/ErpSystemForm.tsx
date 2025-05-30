"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Klant } from "@prisma/client"; // Assuming Klant is the type for ERP System

export const erpSystemFormSchema = z.object({
  naam: z.string().min(2, { message: "Name must be at least 2 characters." }).max(100),
  domein: z.string().url({ message: "Please enter a valid URL (e.g., https://example.com)." }),
  // API Key is optional during edit, but required for create.
  // For simplicity in the form, we'll make it optional here and handle logic in submit.
  api_key: z.string().max(255).optional(), 
});

export type ErpSystemFormValues = z.infer<typeof erpSystemFormSchema>;

interface ErpSystemFormProps {
  onSubmit: (values: ErpSystemFormValues) => Promise<void>;
  defaultValues?: Partial<Klant>; // Klant type from Prisma (id, naam, domein, api_key, createdAt, updatedAt)
  isLoading?: boolean;
  isEditMode?: boolean;
}

export function ErpSystemForm({ onSubmit, defaultValues, isLoading, isEditMode = false }: ErpSystemFormProps) {
  const form = useForm<ErpSystemFormValues>({
    resolver: zodResolver(erpSystemFormSchema),
    defaultValues: {
      naam: defaultValues?.naam || "",
      domein: defaultValues?.domein || "",
      api_key: "", // API key is not pre-filled for security, only set if changed
    },
  });

  const handleSubmit = async (values: ErpSystemFormValues) => {
    // If in edit mode and api_key is empty, don't send it (means no change)
    const submissionValues = { ...values };
    if (isEditMode && (!submissionValues.api_key || submissionValues.api_key.trim() === "")) {
      delete submissionValues.api_key;
    }
    await onSubmit(submissionValues);
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="naam"
          render={({ field }) => (
            <FormItem>
              <FormLabel>System Name</FormLabel>
              <FormControl>
                <Input placeholder="e.g., Main ERP" {...field} disabled={isLoading} />
              </FormControl>
              <FormDescription>A descriptive name for the ERP system.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="domein"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Domain URL</FormLabel>
              <FormControl>
                <Input placeholder="https://erp.example.com" {...field} disabled={isLoading} />
              </FormControl>
              <FormDescription>The base URL of the ERP system's API.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="api_key"
          render={({ field }) => (
            <FormItem>
              <FormLabel>API Key</FormLabel>
              <FormControl>
                <Input type="password" placeholder={isEditMode ? "Enter new API key to change" : "Enter API Key"} {...field} disabled={isLoading} />
              </FormControl>
              <FormDescription>
                {isEditMode ? "Leave blank to keep the existing API key." : "The API key for accessing the ERP system."}
                <br />
                <span className="text-destructive/80">API keys are sensitive and stored as provided.</span> 
                {/* TODO: Mention encryption when implemented */}
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" disabled={isLoading} className="w-full sm:w-auto">
          {isLoading ? (isEditMode ? "Saving Changes..." : "Creating System...") : (isEditMode ? "Save Changes" : "Create ERP System")}
        </Button>
      </form>
    </Form>
  );
}
