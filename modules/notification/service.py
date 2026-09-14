import abc
import asyncio
import logging

from modules.notification.resend_client import (
    ResendClient,
    render_invitation_html,
    render_invitation_text,
)
from shared.config import get_settings
from shared.events import (
    DomainEvent,
    ExpenseCreated,
    IEventBus,
    InvitationCreated,
    MemberAdded,
    SettlementRecorded,
)

logger = logging.getLogger(__name__)


class INotifier(abc.ABC):
    @property
    @abc.abstractmethod
    def supported_event_types(self) -> list[str]: ...

    @abc.abstractmethod
    def notify(self, event: DomainEvent) -> None: ...


class EmailNotifier(INotifier):
    def __init__(self, resend_client: ResendClient | None = None) -> None:
        self._settings = get_settings()
        self._resend = resend_client or ResendClient()

    @property
    def supported_event_types(self) -> list[str]:
        return ["ExpenseCreated", "SettlementRecorded", "InvitationCreated"]

    def notify(self, event: DomainEvent) -> None:
        if isinstance(event, ExpenseCreated):
            self._send_expense_email(event)
        elif isinstance(event, SettlementRecorded):
            self._send_settlement_email(event)
        elif isinstance(event, InvitationCreated):
            self._send_invitation_email(event)

    def _send_invitation_email(self, event: InvitationCreated) -> None:
        invite_url = f"{self._settings.app_base_url}/invite/accept?token={event.token}"
        subject = f"{event.invited_by_name} invited you to join \"{event.group_name}\" on Splitwise"
        html = render_invitation_html(
            group_name=event.group_name,
            invited_by_name=event.invited_by_name,
            invite_url=invite_url,
        )
        text = render_invitation_text(
            group_name=event.group_name,
            invited_by_name=event.invited_by_name,
            invite_url=invite_url,
        )

        logger.info(
            f"INVITATION EMAIL to {event.email} for group '{event.group_name}':\n"
            f"Link: {invite_url}"
        )

        if self._resend.is_configured:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    self._resend.send_email(
                        to=event.email,
                        subject=subject,
                        html=html,
                        text=text,
                    )
                )
            except RuntimeError:
                # In synchronous test or runner contexts without an active event loop
                logger.debug("No active event loop for Resend; skipping task")

    def _send_expense_email(self, event: ExpenseCreated) -> None:
        for split in event.splits:
            if split.user_id == event.paid_by_id:
                continue

            # Note: In a real app we'd fetch the user's email address here
            email_body = (
                f"Hi {split.user_id},\n\n"
                f'A new expense "{event.description}" was added to group {event.group_id}.\n'
                f"You owe ${split.owed_amount:.2f}.\n\n"
                "Thanks,\nSplitwise Clone Team"
            )
            logger.info(f"EMAIL TO {split.user_id}:\n{email_body}")

    def _send_settlement_email(self, event: SettlementRecorded) -> None:
        email_body = (
            f"Hi {event.to_user_id},\n\n"
            f"You received a payment of ${event.amount:.2f} from {event.from_user_id} "
            f"in group {event.group_id}.\n\n"
            "Thanks,\nSplitwise Clone Team"
        )
        logger.info(f"EMAIL TO {event.to_user_id}:\n{email_body}")


class InAppNotifier(INotifier):
    @property
    def supported_event_types(self) -> list[str]:
        return ["ExpenseCreated", "SettlementRecorded", "MemberAdded"]

    def notify(self, event: DomainEvent) -> None:
        # For Prompt 2, we just log. In Prompt 3, we'd insert into a notifications table.
        if isinstance(event, ExpenseCreated):
            for split in event.splits:
                if split.user_id != event.paid_by_id:
                    msg = (
                        f"PUSH NOTIFICATION to {split.user_id}: "
                        f"You owe ${split.owed_amount:.2f} for {event.description}"
                    )
                    logger.info(msg)
        elif isinstance(event, SettlementRecorded):
            msg = (
                f"PUSH NOTIFICATION to {event.to_user_id}: "
                f"{event.from_user_id} paid you ${event.amount:.2f}"
            )
            logger.info(msg)
        elif isinstance(event, MemberAdded):
            msg = f"PUSH NOTIFICATION to {event.user_id}: You were added to group {event.group_id}"
            logger.info(msg)


def register_notification_handlers(bus: IEventBus) -> None:
    email_notifier = EmailNotifier()
    bus.subscribe("expense.ExpenseCreated", email_notifier.notify)
    bus.subscribe("ledger.SettlementRecorded", email_notifier.notify)
    bus.subscribe("invitation.InvitationCreated", email_notifier.notify)

    in_app_notifier = InAppNotifier()
    bus.subscribe("expense.ExpenseCreated", in_app_notifier.notify)
    bus.subscribe("ledger.SettlementRecorded", in_app_notifier.notify)
    bus.subscribe("group.MemberAdded", in_app_notifier.notify)

