from quotation.models import Quotation
from rfq.models import RfqMaster

APPROVAL_ON = ["rfq", "quotation"]
SIGNAL_SENDER = [RfqMaster, Quotation]
