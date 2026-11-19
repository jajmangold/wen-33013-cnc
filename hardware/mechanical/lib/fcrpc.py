"""Talk to one FreeCAD GUI instance over the MCP addon's XML-RPC port.

Several FreeCAD windows usually run at once and each takes the next free
port, so the port is never assumed - read it from
%APPDATA%/FreeCAD/mcp_instances/<pid>.json, or pass it in.

Never send XML-RPC to a port you have not confirmed is FreeCAD: xmlrpc.client
has no default timeout, and probing something else hangs forever.
"""

from __future__ import annotations

import os
import socket
import xmlrpc.client

socket.setdefaulttimeout(120)
DEFAULT_PORT = int(os.environ.get("WEN_FC_PORT", "9879"))


def server(port: int = DEFAULT_PORT) -> xmlrpc.client.ServerProxy:
    return xmlrpc.client.ServerProxy(f"http://127.0.0.1:{port}", allow_none=True)


def run(code: str, port: int = DEFAULT_PORT) -> dict:
    """Execute code in the GUI instance, raising if it did not succeed."""
    result = server(port).execute_code(code)
    if not result.get("success"):
        raise SystemExit(f"FreeCAD on {port}: {result}")
    return result


def whoami(port: int = DEFAULT_PORT) -> dict:
    """pid, window title and open documents - confirm before any write."""
    return server(port).get_instance_info()


if __name__ == "__main__":
    print(whoami())
