# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react/README.md) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

# Running the Dashboard Server

All respective DECICE services needs to be running with publically accesiable URLs to client browser before running dashboard.
## Locally
### Setup env variables
Ensure that the `.env` file is correctly set before starting the application.
```sh
cp .env.example .env
vim .env
```
#### .env file variables
- **`VITE_SERVER_IP`**: Specifies the IP and port of the DECICE Control Manager, which serves the client requests.
- **`VITE_WATMON_API_IP`**: WATMON-Network Service, Used for Vertexpool/Device Management. Provides Network Measurement information to Network Page of the dashboard.
- **`VITE_GRAFANA_URL`**: Defines the URL of the Grafana dashboard for monitoring Compute Plane metrics.

### Installs dependencies and Run dev server
```sh
npm install
npm run dev -- --host
```

## In Kubernetes via Helm Charts.

```bash
# Run all other DECICE services.
# Get Helm values
helm show values ./chart/ >> dashboard-helm.yml
# Edit Helm values
vim dashboard-helm.yml
# Install via Helm
helm upgrade --install -n decice dashboard ./chart/ -f dashboard-helm.yml --create-namespace

```
