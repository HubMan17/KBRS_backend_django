from dataclasses import dataclass

LEVEL_BASE = 100
LEVEL_STEP = 25

def xp_needed(level: int) -> int:
    return LEVEL_BASE + LEVEL_STEP * level

@dataclass
class ApplyResult:
    level: int
    xp: int
    leveled_up: bool
    need: int

def apply_xp(profile, amount: int) -> ApplyResult:
    leveled = False
    profile.xp += amount
    while profile.xp >= xp_needed(profile.level):
        profile.xp -= xp_needed(profile.level)
        profile.level += 1
        leveled = True
    return ApplyResult(level=profile.level, xp=profile.xp, leveled_up=leveled, need=xp_needed(profile.level))
