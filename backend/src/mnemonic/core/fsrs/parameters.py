"""FSRS algorithm parameters configuration.

This module defines the FSRSParameters class containing the 19 weights
from the FSRS-5 research and other algorithm configuration.

Reference: https://github.com/open-spaced-repetition/fsrs4py
"""

from dataclasses import dataclass


@dataclass
class FSRSParameters:
    """FSRS algorithm parameters from FSRS-5 research.

    The FSRS (Free Spaced Repetition Scheduler) algorithm uses 19 weights
    derived from data analysis to optimize spacing and scheduling.

    Attributes:
        w: List of 19 weight parameters from FSRS-5 research
        request_retention: Target retention rate (default 0.9 = 90%)
        maximum_interval: Maximum interval between reviews in days (default 100 years)
    """

    w: list[float]
    request_retention: float = 0.9
    maximum_interval: int = 36500

    @classmethod
    def default(cls) -> "FSRSParameters":
        """Return default FSRS-5 parameters.

        The 19 weights are derived from FSRS-5 research based on analysis
        of millions of review logs. These are proven effective across
        diverse study domains.

        Returns:
            FSRSParameters: Default FSRS-5 configuration
        """
        # FSRS-5 default weights
        w = [
            0.4072,  # w0
            1.1829,  # w1
            3.1262,  # w2
            15.4722,  # w3
            7.2102,  # w4
            0.5316,  # w5
            1.0651,  # w6
            0.0234,  # w7
            1.616,  # w8
            0.1544,  # w9
            1.0824,  # w10
            1.9813,  # w11
            0.0953,  # w12
            0.2975,  # w13
            2.2042,  # w14
            0.2407,  # w15
            2.9466,  # w16
            0.5034,  # w17
            0.6567,  # w18
        ]

        return cls(w=w, request_retention=0.9, maximum_interval=36500)
