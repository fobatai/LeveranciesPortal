'use client';

import React, { useState, useEffect, ChangeEvent } from 'react';

// Define an interface for the ErpSystem objects we expect from the API
interface ErpSystem {
  id: string;
  name: string;
  domain: string;
  apiKey: string;
  createdAt: string;
  updatedAt: string;
}

// Interface for ProgressStatus items from Ultimo API
interface ProgressStatusItem {
  Id: string;
  Description: string;
  Context?: number; // Example: 0 for Job, 1 for WorkOrder
  HoursAreMandatory?: boolean;
  IsSystem?: boolean;
  IsBlocked?: boolean;
  // Add other fields if necessary, based on actual API response
}

export default function StatusMappingsAdminPage() {
  const [erpSystems, setErpSystems] = useState<ErpSystem[]>([]);
  const [selectedErpSystemId, setSelectedErpSystemId] = useState<string>('');
  const [isLoadingErpSystems, setIsLoadingErpSystems] = useState<boolean>(true);
  const [errorErpSystems, setErrorErpSystems] = useState<string | null>(null);

  const [progressStatuses, setProgressStatuses] = useState<ProgressStatusItem[]>([]);
  const [isLoadingProgressStatuses, setIsLoadingProgressStatuses] = useState<boolean>(false);
  const [errorProgressStatuses, setErrorProgressStatuses] = useState<string | null>(null);
  const [sourceStatusId, setSourceStatusId] = useState<string>('');
  const [targetStatusId, setTargetStatusId] = useState<string>('');

  useEffect(() => {
    const fetchErpSystems = async () => {
      setIsLoadingErpSystems(true);
      setErrorErpSystems(null);
      try {
        const response = await fetch('/api/admin/erp-systems');
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.message || `Failed to fetch ERP systems: ${response.statusText}`);
        }
        const data: ErpSystem[] = await response.json();
        setErpSystems(data);
        // Optionally, select the first ERP system by default
        // if (data.length > 0) {
        //   setSelectedErpSystemId(data[0].id);
        // }
      } catch (err: any) {
        setErrorErpSystems(err.message);
        console.error("Error fetching ERP systems:", err);
      } finally {
        setIsLoadingErpSystems(false);
      }
    };

    fetchErpSystems();
  }, []); // Runs once on component mount

  // Effect to fetch progress statuses when selectedErpSystemId changes
  useEffect(() => {
    if (!selectedErpSystemId) {
      setProgressStatuses([]);
      setSourceStatusId('');
      setTargetStatusId('');
      setErrorProgressStatuses(null);
      return;
    }

    const fetchProgressStatuses = async () => {
      setIsLoadingProgressStatuses(true);
      setErrorProgressStatuses(null);
      setSourceStatusId(''); // Reset source status on new ERP selection
      setTargetStatusId(''); // Reset target status on new ERP selection

      const selectedErp = erpSystems.find(erp => erp.id === selectedErpSystemId);
      if (!selectedErp) {
        setErrorProgressStatuses("Selected ERP system details not found.");
        setIsLoadingProgressStatuses(false);
        setProgressStatuses([]);
        return;
      }

      const { domain, apiKey } = selectedErp;
      // Ensure domain does not end with a slash and path starts with one
      const cleanDomain = domain.endsWith('/') ? domain.slice(0, -1) : domain;
      const apiUrl = `${cleanDomain}/api/v1/object/ProgressStatus`;

      try {
        const response = await fetch(apiUrl, {
          method: 'GET',
          headers: {
            'ApiKey': apiKey,
            'Accept': 'application/json', // Specify we want JSON response
          },
        });

        if (!response.ok) {
          let errorMsg = `Failed to fetch progress statuses: ${response.status} ${response.statusText}`;
          try {
            const errorData = await response.json();
            errorMsg = errorData.message || errorData.title || errorMsg;
          } catch (e) {
            // Ignore if response is not JSON
          }
          throw new Error(errorMsg);
        }

        // Assuming the response directly contains the items array or an object with a 'value' or 'items' property
        const data = await response.json();
        let items: ProgressStatusItem[] = [];
        if (Array.isArray(data)) { // Response is directly an array of items
            items = data;
        } else if (data && Array.isArray(data.items)) { // Response is an object like { items: [] }
            items = data.items;
        } else if (data && data.value && Array.isArray(data.value.items)) { // Response is an object like { value: { items: [] } } - common in OData
            items = data.value.items;
        } else if (data && data.value && Array.isArray(data.value)) { // Response is an object like { value: [] } - also common in OData for direct array
             items = data.value;
        }
         else {
          console.warn("Unexpected response structure for ProgressStatus:", data);
          throw new Error("Unexpected response structure for ProgressStatus. Expected an array of items or an object containing an items array.");
        }
        setProgressStatuses(items);

      } catch (err: any) {
        setErrorProgressStatuses(err.message);
        setProgressStatuses([]); // Clear statuses on error
        console.error("Error fetching progress statuses:", err);
      } finally {
        setIsLoadingProgressStatuses(false);
      }
    };

    fetchProgressStatuses();
  }, [selectedErpSystemId, erpSystems]);

  const handleErpSystemChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setSelectedErpSystemId(event.target.value);
  };

  const handleSourceStatusChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setSourceStatusId(event.target.value);
  };

  const handleTargetStatusChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setTargetStatusId(event.target.value);
  };

  return (
    <div>
      <h2>Configure Status Mappings</h2>

      <div style={{ margin: '20px 0' }}>
        <label htmlFor="erp-system-select" style={{ display: 'block', marginBottom: '5px' }}>Select ERP System:</label>
        {isLoadingErpSystems && <p>Loading ERP Systems...</p>}
        {errorErpSystems && <p style={{ color: 'red' }}>Error loading ERP Systems: {errorErpSystems}</p>}
        {!isLoadingErpSystems && !errorErpSystems && (
          <select
            id="erp-system-select"
            value={selectedErpSystemId}
            onChange={handleErpSystemChange}
            style={{ padding: '8px', minWidth: '300px', marginBottom: '20px' }}
          >
            <option value="">-- Select an ERP System --</option>
            {erpSystems.map((erp) => (
              <option key={erp.id} value={erp.id}>
                {erp.name} ({erp.domain})
              </option>
            ))}
          </select>
        )}
      </div>

      {selectedErpSystemId && (
        <div>
          <h3>Status Mapping for: {erpSystems.find(erp => erp.id === selectedErpSystemId)?.name || 'Selected ERP'}</h3>
          {isLoadingProgressStatuses && <p>Loading statuses...</p>}
          {errorProgressStatuses && <p style={{ color: 'red' }}>Error loading statuses: {errorProgressStatuses}</p>}

          {!isLoadingProgressStatuses && !errorProgressStatuses && progressStatuses.length > 0 && (
            <div style={{ marginTop: '20px', padding: '20px', border: '1px solid #eee' }}>
              <div style={{ marginBottom: '15px' }}>
                <label htmlFor="source-status-select" style={{ display: 'block', marginBottom: '5px' }}>Source Status (from ERP):</label>
                <select
                  id="source-status-select"
                  value={sourceStatusId}
                  onChange={handleSourceStatusChange}
                  style={{ padding: '8px', minWidth: '250px' }}
                >
                  <option value="">-- Select Source Status --</option>
                  {progressStatuses.map((status) => (
                    <option key={status.Id} value={status.Id}>
                      {status.Description} (ID: {status.Id})
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ marginBottom: '15px' }}>
                <label htmlFor="target-status-select" style={{ display: 'block', marginBottom: '5px' }}>Target Status (in Portal):</label>
                <select
                  id="target-status-select"
                  value={targetStatusId}
                  onChange={handleTargetStatusChange}
                  style={{ padding: '8px', minWidth: '250px' }}
                >
                  <option value="">-- Select Target Status --</option>
                  {progressStatuses.map((status) => ( // Using same list for now, can be different later
                    <option key={status.Id} value={status.Id}>
                      {status.Description} (ID: {status.Id})
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={() => console.log('Add mapping:', { erpId: selectedErpSystemId, source: sourceStatusId, target: targetStatusId })}
                disabled={!sourceStatusId || !targetStatusId}
                style={{ padding: '10px 15px', cursor: (!sourceStatusId || !targetStatusId) ? 'not-allowed' : 'pointer' }}
              >
                Add Mapping
              </button>
            </div>
          )}
          {!isLoadingProgressStatuses && !errorProgressStatuses && progressStatuses.length === 0 && selectedErpSystemId && (
             <p>No progress statuses found for the selected ERP system, or unable to load them.</p>
          )}
        </div>
      )}
      {!selectedErpSystemId && !isLoadingErpSystems && !errorErpSystems && (
        <p>Please select an ERP system to configure its status mappings.</p>
      )}
    </div>
  );
}
