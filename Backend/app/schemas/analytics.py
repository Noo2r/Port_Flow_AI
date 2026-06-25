from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    total_visits: int
    active_visits: int
    completed_visits: int
    scheduled_visits: int
    avg_turnaround_minutes: float | None
    avg_waiting_minutes: float | None
    berth_utilization_percent: float
    total_berths: int
    occupied_berths: int
    total_vessels: int
    total_ports: int
    total_predictions: int
