from __future__ import annotations

from app.config import settings
from app.schemas import SearchHit, WorkflowResponse, WorkflowStep
from app.services.llm import llm_service
from app.services.search_store import search_store

HIGH_RISK_TERMS = ("冒烟", "明火", "燃油", "泄漏", "漏油", "高温", "烧焦", "紧急")
MEDIUM_RISK_TERMS = ("异响", "无法启动", "熄火", "怠速", "过热", "压力", "电气")


def _risk_level(text: str) -> str:
    if any(term in text for term in HIGH_RISK_TERMS):
        return "high"
    if any(term in text for term in MEDIUM_RISK_TERMS):
        return "medium"
    return "low"

WORKFLOW_TEMPLATES: dict[str, dict[str, dict]] = {
    "摩托车发动机": {
        "daily": {
            "name": "日常点检",
            "safety_notes": ["佩戴防护手套", "发动机冷却后再检查", "禁止运转中触碰运动部件"],
            "steps": [
                {
                    "order": 1,
                    "title": "外观与泄漏检查",
                    "description": "检查发动机外壳、油管、冷却液有无渗漏",
                    "tools": ["手电筒"],
                    "compliance": ["记录异常点拍照"],
                    "required": True,
                },
                {
                    "order": 2,
                    "title": "机油液位检查",
                    "description": "水平放置车辆，抽出油尺检查液位是否在标准刻线之间",
                    "tools": ["抹布"],
                    "compliance": ["液位不足需补充并查因"],
                    "required": True,
                },
                {
                    "order": 3,
                    "title": "冷却与皮带检查",
                    "description": "检查散热器、风扇皮带张紧度",
                    "tools": [],
                    "compliance": ["皮带裂纹需更换"],
                    "required": False,
                },
            ],
        },
        "level1": {
            "name": "一级检修",
            "safety_notes": ["断开蓄电池负极", "确认举升设备锁定", "使用绝缘工具"],
            "steps": [
                {
                    "order": 1,
                    "title": "断电与隔离",
                    "description": "关闭电源总开关，挂警示牌",
                    "tools": ["警示牌", "绝缘手套"],
                    "compliance": ["双人确认断电"],
                    "required": True,
                },
                {
                    "order": 2,
                    "title": "火花塞与点火系统",
                    "description": "拆检火花塞，检查电极间隙与积碳",
                    "tools": ["火花塞套筒", "塞尺"],
                    "compliance": ["间隙超差必须调整或更换"],
                    "required": True,
                },
                {
                    "order": 3,
                    "title": "空气滤清器保养",
                    "description": "清洁或更换空气滤芯",
                    "tools": ["螺丝刀"],
                    "compliance": ["安装后检查密封"],
                    "required": True,
                },
            ],
        },
        "level2": {
            "name": "二级检修",
            "safety_notes": ["必须办理工作票", "燃油系统作业严禁明火", "废油分类回收"],
            "steps": [
                {
                    "order": 1,
                    "title": "燃油系统检查",
                    "description": "检查油路接头、滤清器及喷油嘴工作状态",
                    "tools": ["压力表", "扳手组"],
                    "compliance": ["测压值记录入检修单"],
                    "required": True,
                },
                {
                    "order": 2,
                    "title": "气门间隙调整",
                    "description": "按手册规定冷态调整进气/排气气门间隙",
                    "tools": ["塞尺", "开口扳手"],
                    "compliance": ["调整后复检一遍"],
                    "required": True,
                },
                {
                    "order": 3,
                    "title": "试运转与记录",
                    "description": "怠速及负载试运转，监听异响，检查排放",
                    "tools": ["转速表"],
                    "compliance": ["异常立即停机排查"],
                    "required": True,
                },
            ],
        },
        "emergency": {
            "name": "紧急故障处置",
            "safety_notes": ["优先确保人员安全", "疑似火情立即撤离", "禁止带故障强行运转"],
            "steps": [
                {
                    "order": 1,
                    "title": "紧急停机",
                    "description": "立即切断动力源，释放系统压力",
                    "tools": [],
                    "compliance": ["通报班组长"],
                    "required": True,
                },
                {
                    "order": 2,
                    "title": "快速定位",
                    "description": "根据报警信息与现场现象判断故障类型",
                    "tools": ["听诊器", "测温枪"],
                    "compliance": ["禁止盲目拆检"],
                    "required": True,
                },
                {
                    "order": 3,
                    "title": "临时处置与上报",
                    "description": "采取临时措施防止扩大损失，提交故障报告",
                    "tools": ["应急工具箱"],
                    "compliance": ["完整填写故障单"],
                    "required": True,
                },
            ],
        },
    },
}


def _resolve_device_key(device_model: str) -> str:
    if any(k in device_model for k in ("摩托", "发动机", "250")):
        return "摩托车发动机"
    return "摩托车发动机"


def _append_fault_steps(steps: list[WorkflowStep], fault_description: str | None) -> list[WorkflowStep]:
    if not fault_description:
        return steps
    titles = {s.title for s in steps}
    next_order = max((s.order for s in steps), default=0) + 1
    additions: list[WorkflowStep] = []
    if "机油" in fault_description or "漏油" in fault_description or "渗漏" in fault_description:
        additions.append(
            WorkflowStep(
                order=next_order,
                title="润滑与泄漏复核",
                description="复核油位、油管接头、密封垫和机油泵区域，确认是否存在渗漏或油位异常",
                tools=["手电筒", "抹布", "扳手组"],
                compliance=["擦净后短时观察渗漏点", "废油按规范回收"],
                checkpoint="记录渗漏位置、油位和处理结果",
                required=True,
            )
        )
        next_order += 1
    if "火花塞" in fault_description or "点火" in fault_description or "无法启动" in fault_description:
        additions.append(
            WorkflowStep(
                order=next_order,
                title="点火部件复核",
                description="检查火花塞电极、积碳、间隙和高压帽连接状态",
                tools=["火花塞套筒", "塞尺", "尖嘴钳"],
                compliance=["拆装方向按手册执行", "异常件不得继续带病使用"],
                checkpoint="记录火花塞状态和间隙复测结果",
                required=True,
            )
        )
    for step in additions:
        if step.title not in titles:
            steps.append(step)
    return steps


def _offline_summary(
    device_model: str,
    maintenance_level: str,
    risk: str,
    fault_description: str | None,
    evidence_count: int,
) -> str:
    risk_text = {"high": "高风险", "medium": "中风险", "low": "低风险"}.get(risk, "风险未知")
    return (
        f"{device_model} 本次作业为 {maintenance_level}，判定为{risk_text}。"
        f"故障线索：{fault_description or '未填写'}。"
        f"系统已关联 {evidence_count} 条手册/案例证据；执行时必须先完成安全隔离，"
        "逐项确认必填检查点，试运行正常后再归档。"
    )


async def build_workflow(
    device_model: str,
    maintenance_level: str,
    fault_description: str | None = None,
) -> WorkflowResponse:
    device_key = _resolve_device_key(device_model)
    templates = WORKFLOW_TEMPLATES.get(device_key, WORKFLOW_TEMPLATES["摩托车发动机"])
    tpl = templates.get(maintenance_level, templates["daily"])
    steps = [WorkflowStep(**s) for s in tpl["steps"]]
    steps = _append_fault_steps(steps, fault_description)

    evidence_hits: list[SearchHit] = []
    if fault_description:
        hits = search_store.search(f"{device_model} {fault_description}", top_k=3)
        evidence_hits = [SearchHit(**h) for h in hits]
    rag_context = "\n".join(h.content[:300] for h in evidence_hits)
    risk = _risk_level(f"{maintenance_level} {fault_description or ''}")
    estimated_minutes = {
        "daily": 15,
        "level1": 45,
        "level2": 90,
        "emergency": 30,
    }.get(maintenance_level, 30) + max(0, len(steps) - len(tpl["steps"])) * 10

    prompt = (
        f"设备：{device_model}\n检修等级：{maintenance_level}\n"
        f"风险等级：{risk}\n"
        f"故障描述：{fault_description or '无'}\n"
        f"标准步骤：{[s.title for s in steps]}\n"
        f"相关资料：{rag_context or '无'}"
    )
    offline_summary = _offline_summary(
        device_model,
        maintenance_level,
        risk,
        fault_description,
        len(evidence_hits),
    )
    llm_summary = offline_summary
    if settings.llm_mode.lower() != "mock":
        generated, fallback_reason = await llm_service.generate(
            f"你是检修班组长，用简洁中文总结本次作业要点、风险与注意事项。\n\n{prompt}"
        )
        if not fallback_reason:
            llm_summary = generated

    return WorkflowResponse(
        workflow_name=tpl["name"],
        device_model=device_model,
        maintenance_level=maintenance_level,
        steps=steps,
        safety_notes=list(tpl["safety_notes"]),
        llm_summary=llm_summary,
        risk_level=risk,
        estimated_minutes=estimated_minutes,
        evidence_hits=evidence_hits,
    )
