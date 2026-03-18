import re

from device_config.models import DeviceConfiguration


def generate_next_device_code(prefix: str = "#", width: int = 3) -> str:
    existing_codes = (
        DeviceConfiguration.objects.exclude(device_code__isnull=True)
        .exclude(device_code="")
        .values_list("device_code", flat=True)
    )
    max_num = 0
    pattern = re.compile(rf"{re.escape(prefix)}(\d+)$")
    for code in existing_codes:
        m = pattern.fullmatch(str(code))
        if m:
            try:
                n = int(m.group(1))
                if n > max_num:
                    max_num = n
            except ValueError:
                continue
    return f"{prefix}{max_num + 1:0{width}d}"
