# Slurm Client

## Requirements
1. Create fastapi user for http server
```
sudo useradd --system --create-home --shell /usr/sbin/nologin fastapi
```

2. Create shared group
```
sudo groupadd slurmfastapi
```

3. Add fastapi and slurm users to the group
```
sudo usermod -a -G slurmfastapi fastapi
sudo usermod -a -G slurmfastapi slurm
```

4. Ensure log directory exists and is owned by slurm
```
sudo mkdir -p /var/log/slurm
sudo touch /var/log/slurm/slurm_token_gen.log
sudo chown slurm:slurm /var/log/slurm/slurm_token_gen.log
sudo chmod 750 /var/log/slurm/slurm_token_gen.log
```
