"""Small, IPv4 LAN-only discovery responder; never exposes financial data."""
import ipaddress
import json
import logging
import re
import socket
import threading

DISCOVERY_PORT = 5057
SERVICE = "kys-finance"


def discovery_reply(payload, address, http_port, server_name):
    try:
        peer = ipaddress.ip_address(address)
        if not (peer.is_private or peer.is_link_local or peer.is_loopback):
            return None
        request = json.loads(payload)
        if not isinstance(request, dict):
            return None
        nonce = request.get("nonce", "")
        if (request.get("service") != SERVICE or request.get("version") != 1
                or not isinstance(nonce, str) or not re.fullmatch(r"[a-f0-9]{32}", nonce)):
            return None
        return json.dumps({"service": SERVICE, "version": 1, "nonce": nonce,
                           "name": server_name, "port": http_port}).encode("utf-8")
    except (ValueError, UnicodeError, TypeError):
        return None


def start_discovery(http_port, bind_host="0.0.0.0", discovery_port=DISCOVERY_PORT):
    """Return (stop_event, thread, UDP port). Caller stops it with stop_event.set()."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((bind_host, discovery_port))
        sock.settimeout(0.5)
    except OSError:
        sock.close()
        raise
    port = sock.getsockname()[1]
    stopped = threading.Event()
    server_name = socket.gethostname()

    def respond():
        try:
            while not stopped.is_set():
                try:
                    data, peer = sock.recvfrom(2048)
                    response = discovery_reply(data, peer[0], http_port, server_name)
                    if response:
                        sock.sendto(response, peer)
                except socket.timeout:
                    continue
                except OSError:
                    logging.getLogger(__name__).warning("LAN discovery socket error", exc_info=True)
                    break
        finally:
            sock.close()

    thread = threading.Thread(target=respond, name="kys-lan-discovery", daemon=True)
    thread.start()
    return stopped, thread, port
