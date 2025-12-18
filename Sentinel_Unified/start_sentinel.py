#!/usr/bin/env python3
"""
Sentinel Unified - Master Switch
=================================
This script is the entry point for the entire Sentinel security system.
It launches all microservices simultaneously, aggregates logs, and handles
graceful shutdown.

Services Managed:
- Door Sentry: Front door monitoring with face recognition
- Interior Watch: Interior room monitoring with theft detection
- Web Interface: Next.js frontend dashboard

Author: Sentinel System
"""

import os
import sys
import subprocess
import threading
import signal
import time
import socket
import platform
from pathlib import Path


# ANSI Color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'    # Door Sentry
    BLUE = '\033[94m'     # Interior Watch
    CYAN = '\033[96m'     # Web Interface
    RED = '\033[91m'      # System errors
    YELLOW = '\033[93m'   # System warnings
    RESET = '\033[0m'     # Reset to default


class SystemOrchestrator:
    """
    Main orchestrator class that manages all Sentinel services.
    
    This class handles:
    - MQTT broker verification
    - Service startup and monitoring
    - Log aggregation with color-coded output
    - Graceful shutdown
    """
    
    def __init__(self):
        """Initialize the orchestrator."""
        self.base_dir = Path(__file__).parent
        self.processes = {}
        self.threads = []
        self.running = True
        
        # Service definitions
        self.services = {
            'Door_Sentry': {
                'type': 'python',
                'path': self.base_dir / 'Services' / 'Door_Sentry' / 'main.py',
                'prefix': 'DOOR',
                'color': Colors.GREEN
            },
            'Interior_Watch': {
                'type': 'python',
                'path': self.base_dir / 'Services' / 'Interior_Watch' / 'main.py',
                'prefix': 'INTERIOR',
                'color': Colors.BLUE
            },
            'Web_Interface': {
                'type': 'npm',
                'path': self.base_dir / 'Web_Interface',
                'prefix': 'WEB',
                'color': Colors.CYAN
            }
        }
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """
        Handle shutdown signals (SIGINT/SIGTERM).
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        print(f"\n{Colors.YELLOW}[SYSTEM] Shutdown signal received...{Colors.RESET}")
        self.shutdown()
        sys.exit(0)
    
    def check_mqtt_broker(self):
        """
        Check if MQTT broker (Mosquitto) is running on port 1883.
        
        Returns:
            bool: True if broker is accessible, False otherwise
        """
        print(f"{Colors.YELLOW}[SYSTEM] Checking MQTT broker on port 1883...{Colors.RESET}")
        
        try:
            # Try to connect to MQTT broker port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', 1883))
            sock.close()
            
            if result == 0:
                print(f"{Colors.GREEN}[SYSTEM] ✓ MQTT broker is running{Colors.RESET}")
                return True
            else:
                self._print_mqtt_warning()
                return False
                
        except Exception as e:
            print(f"{Colors.RED}[SYSTEM] Error checking MQTT broker: {e}{Colors.RESET}")
            self._print_mqtt_warning()
            return False
    
    def _print_mqtt_warning(self):
        """Print a warning about missing MQTT broker."""
        print(f"{Colors.RED}")
        print("=" * 70)
        print("⚠️  WARNING: MQTT BROKER NOT DETECTED!")
        print("=" * 70)
        print("The MQTT broker (Mosquitto) is not running on port 1883.")
        print("Services will start but MQTT-based features will not work:")
        print("  - Door unlock commands")
        print("  - Theft alerts")
        print("  - Service communication")
        print()
        
        if platform.system() == 'Linux':
            print("To start Mosquitto on Linux:")
            print("  sudo systemctl start mosquitto")
            print("  OR")
            print("  mosquitto -v")
        elif platform.system() == 'Windows':
            print("To start Mosquitto on Windows:")
            print("  Run 'mosquitto' from command prompt")
            print("  OR install as a service")
        else:
            print("Please start your MQTT broker (Mosquitto) manually.")
        
        print("=" * 70)
        print(f"{Colors.RESET}")
        
        # Give user a chance to start it
        print(f"{Colors.YELLOW}[SYSTEM] Waiting 5 seconds before continuing...{Colors.RESET}")
        time.sleep(5)
    
    def stream_process_output(self, process, prefix, color):
        """
        Stream output from a subprocess to the console with color-coded prefix.
        
        This function runs in a separate thread and continuously reads from
        the process stdout, adding a colored prefix to each line.
        
        Args:
            process: subprocess.Popen object
            prefix: String prefix for log lines (e.g., "DOOR", "INTERIOR")
            color: ANSI color code for the prefix
        """
        try:
            # Read lines from process stdout
            for line in iter(process.stdout.readline, b''):
                if not self.running:
                    break
                    
                # Decode and strip whitespace
                line_text = line.decode('utf-8', errors='replace').rstrip()
                
                if line_text:  # Only print non-empty lines
                    print(f"{color}[{prefix}]{Colors.RESET} {line_text}")
                    
        except Exception as e:
            if self.running:  # Only log errors if we're still running
                print(f"{Colors.RED}[SYSTEM] Error streaming {prefix} output: {e}{Colors.RESET}")
    
    def start_services(self):
        """
        Start all Sentinel services.
        
        This method:
        1. Checks for MQTT broker
        2. Launches Python services with current interpreter
        3. Launches Next.js frontend with npm
        4. Starts log streaming threads for each service
        """
        print(f"{Colors.YELLOW}[SYSTEM] Starting Sentinel services...{Colors.RESET}")
        
        # Check MQTT broker
        self.check_mqtt_broker()
        
        # Start each service
        for service_name, service_info in self.services.items():
            try:
                if service_info['type'] == 'python':
                    self._start_python_service(service_name, service_info)
                elif service_info['type'] == 'npm':
                    self._start_npm_service(service_name, service_info)
                    
            except Exception as e:
                print(f"{Colors.RED}[SYSTEM] Failed to start {service_name}: {e}{Colors.RESET}")
        
        print(f"{Colors.GREEN}[SYSTEM] All services started!{Colors.RESET}")
    
    def _start_python_service(self, service_name, service_info):
        """
        Start a Python-based service.
        
        Args:
            service_name: Name of the service
            service_info: Service configuration dictionary
        """
        path = service_info['path']
        prefix = service_info['prefix']
        color = service_info['color']
        
        # Check if service file exists
        if not path.exists():
            print(f"{Colors.RED}[SYSTEM] ✗ {service_name} not found at {path}{Colors.RESET}")
            return
        
        print(f"{Colors.YELLOW}[SYSTEM] Starting {service_name}...{Colors.RESET}")
        
        # Start process with current Python interpreter
        process = subprocess.Popen(
            [sys.executable, str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            cwd=str(path.parent)
        )
        
        self.processes[service_name] = process
        
        # Start log streaming thread
        thread = threading.Thread(
            target=self.stream_process_output,
            args=(process, prefix, color),
            daemon=True
        )
        thread.start()
        self.threads.append(thread)
        
        print(f"{Colors.GREEN}[SYSTEM] ✓ {service_name} started (PID: {process.pid}){Colors.RESET}")
    
    def _start_npm_service(self, service_name, service_info):
        """
        Start an npm-based service (Next.js).
        
        Args:
            service_name: Name of the service
            service_info: Service configuration dictionary
        """
        path = service_info['path']
        prefix = service_info['prefix']
        color = service_info['color']
        
        # Check if service directory exists
        if not path.exists():
            print(f"{Colors.RED}[SYSTEM] ✗ {service_name} not found at {path}{Colors.RESET}")
            return
        
        # Determine npm command based on OS
        npm_cmd = 'npm.cmd' if platform.system() == 'Windows' else 'npm'
        
        print(f"{Colors.YELLOW}[SYSTEM] Starting {service_name}...{Colors.RESET}")
        
        # Start npm dev server
        process = subprocess.Popen(
            [npm_cmd, 'run', 'dev'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            cwd=str(path)
        )
        
        self.processes[service_name] = process
        
        # Start log streaming thread
        thread = threading.Thread(
            target=self.stream_process_output,
            args=(process, prefix, color),
            daemon=True
        )
        thread.start()
        self.threads.append(thread)
        
        print(f"{Colors.GREEN}[SYSTEM] ✓ {service_name} started (PID: {process.pid}){Colors.RESET}")
    
    def monitor(self):
        """
        Monitor running services and detect crashes.
        
        This method runs in a loop, checking if any service has died.
        If a service crashes, it logs a critical error.
        """
        print(f"{Colors.GREEN}[SYSTEM] Monitoring services... Press Ctrl+C to shutdown{Colors.RESET}")
        
        while self.running:
            try:
                # Check each process
                for service_name, process in list(self.processes.items()):
                    return_code = process.poll()
                    
                    if return_code is not None:
                        # Process has died
                        print(f"{Colors.RED}[SYSTEM] ✗ CRITICAL: {service_name} died with code {return_code}!{Colors.RESET}")
                        
                        # Remove from active processes
                        del self.processes[service_name]
                
                # Sleep briefly before next check
                time.sleep(1)
                
            except Exception as e:
                if self.running:
                    print(f"{Colors.RED}[SYSTEM] Error in monitor loop: {e}{Colors.RESET}")
                    time.sleep(1)
    
    def shutdown(self):
        """
        Gracefully shutdown all services.
        
        This method:
        1. Sets running flag to False
        2. Terminates all child processes
        3. Waits for processes to exit
        4. Reports system offline
        """
        print(f"{Colors.YELLOW}[SYSTEM] Shutting down Sentinel...{Colors.RESET}")
        self.running = False
        
        # Terminate all processes
        for service_name, process in self.processes.items():
            try:
                print(f"{Colors.YELLOW}[SYSTEM] Stopping {service_name}...{Colors.RESET}")
                process.terminate()
            except Exception as e:
                print(f"{Colors.RED}[SYSTEM] Error terminating {service_name}: {e}{Colors.RESET}")
        
        # Wait for processes to exit (with timeout)
        timeout = 10  # seconds
        start_time = time.time()
        
        while self.processes and (time.time() - start_time) < timeout:
            for service_name, process in list(self.processes.items()):
                try:
                    process.wait(timeout=0.5)
                    print(f"{Colors.GREEN}[SYSTEM] ✓ {service_name} stopped{Colors.RESET}")
                    del self.processes[service_name]
                except subprocess.TimeoutExpired:
                    pass
        
        # Force kill any remaining processes
        for service_name, process in self.processes.items():
            try:
                print(f"{Colors.RED}[SYSTEM] Force killing {service_name}...{Colors.RESET}")
                process.kill()
            except Exception as e:
                print(f"{Colors.RED}[SYSTEM] Error killing {service_name}: {e}{Colors.RESET}")
        
        print(f"{Colors.RED}[SYSTEM] System Offline{Colors.RESET}")


def print_banner():
    """Print the Sentinel startup banner."""
    banner = f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   ███████╗███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗   ║
║   ██╔════╝██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║   ║
║   ███████╗█████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║   ║
║   ╚════██║██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║   ║
║   ███████║███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗║
║   ╚══════╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝║
║                                                                  ║
║                    🛡️  UNIFIED SECURITY SYSTEM                   ║
║                         Master Switch v1.0                       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝{Colors.RESET}
"""
    print(banner)


def main():
    """Main entry point for the Sentinel orchestrator."""
    # Print banner
    print_banner()
    
    print(f"{Colors.YELLOW}[SYSTEM] Initializing Sentinel Unified...{Colors.RESET}")
    
    try:
        # Create orchestrator
        orchestrator = SystemOrchestrator()
        
        # Start all services
        orchestrator.start_services()
        
        # Monitor services (blocks until Ctrl+C)
        orchestrator.monitor()
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[SYSTEM] Keyboard interrupt received{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}[SYSTEM] Fatal error: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
    finally:
        # Ensure cleanup happens
        if 'orchestrator' in locals():
            orchestrator.shutdown()


if __name__ == "__main__":
    main()
