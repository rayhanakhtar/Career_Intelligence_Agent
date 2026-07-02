"""Match score computation from FAISS similarity distances."""

import numpy as np


def compute_match_scores(scores: list[float]) -> list[float]:
    """Convert raw inner-product scores to human-friendly match percentages.

    Since vectors are L2-normalised, inner product scores range from -1.0 to 1.0.
    This function maps [-1.0, 1.0] to [0%, 100%] via linear scaling.

    Args:
        scores: List of raw inner-product scores from FAISS.

    Returns:
        List of match percentages (0.0 to 100.0).
    """
    if not scores:
        return []

    arr = np.array(scores, dtype=np.float32)
    # Clamp to [-1.0, 1.0] for safety
    arr = np.clip(arr, -1.0, 1.0)
    # Scale: (-1, 1) → (0, 1) → (0, 100)
    match_scores = ((arr + 1.0) / 2.0) * 100.0
    return match_scores.tolist()
