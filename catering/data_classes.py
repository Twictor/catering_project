from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrackingOrder:
    restaurants: dict[str, dict[str, Any]] = field(default_factory=dict)
    delivery_providers: dict[str, dict[str, Any]] = field(default_factory=dict)
