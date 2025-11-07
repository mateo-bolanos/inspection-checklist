from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.entities import CorrectiveAction, Inspection, InspectionResponse, InspectionStatus, TemplateItem
from app.schemas.dashboard import ActionMetrics, ItemsMetrics, ItemFailureMetric, OverviewMetrics


def get_overview_metrics(db: Session) -> OverviewMetrics:
    total_inspections = db.query(func.count(Inspection.id)).scalar() or 0
    submitted_inspections = (
        db.query(func.count(Inspection.id))
        .filter(Inspection.status.in_([InspectionStatus.submitted.value, InspectionStatus.approved.value, InspectionStatus.rejected.value]))
        .scalar()
        or 0
    )
    approved_inspections = (
        db.query(func.count(Inspection.id))
        .filter(Inspection.status == InspectionStatus.approved.value)
        .scalar()
        or 0
    )
    average_score = db.query(func.avg(Inspection.overall_score)).scalar()
    approval_rate = 0.0
    if submitted_inspections:
        approval_rate = round((approved_inspections / submitted_inspections) * 100, 2)
    return OverviewMetrics(
        total_inspections=total_inspections,
        submitted_inspections=submitted_inspections,
        approval_rate=approval_rate,
        average_score=round(float(average_score), 2) if average_score is not None else None,
    )


def get_action_metrics(db: Session) -> ActionMetrics:
    open_actions = (
        db.query(CorrectiveAction.severity, func.count(CorrectiveAction.id))
        .filter(CorrectiveAction.status != "closed")
        .group_by(CorrectiveAction.severity)
        .all()
    )
    open_by_severity: dict[str, int] = defaultdict(int)
    for severity, count in open_actions:
        open_by_severity[severity] = count

    now = datetime.now(timezone.utc)
    overdue_actions = (
        db.query(func.count(CorrectiveAction.id))
        .filter(
            CorrectiveAction.status != "closed",
            CorrectiveAction.due_date.isnot(None),
            CorrectiveAction.due_date < now,
        )
        .scalar()
        or 0
    )
    return ActionMetrics(open_by_severity=dict(open_by_severity), overdue_actions=overdue_actions)


def get_item_failure_metrics(db: Session, limit: int = 5) -> ItemsMetrics:
    rows = (
        db.query(
            TemplateItem.id,
            TemplateItem.prompt,
            func.count(InspectionResponse.id).label("total"),
            func.sum(case((InspectionResponse.result == "fail", 1), else_=0)).label("failures"),
        )
        .join(InspectionResponse, InspectionResponse.template_item_id == TemplateItem.id)
        .group_by(TemplateItem.id)
        .order_by(func.sum(case((InspectionResponse.result == "fail", 1), else_=0)).desc())
        .limit(limit)
        .all()
    )
    failures: list[ItemFailureMetric] = []
    for item_id, prompt, total, fail_count in rows:
        if not total:
            continue
        rate = round((fail_count or 0) / total * 100, 2)
        failures.append(ItemFailureMetric(item_id=item_id, prompt=prompt, fail_rate=rate))
    return ItemsMetrics(failures=failures)
