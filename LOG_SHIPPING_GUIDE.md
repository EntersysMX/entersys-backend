# Six Sigma Log Shipping Configuration Guide

This guide explains how to configure log shipping from your local FastAPI backend to the remote Loki instance for Six Sigma dashboard integration.

## Overview

The backend generates Six Sigma logs in these files:
- `logs/six_sigma_performance.log` - Performance metrics and SLA compliance
- `logs/six_sigma_errors.log` - Error tracking and failure analysis
- `logs/six_sigma_requests.log` - Request lifecycle tracking
- `logs/six_sigma_sla.log` - SLA breach notifications

## Configuration Files Created

### 1. Promtail Configuration (`promtail-remote-config.yml`)

This configuration file is set up to:
- Monitor all Six Sigma log files
- Parse JSON-structured logs
- Extract relevant labels for dashboard filtering
- Ship logs to remote Loki at `http://34.59.193.54:3100`

### 2. Setup Script (`setup_log_shipping.py`)

Automated setup script that:
- Downloads Promtail binary
- Validates configuration
- Starts log shipping service
- Tests connectivity

## Manual Setup Instructions

Since the remote Loki instance may have network restrictions, here are manual setup steps:

### Step 1: Download Promtail

```bash
# For Windows
curl -L -o promtail.exe.zip https://github.com/grafana/loki/releases/latest/download/promtail-windows-amd64.exe.zip
unzip promtail.exe.zip
mv promtail-windows-amd64.exe promtail.exe

# For Linux/Mac
curl -L -o promtail.zip https://github.com/grafana/loki/releases/latest/download/promtail-linux-amd64.zip
unzip promtail.zip
mv promtail-linux-amd64 promtail
chmod +x promtail
```

### Step 2: Test Configuration

```bash
# Validate configuration
./promtail -config.file promtail-remote-config.yml -dry-run
```

### Step 3: Start Promtail

```bash
# Start Promtail (Linux/Mac)
./promtail -config.file promtail-remote-config.yml &
```

### Step 4: Verify Log Shipping

Check that logs are being sent by monitoring the Promtail output and verifying data in Grafana dashboards.

## Network Configuration

### Firewall Requirements

Ensure outbound connectivity to:
- `34.59.193.54:3100` (Loki ingestion endpoint)

### Alternative Configuration

If direct connectivity is not available, you can:

1. **Use SSH Tunnel:**
   ```bash
   ssh -L 3100:34.59.193.54:3100 user@jumphost
   # Then change config to use localhost:3100
   ```

2. **Use VPN Connection:**
   Connect to your production network via VPN

3. **Modify Network Settings:**
   Update the Promtail config to use different endpoint if needed

## Log Structure

### Six Sigma Performance Logs

```json
{
  "timestamp": "2025-09-25T05:26:47.665104+00:00",
  "level": "INFO",
  "logger": "six_sigma.performance",
  "message": {
    "event_type": "performance_metric",
    "request_id": "req_445986e03469",
    "service": "system_health",
    "operation": "health_check",
    "duration_ms": 4082.991,
    "performance_category": "poor",
    "sla_compliant": false,
    "quality_level": "three_sigma",
    "performance_score": 50
  }
}
```

### Six Sigma Error Logs

```json
{
  "timestamp": "2025-09-25T05:26:58.604525+00:00",
  "level": "ERROR",
  "logger": "six_sigma.errors",
  "message": {
    "event_type": "request_completion",
    "request_id": "req_da58888ebae0",
    "status_code": 404,
    "is_successful": false,
    "error_category": "client_error",
    "six_sigma_metrics": {
      "error_type": "resource_not_found",
      "defect_count": 1,
      "success_rate": 0.0
    },
    "service_info": {
      "service": "unknown",
      "operation": "unknown",
      "business_function": "unknown"
    }
  }
}
```

## Dashboard Integration

Once logs are shipping, they will be available in Grafana with these labels:

- `service="entersys-backend"`
- `component="six-sigma"`
- `log_type="performance|errors|requests|sla"`
- `quality_level="six_sigma|five_sigma|four_sigma|three_sigma"`
- `sla_breach="true|false"`
- `error_category="client_error|server_error|none"`

## Monitoring Commands

### Check Promtail Status

```bash
# Windows
tasklist | findstr promtail

# Linux/Mac
ps aux | grep promtail
```

### View Log Shipping Stats

```bash
# Check Promtail metrics (if running on port 9080)
curl http://localhost:9080/metrics
```

### Test Remote Loki Connectivity

```bash
# Test Loki ready endpoint
curl http://34.59.193.54:3100/ready

# Test log query
curl "http://34.59.193.54:3100/loki/api/v1/query?query={service=\"entersys-backend\"}"
```

## Troubleshooting

### Common Issues

1. **Connection Timeout:** Check firewall and network connectivity
2. **Permission Issues:** Ensure Promtail has read access to log files
3. **Configuration Errors:** Validate YAML syntax and paths
4. **Log Format Issues:** Verify JSON structure matches expected format

### Debug Commands

```bash
# Test configuration
./promtail -config.file promtail-remote-config.yml -dry-run

# Run with debug logging
./promtail -config.file promtail-remote-config.yml -log.level=debug

# Check log file permissions
ls -la logs/six_sigma_*.log
```

## Performance Considerations

- Log files are monitored in real-time
- Network bandwidth usage depends on log volume
- Consider log rotation to manage disk space
- Monitor Promtail resource usage

## Security

- No sensitive data is included in logs (credentials are redacted)
- Transport is HTTP (consider HTTPS for production)
- Access control handled by Loki instance
- Log retention managed by Loki configuration