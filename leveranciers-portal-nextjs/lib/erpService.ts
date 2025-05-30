// lib/erpService.ts

// TODO: Make this configurable if it varies per ERP or setup
const DEFAULT_APPLICATION_ELEMENT_ID = "D1FB01D577C248DFB95A2ADA578578DF";

export class ErpApiError extends Error {
  status: number;
  erpError?: any; // To store any error body from the ERP

  constructor(message: string, status: number, erpError?: any) {
    super(message);
    this.name = "ErpApiError";
    this.status = status;
    this.erpError = erpError;
    Object.setPrototypeOf(this, ErpApiError.prototype);
  }
}

async function fetchErp<T>(
  url: string,
  method: "GET" | "POST" | "PATCH" | "DELETE",
  apiKey: string,
  body?: Record<string, any>,
  additionalHeaders?: Record<string, string>
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    // Common authentication methods for ERPs. Adjust as needed.
    // Some might use a bearer token, some a custom header like X-Api-Key.
    "Authorization": `Bearer ${apiKey}`, 
    "X-Api-Key": apiKey, 
    ...additionalHeaders,
  };

  console.log(`[erpService] Request: ${method} ${url}`);
  // In production, be careful about logging sensitive parts of the body or apiKey.
  // if (body) console.log(`[erpService] Body: ${JSON.stringify(body)}`);


  const response = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let errorBody;
    try {
      errorBody = await response.json(); // Try to parse as JSON
    } catch (e) {
      errorBody = await response.text(); // Fallback to text
    }
    console.error(`[erpService] ERP API Error (${response.status}):`, errorBody);
    throw new ErpApiError(
      `ERP API request failed: ${response.statusText}`,
      response.status,
      errorBody
    );
  }

  // For methods like PATCH or DELETE that might not return a body or return 204 No Content
  if (response.status === 204 || response.headers.get("content-length") === "0") {
    return null as T; // Or an appropriate success indicator like { success: true }
  }
  
  const responseData = await response.json();
  console.log(`[erpService] Response from ${method} ${url}:`, responseData);
  return responseData as T;
}

// --- Core ERP Interaction Functions ---

export async function getErpProgressStatuses(domain: string, apiKey: string): Promise<any[]> {
  const url = `https://${domain}/api/v1/object/ProgressStatus?$select=Name,Description`; // Example: select only needed fields
  return fetchErp<any[]>(url, "GET", apiKey);
}

export async function getErpJobs(
  domain: string,
  apiKey: string,
  options?: { filter?: string; expand?: string, select?: string, top?: number }
): Promise<any[]> {
  let url = `https://${domain}/api/v1/object/Job`;
  const queryParams = new URLSearchParams();
  if (options?.filter) queryParams.append("$filter", options.filter);
  if (options?.expand) queryParams.append("$expand", options.expand);
  if (options?.select) queryParams.append("$select", options.select);
  if (options?.top) queryParams.append("$top", options.top.toString());

  if (queryParams.toString()) {
    url += `?${queryParams.toString()}`;
  }
  return fetchErp<any[]>(url, "GET", apiKey);
}

export async function updateErpJobStatus(
  domain: string,
  apiKey: string,
  jobId: string,
  payload: { ProgressStatus: string; FeedbackText?: string; StatusCompletedDate: string }
): Promise<any> {
  const url = `https://${domain}/api/v1/object/Job('${jobId}')`;
  return fetchErp<any>(url, "PATCH", apiKey, payload);
}

export async function attachImageToErpJob(
  domain: string,
  apiKey: string,
  payload: {
    JobId: string;
    ImageFileBase64: string;
    ImageFileBase64Extension: string;
    ApplicationElementId?: string; // Optional, use default if not provided
  }
): Promise<any> {
  const url = `https://${domain}/api/v1/action/REST_AttachImageToJob`;
  const submissionPayload = {
    JobId: payload.JobId,
    ImageFileBase64: payload.ImageFileBase64,
    ImageFileBase64Extension: payload.ImageFileBase64Extension,
  };
  const headers = {
    ApplicationElementId: payload.ApplicationElementId || DEFAULT_APPLICATION_ELEMENT_ID,
  };
  return fetchErp<any>(url, "POST", apiKey, submissionPayload, headers);
}

// Example of fetching a single job, could be useful
export async function getErpJobById(
  domain: string, 
  apiKey: string, 
  jobId: string,
  options?: { expand?: string, select?: string }
): Promise<any> {
  let url = `https://${domain}/api/v1/object/Job('${jobId}')`;
  const queryParams = new URLSearchParams();
  if (options?.expand) queryParams.append("$expand", options.expand);
  if (options?.select) queryParams.append("$select", options.select);
  if (queryParams.toString()) {
    url += `?${queryParams.toString()}`;
  }
  return fetchErp<any>(url, "GET", apiKey);
}
