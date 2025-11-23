#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log Shipping Setup Script for Entersys Backend
Configures Promtail to ship Six Sigma logs to remote Loki instance
"""

import os
import sys
import subprocess
import requests
import time
import json
import platform
from pathlib import Path

# Set UTF-8 encoding for Windows console
if platform.system() == "Windows":
    import locale
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8')

class LogShippingSetup:
    def __init__(self):
        self.current_dir = Path(__file__).parent
        self.logs_dir = self.current_dir / "logs"
        self.remote_loki_url = "http://34.59.193.54:3100"
        self.promtail_config = self.current_dir / "promtail-remote-config.yml"
        self.is_windows = platform.system() == "Windows"

    def check_remote_loki_connectivity(self):
        """Check if remote Loki instance is accessible"""
        print("🔍 Checking connectivity to remote Loki instance...")

        try:
            # Test Loki ready endpoint
            response = requests.get(f"{self.remote_loki_url}/ready", timeout=10)
            if response.status_code == 200:
                print(f"✅ Remote Loki at {self.remote_loki_url} is accessible")
                return True
            else:
                print(f"❌ Remote Loki returned status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot connect to remote Loki: {e}")
            return False

    def check_log_files_exist(self):
        """Check if Six Sigma log files exist"""
        print("📋 Checking if Six Sigma log files exist...")

        required_logs = [
            "six_sigma_performance.log",
            "six_sigma_errors.log",
            "six_sigma_requests.log"
        ]

        existing_logs = []
        for log_file in required_logs:
            log_path = self.logs_dir / log_file
            if log_path.exists():
                size = log_path.stat().st_size
                print(f"✅ Found {log_file} ({size} bytes)")
                existing_logs.append(log_file)
            else:
                print(f"⚠️  {log_file} does not exist yet")

        if existing_logs:
            print(f"📊 Found {len(existing_logs)} Six Sigma log files")
            return True
        else:
            print("❌ No Six Sigma log files found. Make sure the backend is running and generating logs.")
            return False

    def download_promtail(self):
        """Download Promtail binary if not exists"""
        print("📥 Setting up Promtail...")

        if self.is_windows:
            promtail_binary = self.current_dir / "promtail.exe"
            download_url = "https://github.com/grafana/loki/releases/latest/download/promtail-windows-amd64.exe.zip"
        else:
            promtail_binary = self.current_dir / "promtail"
            download_url = "https://github.com/grafana/loki/releases/latest/download/promtail-linux-amd64.zip"

        if promtail_binary.exists():
            print(f"✅ Promtail binary already exists at {promtail_binary}")
            return promtail_binary

        print(f"📥 Downloading Promtail from {download_url}...")

        try:
            import zipfile
            import tempfile

            # Download the zip file
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()

            # Extract the binary
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name

            with zipfile.ZipFile(temp_file_path, 'r') as zip_ref:
                if self.is_windows:
                    zip_ref.extract("promtail-windows-amd64.exe", self.current_dir)
                    (self.current_dir / "promtail-windows-amd64.exe").rename(promtail_binary)
                else:
                    zip_ref.extract("promtail-linux-amd64", self.current_dir)
                    (self.current_dir / "promtail-linux-amd64").rename(promtail_binary)

            # Make executable on Unix systems
            if not self.is_windows:
                os.chmod(promtail_binary, 0o755)

            # Clean up temp file
            os.unlink(temp_file_path)

            print(f"✅ Promtail downloaded to {promtail_binary}")
            return promtail_binary

        except Exception as e:
            print(f"❌ Failed to download Promtail: {e}")
            print("Please download Promtail manually from: https://github.com/grafana/loki/releases")
            return None

    def test_promtail_config(self, promtail_binary):
        """Test Promtail configuration"""
        print("🔧 Testing Promtail configuration...")

        try:
            # Test config validation
            cmd = [str(promtail_binary), "-config.file", str(self.promtail_config), "-dry-run"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print("✅ Promtail configuration is valid")
                return True
            else:
                print(f"❌ Promtail configuration error: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("❌ Promtail configuration test timed out")
            return False
        except Exception as e:
            print(f"❌ Error testing Promtail configuration: {e}")
            return False

    def start_promtail(self, promtail_binary):
        """Start Promtail process"""
        print("🚀 Starting Promtail log shipper...")

        try:
            # Create positions file directory
            positions_file = self.current_dir / "promtail-positions.yaml"
            positions_file.touch(exist_ok=True)

            # Start Promtail
            cmd = [
                str(promtail_binary),
                "-config.file", str(self.promtail_config),
                "-log.level", "info"
            ]

            if self.is_windows:
                # Start as background process on Windows
                process = subprocess.Popen(
                    cmd,
                    cwd=str(self.current_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
                print(f"✅ Promtail started with PID: {process.pid}")

                # Save PID for later management
                pid_file = self.current_dir / "promtail.pid"
                with open(pid_file, 'w') as f:
                    f.write(str(process.pid))

                # Give it a moment to start
                time.sleep(3)

                # Check if process is still running
                if process.poll() is None:
                    print("✅ Promtail is running and shipping logs")
                    return True
                else:
                    stdout, stderr = process.communicate()
                    print(f"❌ Promtail failed to start: {stderr}")
                    return False

            else:
                # Start as background process on Unix
                with open(self.current_dir / "promtail.log", 'w') as log_file:
                    process = subprocess.Popen(
                        cmd,
                        cwd=str(self.current_dir),
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        start_new_session=True
                    )

                print(f"✅ Promtail started with PID: {process.pid}")

                # Save PID for later management
                pid_file = self.current_dir / "promtail.pid"
                with open(pid_file, 'w') as f:
                    f.write(str(process.pid))

                # Give it a moment to start
                time.sleep(3)

                # Check if process is still running
                if process.poll() is None:
                    print("✅ Promtail is running and shipping logs")
                    return True
                else:
                    print("❌ Promtail failed to start. Check promtail.log for details.")
                    return False

        except Exception as e:
            print(f"❌ Error starting Promtail: {e}")
            return False

    def test_log_shipping(self):
        """Test if logs are being shipped to remote Loki"""
        print("🔍 Testing log shipping to remote Loki...")

        # Wait a bit for logs to be shipped
        print("⏳ Waiting 10 seconds for logs to be shipped...")
        time.sleep(10)

        try:
            # Query Loki for our logs
            query_url = f"{self.remote_loki_url}/loki/api/v1/query"
            query_params = {
                "query": '{service="entersys-backend"}',
                "limit": 10
            }

            response = requests.get(query_url, params=query_params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('data', {}).get('result'):
                    log_count = len(data['data']['result'])
                    print(f"✅ Successfully found {log_count} log streams in remote Loki")

                    # Show sample log entries
                    for stream in data['data']['result'][:2]:  # Show first 2 streams
                        labels = stream.get('stream', {})
                        values = stream.get('values', [])
                        print(f"📊 Stream: {labels}")
                        if values:
                            print(f"   Latest log: {values[0][1][:100]}...")

                    return True
                else:
                    print("⚠️  No logs found in remote Loki yet. This might be normal for a new setup.")
                    return False
            else:
                print(f"❌ Failed to query remote Loki: HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error testing log shipping: {e}")
            return False

    def create_monitoring_script(self):
        """Create a script to monitor log shipping status"""
        monitoring_script = self.current_dir / ("monitor_logs.bat" if self.is_windows else "monitor_logs.sh")

        if self.is_windows:
            script_content = f"""@echo off
echo Checking Promtail log shipping status...

REM Check if Promtail is running
tasklist /fi "imagename eq promtail.exe" | find /i "promtail.exe" >nul
if %errorlevel% equ 0 (
    echo ✅ Promtail is running
) else (
    echo ❌ Promtail is not running
)

REM Check log file sizes
if exist "{self.logs_dir}\\six_sigma_performance.log" (
    for %%A in ("{self.logs_dir}\\six_sigma_performance.log") do echo Six Sigma Performance Log: %%~zA bytes
)
if exist "{self.logs_dir}\\six_sigma_errors.log" (
    for %%A in ("{self.logs_dir}\\six_sigma_errors.log") do echo Six Sigma Errors Log: %%~zA bytes
)

REM Test remote Loki connectivity
curl -s -o nul -w "Remote Loki Status: %%{{http_code}}\\n" {self.remote_loki_url}/ready

pause
"""
        else:
            script_content = f"""#!/bin/bash
echo "Checking Promtail log shipping status..."

# Check if Promtail is running
if pgrep -f promtail > /dev/null; then
    echo "✅ Promtail is running (PID: $(pgrep -f promtail))"
else
    echo "❌ Promtail is not running"
fi

# Check log file sizes
if [ -f "{self.logs_dir}/six_sigma_performance.log" ]; then
    echo "Six Sigma Performance Log: $(stat -f%z "{self.logs_dir}/six_sigma_performance.log" 2>/dev/null || stat -c%s "{self.logs_dir}/six_sigma_performance.log") bytes"
fi
if [ -f "{self.logs_dir}/six_sigma_errors.log" ]; then
    echo "Six Sigma Errors Log: $(stat -f%z "{self.logs_dir}/six_sigma_errors.log" 2>/dev/null || stat -c%s "{self.logs_dir}/six_sigma_errors.log") bytes"
fi

# Test remote Loki connectivity
echo "Remote Loki Status: $(curl -s -o /dev/null -w "%{{http_code}}" {self.remote_loki_url}/ready)"

# Show recent Promtail logs if available
if [ -f "promtail.log" ]; then
    echo ""
    echo "Recent Promtail logs:"
    tail -5 promtail.log
fi
"""

        with open(monitoring_script, 'w') as f:
            f.write(script_content)

        if not self.is_windows:
            os.chmod(monitoring_script, 0o755)

        print(f"📝 Created monitoring script: {monitoring_script}")

    def setup(self):
        """Run the complete setup process"""
        print("🚀 Starting log shipping setup for Entersys Backend")
        print("=" * 60)

        # Step 1: Check remote Loki connectivity
        if not self.check_remote_loki_connectivity():
            print("❌ Cannot proceed without remote Loki connectivity")
            return False

        # Step 2: Check if log files exist
        if not self.check_log_files_exist():
            print("⚠️  No logs to ship yet, but continuing with setup...")

        # Step 3: Download Promtail
        promtail_binary = self.download_promtail()
        if not promtail_binary:
            return False

        # Step 4: Test configuration
        if not self.test_promtail_config(promtail_binary):
            return False

        # Step 5: Start Promtail
        if not self.start_promtail(promtail_binary):
            return False

        # Step 6: Test log shipping
        self.test_log_shipping()

        # Step 7: Create monitoring script
        self.create_monitoring_script()

        print("\n" + "=" * 60)
        print("🎉 Log shipping setup completed!")
        print(f"📊 Logs are being shipped to: {self.remote_loki_url}")
        print("📋 Monitor the setup with the created monitoring script")
        print("🔧 To stop Promtail, kill the process using the PID in promtail.pid")

        return True

def main():
    setup = LogShippingSetup()

    try:
        success = setup.setup()
        if success:
            print("\n✅ Setup completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Setup failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()