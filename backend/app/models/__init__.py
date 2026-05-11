# Import all models here so Base.metadata.create_all() picks them up on init_db()
from app.models.conversation import *  # noqa
from app.models.approval import *      # noqa
from app.models.crm import *           # noqa
from app.models.lead import *          # noqa
from app.models.outreach import *      # noqa
from app.models.memory import *        # noqa
from app.models.tasks import *         # noqa
from app.models.scheduling import *    # noqa
from app.models.notifications import * # noqa
from app.models.intelligence import *  # noqa
from app.models.governance import *    # noqa
from app.models.knowledge import *     # noqa
from app.models.service_catalog import * # noqa
from app.models.ai_audit import *      # noqa
from app.models.team_member import *   # noqa
from app.models.gmail import *         # noqa
