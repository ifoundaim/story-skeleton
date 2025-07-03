from typing import List, Sequence
import math

def clip_vector(vec: Sequence[float], min_val: float = -1.0, max_val: float = 1.0) -> List[float]:
    return [max(min(x, max_val), min_val) for x in vec]

def norm_vector(vec: Sequence[float]) -> float:
    return math.sqrt(sum(x * x for x in vec))

def add_vectors(a: Sequence[float], b: Sequence[float]) -> List[float]:
    return [x + y for x, y in zip(a, b)] 