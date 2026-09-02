"""
Mathematische Hilfsfunktionen
"""

import math


def poisson_probability(lmbda: float, k: int) -> float:
    """
    Berechnet die Poisson-Wahrscheinlichkeit für k Ereignisse bei erwarteter Rate lambda
    
    Args:
        lmbda: Erwartete Anzahl von Ereignissen (λ)
        k: Tatsächliche Anzahl von Ereignissen
        
    Returns:
        Wahrscheinlichkeit P(X = k)
    """
    if lmbda <= 0:
        return 1.0 if k == 0 else 0.0
    return (math.exp(-lmbda) * (lmbda**k)) / math.factorial(k)
