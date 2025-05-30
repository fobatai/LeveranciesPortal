import axios from 'axios'; // You might need to ensure axios is installed or use fetch

const ULTIMO_API_KEY = 'E7BFA8ADE2AF4A3FB49962F54AAFB5A6'; // Reminder: Should be env variable
const BASE_URL = 'https://025105.ultimo-demo.net/api/v1';

interface UltimoProgressStatusItem {
  Id: string;
  Description: string;
  [key: string]: any; // Allow other properties
}

interface UltimoEmployeeItem {
  Id: string;
  Description?: string;
  EmailAddress?: string;
  [key: string]: any;
}

interface UltimoObjectContactItem {
  Id: string;
  Employee?: UltimoEmployeeItem;
  [key: string]: any;
}

interface UltimoVendorItem {
  Id: string;
  Description?: string;
  EmailAddress?: string;
  ObjectContacts?: UltimoObjectContactItem[];
  [key: string]: any;
}

interface UltimoJobItem {
  Id: string;
  Description?: string;
  RecordChangeDate?: string; // Assuming string, will be parsed to DateTime later
  ProgressStatus?: string; // This is the ID of the progress status
  Vendor?: UltimoVendorItem;
  [key: string]: any;
}

interface ApiResponse<T> {
  items: T[];
  // Potentially other pagination fields if Ultimo API uses them
}

export async function fetchProgressStatuses(): Promise<UltimoProgressStatusItem[]> {
  const url = `${BASE_URL}/object/ProgressStatus`;
  try {
    console.log(`Fetching progress statuses from: ${url}`);
    const response = await axios.get<ApiResponse<UltimoProgressStatusItem>>(url, {
      headers: {
        'accept': 'application/json',
        'ApiKey': ULTIMO_API_KEY,
      },
    });
    console.log(`Successfully fetched ${response.data.items.length} progress statuses.`);
    return response.data.items;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      console.error('Error fetching progress statuses:', error.response?.status, error.response?.data);
    } else {
      console.error('Error fetching progress statuses:', error);
    }
    return []; // Return empty array on error
  }
}

export async function fetchJobs(filter?: string): Promise<UltimoJobItem[]> {
  // Base URL for jobs, includes expansion for related entities
  let url = `${BASE_URL}/object/Job?expand=Vendor/ObjectContacts/Employee`;
  if (filter) {
    url += `&filter=${encodeURIComponent(filter)}`; // Add filter if provided
  }
  
  try {
    console.log(`Fetching jobs from: ${url}`);
    // Note: The API response for jobs is directly an object with an "items" array.
    const response = await axios.get<{ items: UltimoJobItem[] }>(url, {
      headers: {
        'accept': 'application/json',
        'ApiKey': ULTIMO_API_KEY,
      },
    });
    console.log(`Successfully fetched ${response.data.items.length} jobs.`);
    return response.data.items;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      console.error('Error fetching jobs:', error.response?.status, error.response?.data);
    } else {
      console.error('Error fetching jobs:', error);
    }
    return []; // Return empty array on error
  }
}
