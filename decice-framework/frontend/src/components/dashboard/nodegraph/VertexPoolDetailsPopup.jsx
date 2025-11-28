import { useState, useEffect } from 'react';
import Popup from 'reactjs-popup';
import { LoadingSpinner } from '../../common/LoadingSpinner';
import { ErrorMessage } from '../../common/ErrorMessage';
import './VertexPoolDetailsPopup.css';

export const VertexPoolDetailsPopup = ({ 
  isOpen, 
  onClose, 
  selectedNode, 
  updateVertexpoolLabels,
  innerError,
  innerNodes,
  innerEdges,
  innerContainerRef 
}) => {
  const [newLabelKey, setNewLabelKey] = useState('');
  const [newLabelValue, setNewLabelValue] = useState('');
  const [pendingLabels, setPendingLabels] = useState([]);
  const [deletingLabel, setDeletingLabel] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  useEffect(() => {
    if (selectedNode?.labels) {
      setPendingLabels(selectedNode.labels);
    }
  }, [selectedNode]);

  const handleDeleteLabel = (index) => {
    setDeletingLabel(index);
  };

  const confirmDelete = (index) => {
    const newLabels = pendingLabels.filter((_, i) => i !== index);
    setPendingLabels(newLabels);
    setDeletingLabel(null);
  };

  const cancelDelete = () => {
    setDeletingLabel(null);
  };

  const handleAddLabel = () => {
    if (newLabelKey) {
      const newLabel = newLabelValue ? `${newLabelKey}:${newLabelValue}` : newLabelKey;
      setPendingLabels([...pendingLabels, newLabel]);
      setNewLabelKey('');
      setNewLabelValue('');
    }
  };

  const handleSaveChanges = async () => {
    setIsSaving(true);
    setSaveError(null);
    
    try {
      const formattedLabels = pendingLabels.map(label => {
        const [k, v] = label.split(':');
        return {
          label_key: k,
          label_value: v || ''
        };
      });
      
      await updateVertexpoolLabels(selectedNode.vertexpool_id, formattedLabels);
      
      // Yerel state'i güncelle
      if (selectedNode) {
        selectedNode.labels = [...pendingLabels];
      }
      
      // Başarılı kaydetme sonrası geçici bir başarı mesajı göster
      const saveButton = document.getElementById('save-button');
      if (saveButton) {
        saveButton.textContent = '✓ Saved';
        saveButton.classList.remove('bg-green-500', 'hover:bg-green-600');
        saveButton.classList.add('bg-green-600', 'cursor-default');
        
        setTimeout(() => {
          if (saveButton) {
            saveButton.textContent = 'Save Changes';
            saveButton.classList.remove('bg-green-600', 'cursor-default');
            saveButton.classList.add('bg-green-500', 'hover:bg-green-600');
          }
        }, 2000);
      }
    } catch (error) {
      setSaveError('Failed to save changes. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const hasChanges = JSON.stringify(selectedNode?.labels) !== JSON.stringify(pendingLabels);

  return (
    <Popup
      open={isOpen}
      onClose={onClose}
      modal
      className="vertex-pool-popup"
    >
      <div className="w-full max-w-5xl bg-white dark:bg-gray-900 rounded-lg shadow-xl">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-200">VertexPool ID: {selectedNode?.id}</div>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <div className="mb-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-200">Labels</h3>
            </div>
            
            <div className="labels-container">
              <div className="labels-grid custom-scrollbar">
                {pendingLabels.map((label, index) => {
                  const [key, value] = label.split(':');
                  return (
                    <div key={index} className="label-item">
                      <div className="label-content">
                        <span className="label-key">{key}</span>
                        {value && <span className="label-separator">:</span>}
                        <span className="label-value">{value || ''}</span>
                      </div>
                      {deletingLabel === index ? (
                        <div className="label-actions">
                          <button
                            onClick={() => confirmDelete(index)}
                            className="text-red-600 hover:text-red-700 dark:text-red-500 dark:hover:text-red-400 transition-colors text-sm"
                          >
                            Confirm
                          </button>
                          <button
                            onClick={cancelDelete}
                            className="text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200 transition-colors text-sm ml-2"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => handleDeleteLabel(index)}
                          className="label-delete"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>

              <div className="flex gap-3 mt-6">
                <input
                  type="text"
                  placeholder="Key"
                  className="flex-1 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-200 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 border border-gray-200 dark:border-gray-600"
                  value={newLabelKey}
                  onChange={(e) => setNewLabelKey(e.target.value)}
                />
                <input
                  type="text"
                  placeholder="Value"
                  className="flex-1 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-200 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 border border-gray-200 dark:border-gray-600"
                  value={newLabelValue}
                  onChange={(e) => setNewLabelValue(e.target.value)}
                />
                <button
                  onClick={handleAddLabel}
                  disabled={!newLabelKey}
                  className={`px-6 py-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors ${
                    newLabelKey 
                      ? 'bg-blue-500 text-white hover:bg-blue-600' 
                      : 'bg-gray-100 dark:bg-gray-600 text-gray-400 cursor-not-allowed'
                  }`}
                >
                  Add
                </button>
              </div>
            </div>

            {hasChanges && (
              <div className="mt-6">
                {saveError && (
                  <div className="mb-2 text-red-600 dark:text-red-500 text-sm">{saveError}</div>
                )}
                <div className="flex justify-end">
                  <button
                    id="save-button"
                    onClick={handleSaveChanges}
                    disabled={isSaving}
                    className={`px-6 py-3 bg-green-500 text-white rounded-lg hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-green-500 transition-all ${
                      isSaving ? 'opacity-75 cursor-not-allowed' : ''
                    }`}
                  >
                    {isSaving ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {innerError ? (
          <ErrorMessage message={innerError} />
        ) : !innerNodes || !innerEdges ? (
          <LoadingSpinner />
        ) : (
          <div ref={innerContainerRef} className="w-full h-[calc(100%-8rem)]" />
        )}
      </div>
    </Popup>
  );
}; 