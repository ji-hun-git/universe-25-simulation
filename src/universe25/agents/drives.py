"""Drive documentation and derived motivational states.

Active drives (NONE is a play reward):
- hunger, thirst, fatigue, energy (homeostasis)
- stress (density / wounds)
- social_drive, aggression, maternal
- curiosity, boredom (generic intrinsic; may cause playground approach)
- maternal_need (derived, below): a nursing female's motivation set by her own litter's hunger

H2: no reward, observation, or utility term named play / bout / motif.
ACT_MANIPULATE satisfies curiosity/boredom only.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from universe25.agents.state import ROLE_NURSING, ROLE_PUP

if TYPE_CHECKING:  # pragma: no cover
    from universe25.agents.state import AgentSoA


def maternal_need(agents: AgentSoA, idx: np.ndarray) -> np.ndarray:
    """Maternal motivation of the agents `idx` (same units as hunger, 0..1.5).

    For a female in the nursing role with a nest box: the mean hunger of the pre-weaning pups in
    her box (nursing in the simulation is per box, so these are the pups her presence feeds);
    zero when the box has no pups, and zero for everyone else. It rises while the litter goes
    unfed and falls when it is fed (dams respond to their pups' cues; Numan & Insel 2003). Read
    by the learner's reward and observation (P4-2, 2026-11-06); the biology does not use it.
    """
    a = agents
    out = np.zeros(idx.size, dtype=np.float64)
    pups = np.flatnonzero(a.alive & (a.role == ROLE_PUP) & (a.nest_id >= 0))
    if pups.size == 0 or idx.size == 0:
        return out
    nest_p = a.nest_id[pups].astype(np.int64)
    n_nests = int(max(nest_p.max(), int(a.nest_id[idx].max()) if idx.size else 0)) + 1
    cnt = np.bincount(nest_p, minlength=n_nests)
    tot = np.bincount(nest_p, weights=a.hunger[pups].astype(np.float64), minlength=n_nests)
    nest = a.nest_id[idx].astype(np.int64)
    mom = (a.role[idx] == ROLE_NURSING) & (nest >= 0)
    ns = np.clip(nest, 0, n_nests - 1)
    has = mom & (cnt[ns] > 0)
    out[has] = tot[ns[has]] / cnt[ns[has]]
    return out
