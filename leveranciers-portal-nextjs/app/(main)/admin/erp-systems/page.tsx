'use client';

import React, { useState, FormEvent } from 'react';

export default function ErpSystemsAdminPage() {
  const [name, setName] = useState('');
  const [domain, setDomain] = useState('');
  const [apiKey, setApiKey] = useState('');

  const handleAddErpSystem = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    console.log('Adding ERP System:', { name, domain, apiKey });
    // Reset form fields after submission (optional)
    setName('');
    setDomain('');
    setApiKey('');
    alert('ERP System details logged to console. Check browser developer tools.');
  };

  return (
    <div>
      <h2>Manage ERP Systems</h2>

      <form onSubmit={handleAddErpSystem} style={{ margin: '20px 0', padding: '20px', border: '1px solid #ccc' }}>
        <h3>Add New ERP System</h3>
        <div style={{ marginBottom: '10px' }}>
          <label htmlFor="erp-name" style={{ marginRight: '10px' }}>Name:</label>
          <input
            type="text"
            id="erp-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            style={{ padding: '5px' }}
          />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label htmlFor="erp-domain" style={{ marginRight: '10px' }}>Domain:</label>
          <input
            type="text"
            id="erp-domain"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="https://example.ultimo.com"
            required
            style={{ padding: '5px' }}
          />
        </div>
        <div style={{ marginBottom: '10px' }}>
          <label htmlFor="erp-apiKey" style={{ marginRight: '10px' }}>API Key:</label>
          <input
            type="text"
            id="erp-apiKey"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            required
            style={{ padding: '5px' }}
          />
        </div>
        <button type="submit" style={{ padding: '8px 15px' }}>Add ERP System</button>
      </form>

      <div>
        <h3>Existing ERP Systems</h3>
        <div>ERP systems list will appear here.</div>
      </div>
    </div>
  );
}
