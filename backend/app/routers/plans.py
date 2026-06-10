from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from pydantic import BaseModel, field_validator
from typing import Optional
import asyncio

from app.database import get_db
from app.models import Employee, Department, AssessmentPlan, AssessmentRecord, EvalTemplate, RecordStatus
from app.routers.auth import UserInfo, get_login_user
from app.permissions import require_hr_user, require_admin_user, require_any_user
from app.services.wecom import wecom_service
from app.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/api", tags=["业务"])


# ── 考核计划 ──

class PlanCreate(BaseModel):
    name: str
    cycle_type: str
    start_date: str
    end_date: str
    self_eval_start: Optional[str] = None
    self_eval_end: Optional[str] = None
    manager_eval_end: Optional[str] = None
    approval_chain: list[str]
    dept_ids: Optional[list[int]] = None

    # 将空字符串转为 None，避免 DateTime 字段写入空字符串导致数据库报错
    @field_validator('self_eval_start', 'self_eval_end', 'manager_eval_end', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v is None or (isinstance(v, str) and v.strip() == ''):
            return None
        return v


@router.get("/plans")
def list_plans(user: UserInfo = Depends(get_login_user), db: Session = Depends(get_db)):
    # 联表查询获取创建者姓名
    stmt = (
        select(AssessmentPlan, Employee.name)
        .outerjoin(Employee, AssessmentPlan.created_by == Employee.id)
        .order_by(AssessmentPlan.created_at.desc())
    )
    rows = db.execute(stmt).all()

    return [
        {
            "id": row[0].id,
            "name": row[0].name,
            "cycle_type": row[0].cycle_type,
            "status": row[0].status,
            "start_date": str(row[0].start_date),
            "end_date": str(row[0].end_date),
            "self_eval_end": str(row[0].self_eval_end) if row[0].self_eval_end else None,
            "created_by_name": row[1] if row[1] else "系统",
        }
        for row in rows
    ]


@router.post("/plans")
async def create_plan(body: PlanCreate, user: UserInfo = Depends(require_admin_user), db: Session = Depends(get_db)):
    plan = AssessmentPlan(
        name=body.name, cycle_type=body.cycle_type,
        start_date=body.start_date, end_date=body.end_date,
        self_eval_start=body.self_eval_start, self_eval_end=body.self_eval_end,
        manager_eval_end=body.manager_eval_end,
        approval_chain=body.approval_chain,
        status="running", created_by=user.id,
    )
    db.add(plan)
    db.flush()

    stmt = select(Employee).where(Employee.status == "active")
    if body.dept_ids:
        stmt = stmt.where(Employee.dept_id.in_(body.dept_ids))
    employees = db.execute(stmt).scalars().all()

    # 创建考核记录
    for emp in employees:
        record = AssessmentRecord(
            plan_id=plan.id, employee_id=emp.id,
            status=RecordStatus.PENDING.value, current_step="self_eval",
        )
        db.add(record)
    db.flush()

    # 提取员工信息用于异步推送（避免 DetachedInstanceError）
    employee_data = [(emp.wecom_userid, emp.name) for emp in employees]

    # 异步推送企微消息给所有员工
    async def send_notifications():
        import logging
        logger = logging.getLogger(__name__)
        success_count = 0
        fail_count = 0

        for wecom_userid, emp_name in employee_data:
            try:
                # 构造消息内容
                self_eval_end_str = body.self_eval_end if body.self_eval_end else "待定"
                description = f"考核周期：{body.cycle_type}\n自评截止时间：{self_eval_end_str}\n请及时完成自评"

                await wecom_service.send_textcard(
                    touser=wecom_userid,
                    title=f"新考核通知：{body.name}",
                    description=description,
                    url=f"{settings.APP_BASE_URL}/employee/assessments"
                )
                success_count += 1
            except Exception as e:
                fail_count += 1
                logger.error(f"发送消息给 {emp_name}({wecom_userid}) 失败: {str(e)}")

        logger.info(f"考核计划 {body.name} 消息推送完成 - 成功:{success_count}, 失败:{fail_count}, 总计:{len(employee_data)}")

    # 在后台执行消息推送
    asyncio.create_task(send_notifications())

    return {"id": plan.id, "message": f"考核计划已创建，覆盖 {len(employees)} 人，正在推送通知"}



# ── 我的考核 ──

@router.get("/my/assessments")
def my_assessments(user: UserInfo = Depends(get_login_user), db: Session = Depends(get_db)):
    stmt = (
        select(AssessmentRecord, AssessmentPlan.name, AssessmentPlan.cycle_type)
        .join(AssessmentPlan, AssessmentRecord.plan_id == AssessmentPlan.id)
        .where(AssessmentRecord.employee_id == user.id)
        .order_by(AssessmentRecord.created_at.desc())
    )
    rows = db.execute(stmt).all()
    return [
        {
            "id": r[0].id, "plan_name": r[1], "cycle_type": r[2],
            "status": r[0].status, "current_step": r[0].current_step,
            "final_score": r[0].final_score,
        }
        for r in rows
    ]


# ── 模板 ──

class TemplateCreate(BaseModel):
    name: str
    type: str
    dimensions: list[dict]


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    dimensions: Optional[list[dict]] = None


@router.get("/templates")
def list_templates(user: UserInfo = Depends(get_login_user), db: Session = Depends(get_db)):
    """管理员可查看所有系统模板（只读）；普通员工仅查看自己的个人模板"""
    from app.permissions import get_user_role, Role
    role = get_user_role(user, db)
    if role == Role.ADMIN:
        stmt = select(EvalTemplate).order_by(EvalTemplate.created_at.desc())
    else:
        stmt = select(EvalTemplate).where(
            EvalTemplate.created_by == user.id,
            EvalTemplate.is_personal == True
        ).order_by(EvalTemplate.created_at.desc())
    templates = db.execute(stmt).scalars().all()
    return [
        {"id": t.id, "name": t.name, "type": t.type, "dimensions": t.dimensions_json,
         "is_default": t.is_default, "is_personal": t.is_personal, "created_by": t.created_by}
        for t in templates
    ]


@router.get("/templates/mine")
def list_my_templates(user: UserInfo = Depends(get_login_user), db: Session = Depends(get_db)):
    """返回当前员工的个人模板列表"""
    stmt = select(EvalTemplate).where(
        EvalTemplate.created_by == user.id,
        EvalTemplate.is_personal == True
    ).order_by(EvalTemplate.created_at.desc())
    templates = db.execute(stmt).scalars().all()
    return [
        {"id": t.id, "name": t.name, "type": t.type, "dimensions": t.dimensions_json,
         "is_default": t.is_default, "is_personal": t.is_personal}
        for t in templates
    ]


@router.post("/templates")
def create_template(body: TemplateCreate, user: UserInfo = Depends(require_any_user), db: Session = Depends(get_db)):
    """任何登录员工均可创建个人模板"""
    template = EvalTemplate(
        name=body.name, type=body.type,
        dimensions_json=body.dimensions,
        created_by=user.id, is_personal=True
    )
    db.add(template)
    db.flush()
    return {"id": template.id, "message": "模板已创建"}


@router.put("/templates/{template_id}")
def update_template(template_id: int, body: TemplateUpdate, user: UserInfo = Depends(require_any_user), db: Session = Depends(get_db)):
    """仅模板创建者可编辑"""
    template = db.execute(select(EvalTemplate).where(EvalTemplate.id == template_id)).scalar_one_or_none()
    if not template:
        raise HTTPException(404, "模板不存在")
    if template.created_by != user.id:
        raise HTTPException(403, "无权编辑他人模板")
    if body.name is not None:
        template.name = body.name
    if body.type is not None:
        template.type = body.type
    if body.dimensions is not None:
        template.dimensions_json = body.dimensions
    db.flush()
    return {"message": "模板已更新"}


@router.delete("/templates/{template_id}")
def delete_template(template_id: int, user: UserInfo = Depends(require_any_user), db: Session = Depends(get_db)):
    """仅模板创建者可删除"""
    template = db.execute(select(EvalTemplate).where(EvalTemplate.id == template_id)).scalar_one_or_none()
    if not template:
        raise HTTPException(404, "模板不存在")
    if template.created_by != user.id:
        raise HTTPException(403, "无权删除他人模板")
    db.delete(template)
    db.flush()
    return {"message": "模板已删除"}


# ── 数据概览 ──

@router.get("/dashboard/overview")
def dashboard_overview(user: UserInfo = Depends(get_login_user), db: Session = Depends(get_db)):
    total_employees = db.execute(select(func.count(Employee.id)).where(Employee.status == "active")).scalar()
    total_depts = db.execute(select(func.count(Department.id))).scalar()
    active_plans = db.execute(select(func.count(AssessmentPlan.id)).where(AssessmentPlan.status == "running")).scalar()
    return {"total_employees": total_employees, "total_departments": total_depts, "active_plans": active_plans}
