from decimal import Decimal
from unittest.mock import patch

import pytest

from modules.notification.service import EmailNotifier, InAppNotifier
from shared.events import ExpenseCreated, ExpenseSplitEvent, SettlementRecorded


@pytest.mark.asyncio
async def test_email_notifier_expense_created():
    notifier = EmailNotifier()

    event = ExpenseCreated(
        expense_id="exp-1",
        group_id="group-1",
        paid_by_id="alice",
        amount=Decimal("30"),
        description="Dinner",
        splits=[
            ExpenseSplitEvent(user_id="alice", owed_amount=Decimal("15")),
            ExpenseSplitEvent(user_id="bob", owed_amount=Decimal("15")),
        ],
    )

    with patch("modules.notification.service.logger.info") as mock_logger:
        await notifier.notify(event)

        # Should only email Bob, not Alice (the payer)
        mock_logger.assert_called_once()
        log_msg = mock_logger.call_args[0][0]
        assert "EMAIL TO bob" in log_msg
        assert "15.00" in log_msg


@pytest.mark.asyncio
async def test_in_app_notifier_settlement_recorded():
    notifier = InAppNotifier()

    event = SettlementRecorded(
        settlement_id="set-1",
        group_id="group-1",
        from_user_id="bob",
        to_user_id="alice",
        amount=Decimal("15"),
    )

    with patch("modules.notification.service.logger.info") as mock_logger:
        await notifier.notify(event)

        mock_logger.assert_called_once()
        log_msg = mock_logger.call_args[0][0]
        assert "PUSH NOTIFICATION to alice" in log_msg
        assert "bob paid you $15.00" in log_msg
