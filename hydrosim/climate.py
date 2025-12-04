"""
Climate engine and data structures for environmental drivers.

The climate engine manages temporal and climatic context including
precipitation, temperature, and evapotranspiration.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ClimateState:
    """Climate drivers for a single timestep."""
    date: datetime
    precip: float  # mm
    t_max: float   # °C
    t_min: float   # °C
    solar: float   # MJ/m²/day
    et0: float     # mm (calculated)


@dataclass
class SiteConfig:
    """Site-specific parameters for climate calculations."""
    latitude: float   # degrees
    elevation: float  # meters
