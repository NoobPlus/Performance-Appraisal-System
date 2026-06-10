#!/usr/bin/env python3
"""
开发环境测试数据初始化脚本
用于快速导入开发测试账号（管理员、HR、经理、员工）
"""

import argparse
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import SessionLocal, Base, engine
from app.models import Employee, Department

# 测试账号定义
TEST_USERS = [
    {
        "id": 999999,
        "name": "开发-管理员",
        "wecom_userid": "dev_admin",
        "position": "系统管理员",
        "level": "T9",
        "expected_role": "admin",
    },
    {
        "id": 999998,
        "name": "开发-HR",
        "wecom_userid": "dev_hr",
        "position": "HR专员",
        "level": "T7",
        "expected_role": "hr",
    },
    {
        "id": 999997,
        "name": "开发-经理",
        "wecom_userid": "dev_manager",
        "position": "部门经理",
        "level": "T8",
        "expected_role": "manager",
    },
    {
        "id": 999996,
        "name": "开发-员工",
        "wecom_userid": "dev_employee",
        "position": "软件工程师",
        "level": "T6",
        "expected_role": "employee",
    },
]

# 下属员工（用于测试 manager 角色）
SUBORDINATE_USERS = [
    {
        "id": 999995,
        "name": "开发-下属员工1",
        "wecom_userid": "dev_subordinate1",
        "position": "软件工程师",
        "level": "T5",
        "direct_leader_id": 999997,  # 指向 dev_manager
    },
    {
        "id": 999994,
        "name": "开发-下属员工2",
        "wecom_userid": "dev_subordinate2",
        "position": "产品经理",
        "level": "T5",
        "direct_leader_id": 999997,  # 指向 dev_manager
    },
]


def init_dev_data(reset: bool = False):
    """初始化开发测试数据"""
    db = SessionLocal()
    try:
        existing_users = db.execute(select(Employee)).scalars().all()
        if existing_users and not reset:
            print("✅ 检测到现有员工数据，跳过初始化。使用 --reset 参数可强制重置")
            return

        if reset:
            # 清除所有开发测试数据
            db.execute(
                Employee.__table__.delete().
                where(Employee.id >= 999994)
            )
            db.execute(
                Department.__table__.delete().
                where(Department.id == 999)
            )
            db.commit()
            print("🗑️  已清除现有开发测试数据")

        # 创建开发测试部门
        dev_dept = Department(
            id=999,
            name="开发测试部门",
            parent_id=None,
        )
        db.add(dev_dept)
        db.flush()

        # 创建测试账号
        for user in TEST_USERS:
            employee = Employee(
                id=user["id"],
                name=user["name"],
                wecom_userid=user["wecom_userid"],
                dept_id=999,
                position=user["position"],
                level=user["level"],
                status="active",
            )
            db.add(employee)
            db.flush()
            print(f"👤 创建测试账号: {user['name']} ({user['expected_role']})")

        # 创建下属员工
        for sub in SUBORDINATE_USERS:
            employee = Employee(
                id=sub["id"],
                name=sub["name"],
                wecom_userid=sub["wecom_userid"],
                dept_id=999,
                position=sub["position"],
                level=sub["level"],
                direct_leader_id=sub["direct_leader_id"],
                status="active",
            )
            db.add(employee)
            db.flush()
            print(f"👥 创建下属员工: {sub['name']}")
        
        # 注意：dev_manager 天然拥有下属（dev_subordinate1, dev_subordinate2），将获得 manager 角色

        db.commit()
        print("\n✅ 开发测试数据初始化完成！")
        print("\n📋 可用测试账号:")
        for user in TEST_USERS:
            print(f"   - {user['wecom_userid']} : {user['name']} ({user['expected_role']})")

    except Exception as e:
        db.rollback()
        print(f"❌ 初始化失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="初始化开发测试数据")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="重置已有开发测试数据",
    )
    args = parser.parse_args()
    init_dev_data(reset=args.reset)