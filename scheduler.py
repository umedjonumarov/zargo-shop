"""
ZarGo Shop — APScheduler
Har kuni soat 14:00 da 3 kun oldin xarid qilganlarga eslatma yuboradi.
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from database import db
from whatsapp_meta import send_3day_reminder

logger = logging.getLogger(__name__)


def _title(gender: str) -> str:
    return "опа" if gender == "female" else "ака"


def send_3day_reminders():
    """3 kun oldin buyurtma bergan mijozlarga eslatma yuboradi."""
    logger.info("3 kunlik eslatma vazifasi boshlandi...")
    try:
        orders = db.get_orders_3days_ago()
        if not orders:
            logger.info("3 kun oldin buyurtma yo'q.")
            return

        sent_phones = set()  # bir mijozga bir marta yuborish
        for order in orders:
            phone = str(order.get('phone', '')).strip()
            if not phone or phone in sent_phones:
                continue

            customer = db.get_customer(phone)
            name   = customer.get('name', '')  if customer else ''
            gender = customer.get('gender', 'unknown') if customer else 'unknown'
            title  = _title(gender)

            ok = send_3day_reminder(phone, name, title)
            if ok:
                sent_phones.add(phone)
                logger.info(f"Eslatma yuborildi: +{phone} ({name} {title})")
            else:
                logger.warning(f"Eslatma yuborilmadi: +{phone}")

        logger.info(f"3 kunlik eslatma tugadi. Yuborildi: {len(sent_phones)} ta")
    except Exception as e:
        logger.error(f"3 kunlik eslatma xatosi: {e}")


def start_scheduler():
    scheduler = BackgroundScheduler(timezone="Asia/Dushanbe")
    scheduler.add_job(
        send_3day_reminders,
        CronTrigger(hour=14, minute=0),
        id="3day_reminder",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler ishga tushdi (har kuni 14:00 Dushanbe vaqti)")
    return scheduler
