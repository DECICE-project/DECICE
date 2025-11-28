import React, { useState } from 'react';

export const SearchField = ({ onSearch, data }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [showResults, setShowResults] = useState(false);
  const [results, setResults] = useState([]);

  const handleSearch = (e) => {
    const term = e.target.value;
    setSearchTerm(term);
    
    if (term.length < 2) {
      setResults([]);
      setShowResults(false);
      return;
    }

    const searchResults = data.reduce((acc, pool) => {
      const nodes = pool.nodes?.filter(node => 
        node.nodename.includes(term)
      ) || [];
      
      const devices = pool.devices?.filter(device => 
        device.name.toLowerCase().includes(term.toLowerCase())
      ) || [];

      if (nodes.length > 0 || devices.length > 0) {
        acc.push({
          poolId: pool.vertexpool_id,
          poolLabels: pool.labels || [],
          nodes,
          devices
        });
      }
      
      return acc;
    }, []);

    setResults(searchResults);
    setShowResults(true);
  };

  const handleResultClick = (result) => {
    onSearch(result);
    setSearchTerm('');
    setShowResults(false);
    setResults([]);
  };

  return (
    <div className="relative w-full max-w-md">
      <div className="relative">
        <input
          type="text"
          value={searchTerm}
          onChange={handleSearch}
          placeholder="Search Node, Device"
          className="w-full px-4 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-white"
        />
        <div className="absolute inset-y-0 right-0 flex items-center pr-3">
          <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>

      {showResults && results.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-96 overflow-y-auto">
          {results.map((result, index) => (
            <div key={index} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer">
              <div className="text-sm font-semibold text-gray-900 dark:text-white">
                VertexPool ID: {result.poolId}
              </div>
              {result.poolLabels?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1">
                  {result.poolLabels.map((label, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-100 rounded-full text-xs"
                    >
                      {label}
                    </span>
                  ))}
                </div>
              )}
              {result.nodes.length > 0 && (
                <div className="mt-1">
                  <div className="text-xs font-medium text-gray-500 dark:text-gray-400">Nodes:</div>
                  {result.nodes.map((node, idx) => (
                    <div
                      key={idx}
                      className="text-sm text-gray-700 dark:text-gray-300"
                    >
                      {node.nodename}
                    </div>
                  ))}
                </div>
              )}
              {result.devices.length > 0 && (
                <div className="mt-1">
                  <div className="text-xs font-medium text-gray-500 dark:text-gray-400">Devices:</div>
                  {result.devices.map((device, idx) => (
                    <div
                      key={idx}
                      className="text-sm text-gray-700 dark:text-gray-300"
                    >
                      {device.name}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}; 