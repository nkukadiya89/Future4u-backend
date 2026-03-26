"""
Backward-compatible alias module.

Some legacy code/tests reference `company.serializer` (singular) even though the
project uses `company.serializers` (plural). Keep this shim to avoid breakage.
"""

from utils.generate_ip_address import get_client_ip  # re-export
from utils.role_permission import create_company_role_family  # re-export

