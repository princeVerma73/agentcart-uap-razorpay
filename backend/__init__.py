import sys

from backend import config
from backend import audit
from backend.audit import ledger
from backend.audit import models as audit_models
from backend import merchant
from backend.merchant import catalog
from backend.merchant import models as merchant_models
from backend.merchant import growth_engine
from backend.merchant import analytics
from backend import security
from backend.security import policy_engine
from backend import payments
from backend.payments import razorpay_client
from backend import agent
from backend.agent import buyer_agent
from backend.agent import buyer_intent
from backend.agent import tools

# Guarantee that both `import backend.X` and `import X` reference the identical module singleton
sys.modules["config"] = config
sys.modules["audit"] = audit
sys.modules["audit.ledger"] = ledger
sys.modules["audit.models"] = audit_models
sys.modules["merchant"] = merchant
sys.modules["merchant.catalog"] = catalog
sys.modules["merchant.models"] = merchant_models
sys.modules["merchant.growth_engine"] = growth_engine
sys.modules["merchant.analytics"] = analytics
sys.modules["security"] = security
sys.modules["security.policy_engine"] = policy_engine
sys.modules["payments"] = payments
sys.modules["payments.razorpay_client"] = razorpay_client
sys.modules["agent"] = agent
sys.modules["agent.buyer_agent"] = buyer_agent
sys.modules["agent.buyer_intent"] = buyer_intent
sys.modules["agent.tools"] = tools

try:
    from backend import main
    sys.modules["main"] = main
except ImportError:
    pass
