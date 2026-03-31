def evaluate_sports_domain(user_id):
    from assessment.services.universal_scoring_service import evaluate_domain

    return evaluate_domain("sports", user_id)
