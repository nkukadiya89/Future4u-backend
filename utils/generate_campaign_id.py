from datetime import datetime

from campaign.models import Campaign


def generate_campaign_id_with_date_format():
    today = datetime.now()
    date_str = today.strftime("%Y%m%d")
    base_campaign_id = f"CAM-{date_str}"

    # Check if base ID exists, if so add a suffix
    campaign_id = base_campaign_id
    counter = 1

    while Campaign.objects.filter(campaign_id=campaign_id).exists():
        campaign_id = f"{base_campaign_id}-{counter:02d}"
        counter += 1

    return campaign_id
