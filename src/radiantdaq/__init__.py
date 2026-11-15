"""RadiantDAQ: synthetic detector-chain modeling (research education, not clinical use)."""
from .config import DetectorConfig
from .metrics import simulate_pet_pair

__all__ = ['DetectorConfig', 'simulate_pet_pair']
__version__ = '0.1.0'
