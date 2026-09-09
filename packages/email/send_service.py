import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from packages.common.models.email import (
    EmailAccount,
    EmailThread,
    EmailMessage,
    EmailProviderType,
    MailboxHealthStatus,
    ThreadStatus,
    MessageDirection,
    DeliveryStatus
)
from packages.common.models.crm import CRMLead
from packages.common.encryption import TokenEncryptor
from packages.common.distributed_lock import DistributedLock
from packages.email.base import EmailProvider, OutboundEmail, SendResult
from packages.email.adapters.gmail_adapter import GmailProvider
from packages.email.adapters.graph_adapter import GraphProvider
from packages.email.suppression import SuppressionChecker

logger = logging.getLogger("codenter.email.send")

class EmailDeliveryError(Exception):
    pass

class EmailSendService:
    @classmethod
    async def dispatch_email(
        cls,
        workspace_id: str,
        account_id: str,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        lead_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[list[str]] = None,
        db: Optional[AsyncSession] = None,
        custom_provider: Optional[EmailProvider] = None
    ) -> EmailMessage:
        if db is None:
            raise ValueError("AsyncSession 'db' is required for email dispatch")

        # 1. Acquire Distributed Lock (Double-Sending Protection)
        lock_key = f"send_lock:{workspace_id}:{lead_id or to_email}"
        async with DistributedLock(lock_key, ttl_seconds=30):

            # 2. Re-check Suppression List
            if await SuppressionChecker.is_email_suppressed(workspace_id, to_email, db):
                logger.warning(f"Aborting email dispatch to {to_email}: Email or domain is suppressed.")
                raise EmailDeliveryError(f"Email '{to_email}' is suppressed in workspace '{workspace_id}'")

            # 3. Verify Email Account & Deliverability Daily Limits
            acc_res = await db.execute(
                select(EmailAccount).where(
                    EmailAccount.id == account_id,
                    EmailAccount.workspace_id == workspace_id
                )
            )
            account = acc_res.scalar_one_or_none()
            if not account:
                raise EmailDeliveryError(f"Email account {account_id} not found in workspace {workspace_id}")

            if account.health_status == MailboxHealthStatus.REVOKED:
                raise EmailDeliveryError(f"Mailbox {account.email_address} is REVOKED due to authentication failure")

            if account.health_status == MailboxHealthStatus.PAUSED:
                raise EmailDeliveryError(f"Mailbox {account.email_address} is PAUSED")

            if account.current_day_sends >= account.daily_send_limit:
                raise EmailDeliveryError(
                    f"Mailbox {account.email_address} exceeded daily limit ({account.current_day_sends}/{account.daily_send_limit})"
                )

            # 4. Decrypt OAuth Credentials
            encryptor = TokenEncryptor()
            try:
                decrypted_cred = encryptor.decrypt(account.encrypted_credentials)
                credentials = {"access_token": decrypted_cred}
            except Exception as e:
                logger.error(f"Failed decrypting credentials for mailbox {account.id}: {e}")
                raise EmailDeliveryError(f"Decryption error: {e}")

            # 5. Select Provider Adapter
            provider = custom_provider
            if provider is None:
                if account.provider == EmailProviderType.GOOGLE:
                    provider = GmailProvider()
                elif account.provider == EmailProviderType.MICROSOFT:
                    provider = GraphProvider()
                else:
                    raise EmailDeliveryError(f"Provider {account.provider} not supported for direct sending")

            # 6. Construct Outbound Message
            outbound_msg = OutboundEmail(
                from_address=account.email_address,
                to_address=to_email,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                thread_id=thread_id,
                in_reply_to=in_reply_to,
                references=references or []
            )

            # 7. Execute Send API Call
            send_res: SendResult = await provider.send_message(credentials, outbound_msg)

            # Handle 401 Authentication Failure (Immediate Mailbox Revocation)
            if send_res.status_code == 401 or send_res.error == "AUTHENTICATION_REVOKED":
                account.health_status = MailboxHealthStatus.REVOKED
                await db.commit()
                logger.critical(f"Mailbox {account.email_address} marked REVOKED due to 401 Unauthorized")
                raise EmailDeliveryError(f"Provider returned 401 Unauthorized. Mailbox {account.email_address} is now REVOKED.")

            if not send_res.success:
                logger.error(f"Provider send error for {to_email}: {send_res.error}")
                raise EmailDeliveryError(f"Email dispatch failed: {send_res.error}")

            # 8. Manage EmailThread
            now = datetime.now(timezone.utc)
            thread = None
            if thread_id:
                t_res = await db.execute(
                    select(EmailThread).where(
                        EmailThread.id == thread_id,
                        EmailThread.workspace_id == workspace_id
                    )
                )
                thread = t_res.scalar_one_or_none()

            if not thread:
                thread = EmailThread(
                    workspace_id=workspace_id,
                    lead_id=lead_id,
                    campaign_id=campaign_id,
                    subject=subject,
                    status=ThreadStatus.OPEN,
                    last_message_at=now
                )
                db.add(thread)
                await db.flush()
            else:
                thread.last_message_at = now

            # 9. Persist EmailMessage
            msg_record = EmailMessage(
                workspace_id=workspace_id,
                thread_id=thread.id,
                provider_message_id=send_res.provider_message_id,
                direction=MessageDirection.OUTBOUND,
                from_address=account.email_address,
                to_address=to_email,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                headers_json={"in_reply_to": in_reply_to, "references": references or []},
                delivery_status=DeliveryStatus.SENT
            )
            db.add(msg_record)

            # 10. Increment Daily Send Counter & Update Timestamp
            account.current_day_sends += 1
            account.last_send_at = now

            await db.commit()
            await db.refresh(msg_record)
            logger.info(f"Successfully sent outbound email to {to_email} (Msg ID: {send_res.provider_message_id})")
            return msg_record
