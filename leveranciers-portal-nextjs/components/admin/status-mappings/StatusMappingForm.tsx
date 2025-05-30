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
import { StatusToewijzing } from "@prisma/client";

export const statusMappingFormSchema = z.object({
  van_status: z.string().min(1, { message: "From Status cannot be empty." }).max(100),
  naar_status: z.string().min(1, { message: "To Status cannot be empty." }).max(100),
  // klant_id will be handled by the parent component, not part of this specific form's input fields
});

export type StatusMappingFormValues = z.infer<typeof statusMappingFormSchema>;

interface StatusMappingFormProps {
  onSubmit: (values: StatusMappingFormValues) => Promise<void>;
  defaultValues?: Partial<Omit<StatusToewijzing, "klant_id">>; // klant_id is managed outside
  isLoading?: boolean;
  isEditMode?: boolean;
}

export function StatusMappingForm({ onSubmit, defaultValues, isLoading, isEditMode = false }: StatusMappingFormProps) {
  const form = useForm<StatusMappingFormValues>({
    resolver: zodResolver(statusMappingFormSchema),
    defaultValues: {
      van_status: defaultValues?.van_status || "",
      naar_status: defaultValues?.naar_status || "",
    },
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="van_status"
          render={({ field }) => (
            <FormItem>
              <FormLabel>From Status (ERP)</FormLabel>
              <FormControl>
                <Input placeholder="e.g., OPEN" {...field} disabled={isLoading} />
              </FormControl>
              <FormDescription>The status name as it appears in the ERP system.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="naar_status"
          render={({ field }) => (
            <FormItem>
              <FormLabel>To Status (Portal)</FormLabel>
              <FormControl>
                <Input placeholder="e.g., In Progress" {...field} disabled={isLoading} />
              </FormControl>
              <FormDescription>The corresponding status to display in the portal.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" disabled={isLoading} className="w-full sm:w-auto">
          {isLoading ? (isEditMode ? "Saving Changes..." : "Creating Mapping...") : (isEditMode ? "Save Changes" : "Create Mapping")}
        </Button>
      </form>
    </Form>
  );
}
