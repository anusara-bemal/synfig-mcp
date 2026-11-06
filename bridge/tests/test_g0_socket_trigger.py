"""
Phase G0 Feasibility Test Trigger.
Connects to Synfig Studio throwaway hook at 127.0.0.1:19998
and triggers circle creation via Glib::Dispatcher.
"""
import socket
import sys
import time

def trigger_g0(host="127.0.0.1", port=19998, timeout=5.0):
    print(f"Connecting to Synfig Studio G0 hook at {host}:{port}...")
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.sendall(b"create_circle\n")
            response = s.recv(1024)
            print(f"Received from Synfig Studio: {response.decode('utf-8').strip()}")
            return True
    except ConnectionRefusedError:
        print(f"Connection refused at {host}:{port}. Ensure Synfig Studio is running with the G0 hook.")
        return False
    except Exception as e:
        print(f"Error communicating with G0 hook: {e}")
        return False

if __name__ == "__main__":
    success = trigger_g0()
    sys.exit(0 if success else 1)
