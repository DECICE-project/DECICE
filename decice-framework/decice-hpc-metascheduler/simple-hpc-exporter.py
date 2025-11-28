#!/usr/bin/env python3
"""
Simple Remote HPC Metrics Exporter
Uses standard SLURM commands to collect metrics from remote HPC cluster
"""
import subprocess
import json
import time
import re
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleHPCCollector:
    def __init__(self, hpc_host="192.168.23.14"):
        self.hpc_host = hpc_host
        self.cache = {}
        self.cache_ttl = 30
        self.last_update = 0
    
    def run_ssh_command(self, command):
        """Execute command on remote HPC via SSH"""
        try:
            ssh_cmd = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {self.hpc_host} '{command}'"
            result = subprocess.run(ssh_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                  universal_newlines=True, timeout=15)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"SSH command failed: {command}")
                return None
        except Exception as e:
            print(f"SSH error: {e}")
            return None
    
    def parse_sinfo(self):
        """Parse sinfo output to get detailed CPU and Memory information"""
        # Get detailed resource information
        output = self.run_ssh_command('sinfo -o "%P %A %C %m %e %T"')
        if not output:
            return {}
        
        partitions = {}
        total_stats = {"idle": 0, "alloc": 0, "mix": 0, "down": 0, "total": 0}
        
        # CPU and Memory statistics
        total_cpus = {"allocated": 0, "idle": 0, "other": 0, "total": 0}
        total_memory = {"total_mb": 0, "free_mb": 0, "allocated_mb": 0, "nodes": 0}
        
        lines = output.split('\n')[1:]  # Skip header
        for line in lines:
            if line.strip():
                parts = line.split()
                if len(parts) >= 6:
                    partition = parts[0].rstrip('*')
                    
                    # Only include cn-eth and cn-ib partitions (cn09-cn28)
                    # Skip: cn-kube (k8s nodes cn01-08), a800-9000 (ml01), a800-3000 (ml02)
                    if partition not in ["cn-eth", "cn-ib"]:
                        continue
                    
                    nodes_info = parts[1]  # Format: avail/idle
                    cpus_info = parts[2]   # Format: allocated/idle/other/total
                    memory_per_node = parts[3]  # Memory per node in MB
                    free_memory_range = parts[4]  # Free memory range
                    state = parts[5]
                    
                    # Parse node counts
                    if '/' in nodes_info:
                        avail_nodes, idle_nodes = map(int, nodes_info.split('/'))
                        nodes = avail_nodes + idle_nodes
                    else:
                        nodes = int(nodes_info)
                    
                    # Parse CPU information (allocated/idle/other/total)
                    try:
                        cpu_parts = cpus_info.split('/')
                        if len(cpu_parts) == 4:
                            cpu_allocated, cpu_idle, cpu_other, cpu_total = map(int, cpu_parts)
                            
                            total_cpus["allocated"] += cpu_allocated
                            total_cpus["idle"] += cpu_idle
                            total_cpus["other"] += cpu_other
                            total_cpus["total"] += cpu_total
                    except (ValueError, IndexError):
                        pass
                    
                    # Parse memory information
                    try:
                        memory_per_node_mb = int(memory_per_node)
                        total_memory["total_mb"] += memory_per_node_mb * nodes
                        total_memory["nodes"] += nodes
                        
                        # Parse free memory range (e.g., "11945-108880" or "N/A")
                        if free_memory_range != "N/A" and '-' in free_memory_range:
                            free_parts = free_memory_range.split('-')
                            if len(free_parts) == 2:
                                # Use average of min and max free memory
                                min_free = int(free_parts[0])
                                max_free = int(free_parts[1])
                                avg_free_per_node = (min_free + max_free) / 2
                                total_memory["free_mb"] += avg_free_per_node * nodes
                    except (ValueError, IndexError):
                        pass
                    
                    # Track partition states
                    if partition not in partitions:
                        partitions[partition] = {"idle": 0, "alloc": 0, "mix": 0, "down": 0, "total": 0}
                    
                    # Normalize state names
                    if "down" in state.lower():
                        state = "down"
                    elif "mixed" in state.lower():
                        state = "mix"
                    elif "allocated" in state.lower():
                        state = "alloc"
                    elif "idle" in state.lower():
                        state = "idle"
                    
                    partitions[partition][state] = partitions[partition].get(state, 0) + nodes
                    partitions[partition]["total"] += nodes
                    
                    total_stats[state] = total_stats.get(state, 0) + nodes
                    total_stats["total"] += nodes
        
        # Calculate utilization percentages
        node_utilization = ((total_stats.get("alloc", 0) + total_stats.get("mix", 0)) / max(total_stats["total"], 1)) * 100
        cpu_utilization = (total_cpus["allocated"] / max(total_cpus["total"], 1)) * 100
        
        # Calculate memory utilization
        total_memory["allocated_mb"] = total_memory["total_mb"] - total_memory["free_mb"]
        memory_utilization = (total_memory["allocated_mb"] / max(total_memory["total_mb"], 1)) * 100
        
        return {
            "partitions": partitions,
            "total_nodes": total_stats,
            "node_utilization": round(node_utilization, 2),
            "cpu_utilization": round(cpu_utilization, 2),
            "memory_utilization": round(memory_utilization, 2),
            "cpu_stats": total_cpus,
            "memory_stats": total_memory,
            "utilization": round(node_utilization, 2),  # Keep for backward compatibility
            "available": total_stats.get("idle", 0),
            "busy": total_stats.get("alloc", 0) + total_stats.get("mix", 0)
        }
    
    def parse_squeue(self):
        """Parse squeue output"""
        output = self.run_ssh_command("squeue")
        if not output:
            return {}
        
        jobs = {"total": 0, "running": 0, "pending": 0, "by_partition": {}}
        
        lines = output.split('\n')[1:]  # Skip header
        for line in lines:
            if line.strip():
                parts = line.split()
                if len(parts) >= 6:
                    partition = parts[1]
                    state = parts[4]
                    
                    jobs["total"] += 1
                    
                    if state == "R":
                        jobs["running"] += 1
                    elif state in ["PD", "CG"]:
                        jobs["pending"] += 1
                    
                    if partition not in jobs["by_partition"]:
                        jobs["by_partition"][partition] = {"total": 0, "running": 0, "pending": 0}
                    
                    jobs["by_partition"][partition]["total"] += 1
                    if state == "R":
                        jobs["by_partition"][partition]["running"] += 1
                    elif state in ["PD", "CG"]:
                        jobs["by_partition"][partition]["pending"] += 1
        
        return jobs
    
    def collect_metrics(self):
        """Collect all metrics"""
        current_time = time.time()
        
        if current_time - self.last_update < self.cache_ttl and self.cache:
            return self.cache
        
        print(f"[{datetime.now().isoformat()}] Collecting HPC metrics...")
        
        cluster_info = self.parse_sinfo()
        job_info = self.parse_squeue()
        
        metrics = {
            "timestamp": current_time,
            "hpc_host": self.hpc_host,
            "cluster": cluster_info,
            "jobs": job_info
        }
        
        self.cache = metrics
        self.last_update = current_time
        
        return metrics
    
    def generate_prometheus_metrics(self):
        """Generate Prometheus metrics"""
        data = self.collect_metrics()
        
        lines = []
        lines.append("# HELP remote_hpc_info Remote HPC cluster metrics")
        lines.append("# TYPE remote_hpc_info gauge")
        
        cluster = data["cluster"]
        jobs = data["jobs"]
        host = self.hpc_host
        
        # Detailed CPU and Memory metrics (for unified load calculation)
        lines.append("# HELP remote_hpc_cpu_utilization_percent CPU utilization percentage")
        lines.append("# TYPE remote_hpc_cpu_utilization_percent gauge")
        lines.append(f'remote_hpc_cpu_utilization_percent{{host="{host}"}} {cluster.get("cpu_utilization", 0)}')
        
        lines.append("# HELP remote_hpc_memory_utilization_percent Memory utilization percentage")
        lines.append("# TYPE remote_hpc_memory_utilization_percent gauge")
        lines.append(f'remote_hpc_memory_utilization_percent{{host="{host}"}} {cluster.get("memory_utilization", 0)}')
        
        # Legacy/compatibility metrics
        lines.append(f'remote_hpc_utilization_percent{{host="{host}"}} {cluster.get("utilization", 0)}')
        lines.append(f'remote_hpc_nodes_total{{host="{host}"}} {cluster.get("total_nodes", {}).get("total", 0)}')
        lines.append(f'remote_hpc_nodes_idle{{host="{host}"}} {cluster.get("available", 0)}')
        lines.append(f'remote_hpc_nodes_busy{{host="{host}"}} {cluster.get("busy", 0)}')
        
        # Detailed CPU breakdown
        cpu_stats = cluster.get("cpu_stats", {})
        lines.append(f'remote_hpc_cpu_allocated{{host="{host}"}} {cpu_stats.get("allocated", 0)}')
        lines.append(f'remote_hpc_cpu_idle{{host="{host}"}} {cpu_stats.get("idle", 0)}')
        lines.append(f'remote_hpc_cpu_total{{host="{host}"}} {cpu_stats.get("total", 0)}')
        
        # Detailed Memory breakdown  
        memory_stats = cluster.get("memory_stats", {})
        lines.append(f'remote_hpc_memory_allocated_mb{{host="{host}"}} {memory_stats.get("allocated_mb", 0)}')
        lines.append(f'remote_hpc_memory_free_mb{{host="{host}"}} {memory_stats.get("free_mb", 0)}')
        lines.append(f'remote_hpc_memory_total_mb{{host="{host}"}} {memory_stats.get("total_mb", 0)}')
        
        # Job metrics
        lines.append(f'remote_hpc_jobs_total{{host="{host}"}} {jobs.get("total", 0)}')
        lines.append(f'remote_hpc_jobs_running{{host="{host}"}} {jobs.get("running", 0)}')
        lines.append(f'remote_hpc_jobs_pending{{host="{host}"}} {jobs.get("pending", 0)}')
        
        # Load score for meta-scheduler (0-100, higher = more loaded)
        # Use detailed CPU and Memory utilization if available
        cpu_util = cluster.get("cpu_utilization", 0)
        memory_util = cluster.get("memory_utilization", 0)
        pending_jobs = jobs.get("pending", 0)
        
        # Unified load calculation (same formula as Volcano)
        # CPU 40% + Memory 40% + Queue 20%
        cpu_score = cpu_util * 0.4
        memory_score = memory_util * 0.4
        queue_score = min(20, pending_jobs * 2) * 0.2  # Max 20 points for queue
        
        load_score = cpu_score + memory_score + queue_score
        capacity_score = max(0, 100 - load_score)
        
        lines.append(f'remote_hpc_load_score{{host="{host}"}} {load_score:.1f}')
        lines.append(f'remote_hpc_capacity_score{{host="{host}"}} {capacity_score:.1f}')
        
        return "\n".join(lines)

class MetricsHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, collector=None, **kwargs):
        self.collector = collector
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            metrics = self.collector.generate_prometheus_metrics()
            self.wfile.write(metrics.encode())
        
        elif self.path == "/health":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            health = {"status": "healthy", "host": self.collector.hpc_host}
            self.wfile.write(json.dumps(health).encode())
        
        elif self.path == "/api":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            data = self.collector.collect_metrics()
            self.wfile.write(json.dumps(data, indent=2).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        print(f"[{datetime.now().isoformat()}] {format % args}")

def main():
    collector = SimpleHPCCollector()
    
    # Test connection
    print("Testing HPC connection...")
    test_data = collector.collect_metrics()
    
    if not test_data["cluster"] or test_data["cluster"]["total_nodes"]["total"] == 0:
        print("ERROR: Cannot collect HPC data!")
        return
    
    print(f"✅ Connected to HPC cluster {collector.hpc_host}")
    print(f"   Total nodes: {test_data['cluster']['total_nodes']['total']}")
    print(f"   Utilization: {test_data['cluster']['utilization']}%")
    print(f"   Running jobs: {test_data['jobs']['running']}")
    
    # Start server
    port = 8092
    def handler(*args, **kwargs):
        return MetricsHandler(*args, collector=collector, **kwargs)
    
    httpd = HTTPServer(("0.0.0.0", port), handler)
    print(f"🚀 Simple HPC Exporter running on port {port}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down")

if __name__ == "__main__":
    main()
