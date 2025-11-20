import asyncio
import smtplib
import time
from email.header import Header
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional

from pydantic import Field

from app.exceptions import ToolError
from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.footbook.seat_reserver import SeatReserver


class FootbookSeatReservation(BaseTool):
    """Tool wrapper for the Footbook seat reservation script."""

    name: str = "footbook_seat_reservation"
    description: str = (
        "预约图书馆座位。使用天津大学Footbook预约接口完成登录、查询和下单。"
        "需要提供学号、密码。"
        "可选指定区域（A/B）或具体座位号，若不指定则自动寻找空座。"
        "可选提供邮箱地址，若提供，无论预约成功还是失败，系统都会自动发送邮件通知。"
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "student_id": {
                "type": "string",
                "description": "学号，将用于登录 Footbook 系统。",
            },
            "password": {
                "type": "string",
                "description": "密码，用于登录 Footbook 系统。",
            },
            "email": {
                "type": "string",
                "description": "可选。用户的邮箱地址。如果提供，将在预约结束后发送结果通知（无论成功或失败）。",
            },
            "target_area": {
                "type": "string",
                "enum": ["A", "B"],
                "description": "可选，指定预约区域（A/B）。不填则自动搜索全部区域。",
            },
            "target_seat_no": {
                "type": "integer",
                "description": (
                    "可选，指定区域内的座位号。仅在 target_area 同时提供时生效。"
                ),
            },
        },
        "required": ["student_id", "password"],
    }

    config_path: Path = Field(
        default=Path(__file__).with_name("seat_reserver.ini"), exclude=True
    )

    # ================= 邮箱配置区域 =================
    SMTP_SERVER: ClassVar[str] = "smtp.qq.com"
    SMTP_PORT: ClassVar[int] = 465
    SENDER_EMAIL: ClassVar[str] = "3758429742@qq.com"
    SENDER_PASSWORD: ClassVar[str] = "eukehtpwvpvkcfhd"
    # ===========================================

    # 记录上次发送失败邮件的时间戳 (类变量，所有实例共享)
    _last_failure_time: ClassVar[float] = 0.0
    # 失败邮件冷却时间 (秒)
    FAILURE_COOLDOWN: ClassVar[int] = 300

    async def execute(
        self,
        student_id: str,
        password: str,
        email: Optional[str] = None,
        target_area: Optional[str] = None,
        target_seat_no: Optional[int] = None,
    ) -> ToolResult:
        reserver = self._build_reserver()

        reserver.configure_user(
            username=student_id,
            password=password,
            target_area=target_area,
            target_seat_no=target_seat_no,
        )

        try:
            reservation_response = await asyncio.to_thread(reserver.run)

            # 成功 -> 如果有邮箱则发送 (成功邮件不限频)
            if email:
                seat_info = reservation_response.get("seat_info", {})
                area_label = seat_info.get("area", "未知区域")
                seat_num = seat_info.get("seat_no", "未知座位")

                subject = "【OpenManus】图书馆座位预约成功"
                content = (
                    f"尊敬的用户：\n\n"
                    f"恭喜您，座位已预约成功！\n\n"
                    f"📋 预约详情：\n"
                    f"   - 学号：{student_id}\n"
                    f"   - 位置：{area_label} {seat_num}号\n"
                    f"   - 状态：已锁定\n\n"
                    f"请准时入馆签到。\n"
                )
                await self._send_email(email, subject, content)

        except Exception as exc:  # noqa: BLE001
            # 失败 -> 如果有邮箱则发送 (增加冷却判定)
            logger.error("Footbook reservation failed", exc_info=exc)

            if email:
                current_time = time.time()
                # 检查是否在冷却期内
                if current_time - self._last_failure_time > self.FAILURE_COOLDOWN:
                    subject = "【OpenManus】图书馆座位预约失败"
                    content = (
                        f"尊敬的用户：\n\n"
                        f"很抱歉，您的座位预约请求未能完成。\n\n"
                        f"❌ 失败原因：\n"
                        f"{str(exc)}\n\n"
                        f"建议您检查账号密码或稍后重试。"
                    )
                    await self._send_email(email, subject, content)
                    # 更新发送时间
                    FootbookSeatReservation._last_failure_time = current_time
                else:
                    logger.info(f"Failure email skipped due to cooldown ({self.FAILURE_COOLDOWN}s).")

            raise ToolError(f"Footbook 预约失败：{exc}") from exc

        output: Dict[str, Any] = {
            "student_id": student_id,
            "target_area": target_area or "auto",
            "target_seat_no": target_seat_no,
            "reservation_response": reservation_response,
        }
        if email:
            output["notification_status"] = f"已发送结果通知至 {email}"

        return ToolResult(output=output)

    def _build_reserver(self) -> SeatReserver:
        try:
            return SeatReserver(config_path=str(self.config_path))
        except FileNotFoundError as exc:
            raise ToolError(str(exc)) from exc

    async def _send_email(self, to_email: str, subject: str, content: str) -> None:
        """Internal helper to send email synchronously (wrapped in async)."""
        def _sync_send():
            try:
                message = MIMEText(content, 'plain', 'utf-8')
                message['From'] = self.SENDER_EMAIL
                message['To'] = to_email
                message['Subject'] = Header(subject, 'utf-8')

                if self.SMTP_PORT == 465:
                    smtp_obj = smtplib.SMTP_SSL(self.SMTP_SERVER, self.SMTP_PORT)
                else:
                    smtp_obj = smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT)

                smtp_obj.login(self.SENDER_EMAIL, self.SENDER_PASSWORD)
                smtp_obj.sendmail(self.SENDER_EMAIL, [to_email], message.as_string())
                smtp_obj.quit()
                logger.info(f"Email sent successfully to {to_email}")
            except Exception as e:
                logger.error(f"Failed to send email: {e}")
                # We log the error but don't stop the main process
                # or you could choose to raise it.

        await asyncio.to_thread(_sync_send)
