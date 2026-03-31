DOMAIN_CONFIG = {
    "sports": {
        "dimensions": {
            "interest": 0.30,
            "aptitude": 0.30,
            "personality": 0.20,
            "work_style": 0.20,
        },
        "careers": {
            "athlete": {
                "dimension_factors": {
                    "interest": 1.00,
                    "aptitude": 1.00,
                    "personality": 0.85,
                    "work_style": 0.90,
                }
            },
            "sports_science": {
                "dimension_factors": {
                    "interest": 0.90,
                    "aptitude": 0.95,
                    "personality": 0.95,
                    "work_style": 1.00,
                }
            },
            "coach": {
                "dimension_factors": {
                    "interest": 0.95,
                    "aptitude": 0.80,
                    "personality": 1.00,
                    "work_style": 0.95,
                }
            },
        },
        "rules": {
            "thresholds": [
                {
                    "dimension": "aptitude",
                    "operator": "lt",
                    "value": 45,
                    "actions": [{"type": "multiply", "career": "athlete", "value": 0.75}],
                }
            ],
            "suppressions": [
                {
                    "dimension": "interest",
                    "operator": "lt",
                    "value": 40,
                    "careers": {
                        "athlete": 0.40,
                        "sports_science": 0.70,
                        "coach": 0.55,
                    },
                }
            ],
            "hybrid_margin": 5,
        },
        "defaults": {
            "missing_dimension_score": 50.0,
            "max_score_per_answer": 5.0,
        },
    }
}

