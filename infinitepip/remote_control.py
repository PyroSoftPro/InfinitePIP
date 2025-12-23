from __future__ import annotations

import json
import socketserver


class RemoteControlHandler(socketserver.BaseRequestHandler):
    """Handles remote control requests for InfinitePIP"""

    def handle(self):
        try:
            # Receive data
            data = self.request.recv(1024).decode("utf-8")
            command_data = json.loads(data)

            # Process command
            response = self.process_command(command_data)

            # Send response
            self.request.sendall(json.dumps(response).encode("utf-8"))

        except Exception as e:
            error_response = {"status": "error", "message": str(e)}
            self.request.sendall(json.dumps(error_response).encode("utf-8"))

    def process_command(self, command_data):
        """Process a remote control command"""
        action = command_data.get("action")

        if action == "create_window_pip":
            return self.create_window_pip(command_data.get("window_data"))
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def create_window_pip(self, window_data):
        """Create a window PIP from external request"""
        try:
            # Get the main app instance
            app = getattr(self.server, "app_instance", None)
            if not app:
                return {"status": "error", "message": "App instance not available"}

            # Create window PIP
            app.create_window_pip_from_external(window_data)

            return {"status": "success", "message": "Window PIP created successfully"}

        except Exception as e:
            return {"status": "error", "message": str(e)}


class RemoteControlServer(socketserver.ThreadingTCPServer):
    """TCP server for remote control functionality"""

    allow_reuse_address = True

    def __init__(self, host, port, app_instance):
        super().__init__((host, port), RemoteControlHandler)
        self.app_instance = app_instance
        self.daemon_threads = True


