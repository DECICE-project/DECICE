import { useState } from 'react';
import {
  Tabs,
  Tab,
  Button,
  Card,
  CardBody,
  Textarea,
  Spacer,
  Kbd,
  Progress
} from '@nextui-org/react';
import { useSelector } from 'react-redux';
import { toast } from 'react-toastify';



function JobPost() {
  const serverIP = useSelector((state) => state.serverIP.value);
  const authToken = useSelector((state) => state.authToken.value);
  const [selectedTab, setSelectedTab] = useState('form');

  const [inputFile, setInputFile] = useState(null);
  const [definitionFile, setDefinitionFile] = useState(null);
  const [workflowName, setWorkflowName] = useState('');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [storageFilename, setStorageFilename] = useState('');
  const [workflowJson, setWorkflowJson] = useState('');
  const [inputFileKey, setInputFileKey] = useState(0);
  const [definitionFileKey, setDefinitionFileKey] = useState(0);
  const [error, setError] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  const handleInputFileChange = (event) => {
    const file = event.target.files?.[0] || null;
    setInputFile(file);
    if (!file) {
      setStorageFilename('');
    }
  };

  const handleDefinitionFileChange = (event) => {
    const file = event.target.files?.[0] || null;
    setDefinitionFile(file);
  };

  const handleSubmit = async () => {
    setError(null);

    if (!authToken) {
      setError('User is not authenticated.');
      return;
    }

    if (!definitionFile) {
      setError('Please upload a deployment file.');
      return;
    }

    let workflowPayload;

    if (selectedTab === 'form') {
      const trimmedName = workflowName.trim();
      if (!trimmedName) {
        setError('Please provide a workflow name.');
        return;
      }

      if (inputFile && !storageFilename.trim()) {
        setError('Storage filename is required when uploading an input file.');
        return;
      }

      workflowPayload = {
        name: trimmedName,
      };

      const trimmedDescription = workflowDescription.trim();
      if (trimmedDescription) {
        workflowPayload.description = trimmedDescription;
      }

      if (inputFile) {
        workflowPayload.storage_filename = storageFilename.trim();
      }
    } else {
      let parsed;
      try {
        parsed = JSON.parse(workflowJson);
      } catch (err) {
        setError('Invalid JSON payload. Please provide valid JSON.');
        return;
      }

      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        setError('Workflow JSON must be an object.');
        return;
      }

      const trimmedName = typeof parsed.name === 'string' ? parsed.name.trim() : '';
      if (!trimmedName) {
        setError('Workflow name is required in JSON payload.');
        return;
      }

      const payload = { ...parsed, name: trimmedName };

      if (payload.description === '') {
        delete payload.description;
      }

      if (inputFile) {
        if (typeof payload.storage_filename !== 'string' || !payload.storage_filename.trim()) {
          setError('Storage filename is required when uploading an input file.');
          return;
        }
        payload.storage_filename = payload.storage_filename.trim();
      } else if ('storage_filename' in payload) {
        delete payload.storage_filename;
      }

      workflowPayload = payload;
    }

    setIsUploading(true);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('definition_file', definitionFile);
    formData.append('workflow', JSON.stringify(workflowPayload));

    try {
      const response = await fetch(`http://${serverIP}/v1/workflow/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to submit workflow.');
      }

      const data = await response.json();
      setUploadProgress(inputFile ? 20 : 100);

      if (inputFile) {
        if (data.presigned_url) {
          await new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.upload.addEventListener('progress', (event) => {
              if (event.lengthComputable) {
                const progress = 20 + Math.round((event.loaded / event.total) * 80);
                setUploadProgress(progress);
              }
            });
            xhr.onload = () => {
              if (xhr.status >= 200 && xhr.status < 300) {
                resolve();
              } else {
                reject(new Error('Input file upload failed.'));
              }
            };
            xhr.onerror = () => reject(new Error('Input file upload failed.'));
            xhr.open('PUT', data.presigned_url);
            xhr.send(inputFile);
          });
          setUploadProgress(100);
          toast.success('Input file uploaded successfully!', { position: 'bottom-right' });
        } else {
          toast.warn('Workflow created, but no presigned URL was returned for the input file.', {
            position: 'bottom-right',
          });
        }
      }

      toast.success('Workflow uploaded successfully!', { position: 'bottom-right' });

      // Reset state
      setWorkflowName('');
      setWorkflowDescription('');
      setStorageFilename('');
      setWorkflowJson('');
      setInputFile(null);
      setDefinitionFile(null);
      setInputFileKey((prev) => prev + 1);
      setDefinitionFileKey((prev) => prev + 1);
      setUploadProgress(100);
    } catch (err) {
      setError(err.message);
      toast.error(err.message, {
        position: 'bottom-right',
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div>
      <h2 className="mb-3 font-semibold">Input File (optional)</h2>
      <div className="mb-4">

        <input
          key={inputFileKey}
       // className="mb-3 w-full text-gray-500 font-medium text-sm sm:text-lg bg-gray-100 file:cursor-not-allowed file:border-0 file:py-3 file:px-4 file:mr-4 file:bg-gray-300 file:text-gray-400 rounded-3xl"
          className="mb-3 w-full text-gray-500 font-medium text-sm sm:text-lg bg-gray-100 file:cursor-pointer cursor-pointer file:border-0 file:py-3 file:px-4 file:mr-4 file:bg-gray-800 file:hover:bg-gray-700 file:text-white rounded-3xl"
          type="file"
          onChange={handleInputFileChange}
          // disabled
        />
        {inputFile && <Kbd>{inputFile.name}</Kbd>}
      </div>

      <h2 className="mb-3 mt-7 font-semibold">Deployment File</h2>
      <div className="mb-4">
      
        <input  
        key={definitionFileKey}
        className="mb-3 w-full text-gray-500 font-medium text-sm sm:text-lg bg-gray-100 file:cursor-pointer cursor-pointer file:border-0 file:py-3 file:px-4 file:mr-4 file:bg-gray-800 file:hover:bg-gray-700 file:text-white rounded-3xl"
        type="file" 
        onChange={handleDefinitionFileChange} 
        />
        {definitionFile && <Kbd>{definitionFile.name}</Kbd> }
      </div>

      <h2 className="mb-3 mt-7 font-semibold">Workflow Details</h2>

      <div className="flex flex-col w-full">
        <Card className="max-w-full w-full">
          <CardBody className="overflow-hidden">
            <Tabs
              fullWidth
              size="md"
              aria-label="Workflow configuration"
              selectedKey={selectedTab}
              onSelectionChange={setSelectedTab}
            >
              <Tab key="form" title="Upload with Form">
                <div className="mt-4">
                  <input
                 className="form-input w-full py-2 dark:text-black"
                    label="Name"
                    name="name"
                    value={workflowName}
                    onChange={(e) => setWorkflowName(e.target.value)}
                    placeholder="Enter workflow name"

                  />
                  <Spacer y={0.5} />
                  <input
                   className="form-input w-full py-2 dark:text-black"
                    label="Description"
                    name="description"
                    value={workflowDescription}
                    onChange={(e) => setWorkflowDescription(e.target.value)}
                    placeholder="Enter workflow description (optional)"
                  />
                  <Spacer y={0.5} />
                  <input
                   className="form-input w-full py-2 dark:text-black disabled:bg-gray-200 disabled:text-gray-500"
                    label="Storage Filename"
                    name="storage_filename"
                    value={storageFilename}
                    onChange={(e) => setStorageFilename(e.target.value)}
                    placeholder="Enter storage filename for the input file"
                    disabled={!inputFile}
                  />
                  <p className="text-xs text-default-500 mt-1">
                    Provide a storage filename only when uploading an additional input file.
                  </p>
                </div>
              </Tab>
              <Tab key="json" title="Upload with JSON">
                <Textarea
                  minRows={11}
                  label="Workflow JSON"
                  placeholder='{
  "name": "workflow-name",
  "description": "optional description",
  "storage_filename": "optional-input-file-name"
}'
                  value={workflowJson}
                  onChange={(e) => setWorkflowJson(e.target.value)}
                  fullWidth
                />
              </Tab>
            </Tabs>
          </CardBody>
        </Card>
      </div>

      {error && <p className="text-red-500 mt-4">{error}</p>}

      {isUploading && (
        <Progress
          size="sm"
          value={uploadProgress}
          className="mt-4"
          color="primary"
        />
      )}

      <Button 
        className="w-full mt-3" 
        onClick={handleSubmit}
        isLoading={isUploading}
      >
        {isUploading ? 'Uploading...' : 'Send'}
      </Button>
    </div>
  );
}

export default JobPost;
