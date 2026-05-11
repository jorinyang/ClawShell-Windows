"""
ClawShell Cloud — N8N Bridge Service v2.0
==========================================
Bridge between ClawShell EventBus and N8N workflow engine.
Triggers N8N workflows when matching events are published.
"""

import json
import logging
from typing import Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger("N8NBridge")


class N8NBridge:
    """
    Bridge to N8N workflow automation engine.

    Maps ClawShell events → N8N webhooks, and provides
    workflow status queries.
    """

    def __init__(self, n8n_url: str = "http://localhost:5678"):
        self.n8n_url = n8n_url.rstrip("/")
        # Event type → webhook URL mapping
        self._event_workflow_map: Dict[str, str] = {}

    def register_workflow(self, event_type: str, webhook_path: str):
        """Map an event type to an N8N webhook"""
        self._event_workflow_map[event_type] = webhook_path

    def trigger_by_event(self, event_type: str, payload: Dict) -> bool:
        """Trigger an N8N workflow based on event type"""
        webhook = self._event_workflow_map.get(event_type)
        if not webhook:
            # Try wildcard match
            import fnmatch
            for pattern, wh in self._event_workflow_map.items():
                if fnmatch.fnmatch(event_type, pattern):
                    webhook = wh
                    break

        if not webhook:
            return False

        url = f"{self.n8n_url}/webhook/{webhook.lstrip('/')}"
        data = json.dumps(payload).encode()

        try:
            req = Request(url, data=data, headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=10) as resp:
                result = resp.read().decode()
            logger.info(f"N8N triggered: {event_type} → {webhook}")
            return True
        except URLError as e:
            logger.error(f"N8N trigger failed [{event_type}]: {e}")
            return False

    def trigger_webhook(self, webhook_path: str, payload: Dict = None) -> bool:
        """Directly trigger an N8N webhook"""
        url = f"{self.n8n_url}/webhook/{webhook_path.lstrip('/')}"
        data = json.dumps(payload or {}).encode()

        try:
            req = Request(url, data=data, headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=10) as resp:
                result = resp.read().decode()
            logger.info(f"N8N webhook triggered: {webhook_path}")
            return True
        except URLError as e:
            logger.error(f"N8N webhook failed [{webhook_path}]: {e}")
            return False

    def list_mappings(self) -> Dict[str, str]:
        return dict(self._event_workflow_map)

    def health_check(self) -> bool:
        """Check if N8N is reachable"""
        try:
            req = Request(f"{self.n8n_url}/healthz", method="HEAD")
            with urlopen(req, timeout=5):
                return True
        except:
            return False
