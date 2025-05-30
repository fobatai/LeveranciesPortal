// leveranciers-portal-nextjs/scripts/syncUltimo.ts
import prisma from '../lib/db'; // Adjust path if your db export is elsewhere
import { fetchProgressStatuses, fetchJobs } from '../lib/ultimoService'; // Adjust path

async function main() {
  console.log('Starting Ultimo data synchronization...');

  // 1. Sync Progress Statuses
  console.log('Fetching progress statuses from Ultimo...');
  const progressStatuses = await fetchProgressStatuses();
  if (progressStatuses.length > 0) {
    console.log(`Upserting ${progressStatuses.length} progress statuses into the database...`);
    for (const status of progressStatuses) {
      try {
        await prisma.ultimoProgressStatus.upsert({
          where: { id: status.Id },
          update: { description: status.Description },
          create: {
            id: status.Id,
            description: status.Description,
          },
        });
      } catch (e) {
        console.error(`Error upserting progress status ${status.Id}:`, e);
      }
    }
    console.log('Progress statuses synchronized.');
  } else {
    console.log('No progress statuses fetched or an error occurred.');
  }

  // 2. Sync Jobs (includes Vendors and Employees)
  console.log('Fetching jobs from Ultimo...');
  // For a full sync, we don't pass a filter. 
  // For incremental, a filter like `RecordChangeDate gt 'YYYY-MM-DDTHH:MM:SSZ'` would be needed.
  const jobs = await fetchJobs(); 
  if (jobs.length > 0) {
    console.log(`Processing ${jobs.length} jobs for synchronization...`);
    for (const job of jobs) {
      try {
        // Upsert Vendor first, if present
        let vendorIdToLink: string | undefined = undefined;
        if (job.Vendor) {
          const vendorData = job.Vendor;
          try {
            await prisma.ultimoVendor.upsert({
              where: { id: vendorData.Id },
              update: {
                description: vendorData.Description,
                emailAddress: vendorData.EmailAddress,
              },
              create: {
                id: vendorData.Id,
                description: vendorData.Description,
                emailAddress: vendorData.EmailAddress,
              },
            });
            vendorIdToLink = vendorData.Id;
            console.log(`Upserted Vendor ${vendorData.Id}`);

            // Upsert Employees for this Vendor, if present
            if (vendorData.ObjectContacts && vendorData.ObjectContacts.length > 0) {
              for (const contact of vendorData.ObjectContacts) {
                if (contact.Employee && contact.Employee.EmailAddress) { // EmailAddress is mandatory for login
                  const employeeData = contact.Employee;
                  try {
                    await prisma.ultimoEmployee.upsert({
                      where: { emailAddress: employeeData.EmailAddress }, // Use emailAddress as unique key
                      update: {
                        id: employeeData.Id, // Update Id if it somehow changed for the same email
                        description: employeeData.Description,
                        vendorId: vendorData.Id,
                      },
                      create: {
                        id: employeeData.Id,
                        description: employeeData.Description,
                        emailAddress: employeeData.EmailAddress,
                        vendorId: vendorData.Id,
                      },
                    });
                    console.log(`Upserted Employee ${employeeData.EmailAddress} for Vendor ${vendorData.Id}`);
                  } catch (empError) {
                    console.error(`Error upserting employee ${employeeData.EmailAddress} for vendor ${vendorData.Id}:`, empError);
                  }
                }
              }
            }
          } catch (venError) {
             console.error(`Error upserting vendor ${vendorData.Id}:`, venError);
          }
        }

        // Then Upsert Job
        // Ensure RecordChangeDate is a valid Date object or null
        let recordChangeDateTime: Date | null = null;
        if (job.RecordChangeDate) {
            recordChangeDateTime = new Date(job.RecordChangeDate);
            if (isNaN(recordChangeDateTime.getTime())) {
                console.error(`Invalid RecordChangeDate for job ${job.Id}: ${job.RecordChangeDate}. Setting to null, but this might fail.`);
                // Forcing an error or specific handling might be better depending on strictness
                // recordChangeDateTime = null; // Prisma will error if this isn't a valid date or null for a DateTime field
                throw new Error(`Invalid RecordChangeDate for job ${job.Id}: ${job.RecordChangeDate}. Cannot proceed with this job.`);
            }
        }
        
        await prisma.job.upsert({
          where: { id: job.Id },
          update: {
            description: job.Description ?? 'No description',
            recordChangeDate: recordChangeDateTime!, 
            statusId: job.ProgressStatus, // This is the ID string from Ultimo
            vendorId: vendorIdToLink,
            // Note: We are not updating 'klant_id' or other original JobsCache fields here
            // unless they are also part of the 'job' payload from Ultimo and mapped.
          },
          create: {
            id: job.Id,
            description: job.Description ?? 'No description',
            recordChangeDate: recordChangeDateTime!,
            statusId: job.ProgressStatus,
            vendorId: vendorIdToLink,
            // `klant_id` would be null/undefined here unless specifically mapped
          },
        });
        console.log(`Upserted Job ${job.Id}`);

      } catch (e) {
        console.error(`Error processing or upserting job ${job.Id}:`, e);
      }
    }
    console.log('Jobs, vendors, and employees synchronized.');
  } else {
    console.log('No jobs fetched or an error occurred during fetch.');
  }

  console.log('Ultimo data synchronization finished.');
}

main()
  .catch((e) => {
    console.error('Unhandled error in main sync script:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
