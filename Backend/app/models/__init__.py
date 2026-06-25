# Import all models so that SQLAlchemy / Alembic can discover them via Base.metadata
from app.models.port import Port, Terminal  # noqa: F401
from app.models.vessel import Vessel, VesselType, VesselStatus  # noqa: F401
from app.models.berth import Berth, BerthType, BerthStatus  # noqa: F401
from app.models.voyage import Voyage, VoyageStatus  # noqa: F401
from app.models.visit import Visit, VisitStatus, CargoType, ClearanceStatus  # noqa: F401
from app.models.weather import WeatherData  # noqa: F401
from app.models.prediction import Prediction, PredictionType, PredictionStatus  # noqa: F401
from app.models.ai_registry import AIModelRegistry, ModelApprovalStatus, DeploymentEnvironment  # noqa: F401
from app.models.operations import CargoManifest, Container, BulkCargo  # noqa: F401
from app.models.resources import Equipment, EquipmentAllocation, LaborShift, LaborAllocation  # noqa: F401
from app.models.environmental import VesselEmission, WasteManagement  # noqa: F401
from app.models.iam import User, APIKey, AuditTrail, UserRole  # noqa: F401
from app.models.anomaly import Anomaly, AnomalyType, AnomalySeverity, AnomalyStatus  # noqa: F401
from app.models.notifications import Notification, NotificationTemplate  # noqa: F401
from app.models.reporting import KPIDefinition, KPIValue, Report  # noqa: F401
from app.models.research import AASTResearchProject, ResearchDataAccess, ResearchFinding  # noqa: F401
from app.models.governance import RegulatoryCompliance, SecurityIncident  # noqa: F401
from app.models.work_orders import WorkOrder, WorkOrderType, WorkOrderStatus, WorkOrderPriority  # noqa: F401
from app.models.engine_allocation import EngineAllocation  # noqa: F401
