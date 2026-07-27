from rest_framework import serializers


def validate_domain_category_and_domain(attrs, instance=None):
    category = attrs.get("domain_category")
    domain = attrs.get("domain")

    if instance:
        if category is None and instance.domain_category_id:
            category = instance.domain_category
        if domain is None and instance.domain_id:
            domain = instance.domain

    if category and category.parent_id is not None:
        raise serializers.ValidationError(
            {"domain_category": "Selected category must be a parent domain."}
        )

    if domain and domain.parent_id is None:
        raise serializers.ValidationError(
            {"domain": "Selected domain must be a child domain."}
        )

    if category and domain and domain.parent_id != category.id:
        raise serializers.ValidationError(
            {"domain": "Selected domain must belong to selected category."}
        )

    return attrs
