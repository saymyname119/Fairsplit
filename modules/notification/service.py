from __future__ import annotations

import abc
import logging

from shared.events import DomainEvent, ExpenseCreated, SettlementRecorded, MemberAdded, GroupCreated

logger = logging.getLogger(__name__)


class INotifier(abc.ABC):
    @property
    @abc.abstractmethod
    def supported_event_types(self) -> list[str]: ...

    @abc.abstractmethod
    async def notify(self, event: DomainEvent) -> None: ...


class EmailNotifier(INotifier):
    @property
    def supported_event_types(self) -> list[str]:
        return ["ExpenseCreated", "SettlementRecorded"]

    async def notify(self, event: DomainEvent) -> None:
        if isinstance(event, ExpenseCreated):
            await self._send_expense_email(event)
        elif isinstance(event, SettlementRecorded):
            await self._send_settlement_email(event)

    async def _send_expense_email(self, event: ExpenseCreated) -> None:
        for split in event.splits:
            if split.user_id == event.paid_by_id:
                continue
                
            # Note: In a real app we'd fetch the user's email address here
            email_body = f"""
            Hi {split.user_id},
            
            A new expense "{event.description}" was added to group {event.group_id}.
            You owe ${split.owed_amount:.2f}.
            
            Thanks,
            Splitwise Clone Team
            """
            logger.info(f"EMAIL TO {split.user_id}:\n{email_body}")

    async def _send_settlement_email(self, event: SettlementRecorded) -> None:
        email_body = f"""
        Hi {event.to_user_id},
        
        You received a payment of ${event.amount:.2f} from {event.from_user_id} in group {event.group_id}.
        
        Thanks,
        Splitwise Clone Team
        """
        logger.info(f"EMAIL TO {event.to_user_id}:\n{email_body}")


class InAppNotifier(INotifier):
    @property
    def supported_event_types(self) -> list[str]:
        return ["ExpenseCreated", "SettlementRecorded", "MemberAdded"]

    async def notify(self, event: DomainEvent) -> None:
        # For Prompt 2, we just log. In Prompt 3, we'd insert into a notifications table.
        if isinstance(event, ExpenseCreated):
            for split in event.splits:
                if split.user_id != event.paid_by_id:
                    logger.info(f"PUSH NOTIFICATION to {split.user_id}: You owe ${split.owed_amount:.2f} for {event.description}")
        elif isinstance(event, SettlementRecorded):
            logger.info(f"PUSH NOTIFICATION to {event.to_user_id}: {event.from_user_id} paid you ${event.amount:.2f}")
        elif isinstance(event, MemberAdded):
            logger.info(f"PUSH NOTIFICATION to {event.user_id}: You were added to group {event.group_id}")


def register_notification_handlers(bus) -> None:
    email_notifier = EmailNotifier()
    for event_type in email_notifier.supported_event_types:
        bus.subscribe(f"expense.{event_type}", email_notifier.notify)
        bus.subscribe(f"ledger.{event_type}", email_notifier.notify)

    in_app_notifier = InAppNotifier()
    for event_type in in_app_notifier.supported_event_types:
        bus.subscribe(f"expense.{event_type}", in_app_notifier.notify)
        bus.subscribe(f"ledger.{event_type}", in_app_notifier.notify)
        bus.subscribe(f"group.{event_type}", in_app_notifier.notify)
