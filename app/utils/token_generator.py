from datetime import datetime, timedelta

from app.extensions import db

# Nepal Standard Time (UTC+5:45) — used for daily counter reset and operating hours
NPT_OFFSET = timedelta(hours=5, minutes=45)


def get_local_now():
    """Return current datetime in Nepal Standard Time."""
    return datetime.utcnow() + NPT_OFFSET


def get_business_date():
    """Return today's date in Nepal Standard Time."""
    return get_local_now().date()


def get_bank_settings():
    """Return the singleton bank settings row, creating defaults if needed."""
    from app.models.bank_settings import BankSettings

    settings = BankSettings.query.first()
    if not settings:
        settings = BankSettings()
        db.session.add(settings)
        db.session.commit()
    return settings


def _format_time_12h(t):
    return t.strftime('%I:%M %p').lstrip('0')


def _format_hours_range(settings):
    return f'{_format_time_12h(settings.open_time)} – {_format_time_12h(settings.close_time)} NPT'


def is_within_operating_hours(settings):
    """True when current NPT time falls within configured open/close times."""
    current_time = get_local_now().time()
    open_t = settings.open_time
    close_t = settings.close_time

    if open_t <= close_t:
        return open_t <= current_time < close_t
    return current_time >= open_t or current_time < close_t


def is_bank_open(settings=None):
    """True when token generation is allowed (respects manual override and schedule)."""
    if settings is None:
        settings = get_bank_settings()

    if settings.manual_override == 'closed':
        return False
    if settings.manual_override == 'open':
        return True
    return is_within_operating_hours(settings)


def get_bank_status_info(settings=None):
    """Return bank open/closed state and customer-facing messaging."""
    if settings is None:
        settings = get_bank_settings()

    hours = _format_hours_range(settings)
    info = {
        'is_open': is_bank_open(settings),
        'hours': hours,
        'open_time': settings.open_time,
        'close_time': settings.close_time,
        'manual_override': settings.manual_override,
        'reason': 'open',
        'message': None,
    }

    if settings.manual_override == 'closed':
        info.update({
            'is_open': False,
            'reason': 'manual_closed',
            'message': (
                'The bank is temporarily closed. Token generation is unavailable '
                'until an administrator reopens the bank.'
            ),
        })
        return info

    if settings.manual_override == 'open':
        info.update({'reason': 'manual_open'})
        return info

    if is_within_operating_hours(settings):
        info.update({'reason': 'schedule_open'})
        return info

    info.update({
        'is_open': False,
        'reason': 'outside_hours',
        'message': (
            f'The bank is currently closed. Operating hours are {hours}. '
            'Please return during operating hours to get a token.'
        ),
    })
    return info


def generate_token_number(service, prefix='N'):
    """
    Increment the service's daily counter and return the next token number.
    Automatically resets the counter to 1 when the business date changes.
    Token format: {prefix}-{counter:03d}  e.g. N-001, P-002, E-003
    """
    today = get_business_date()
    if service.counter_reset_date != today:
        service.daily_token_counter = 0
        service.counter_reset_date = today

    service.daily_token_counter += 1
    return f"{prefix}-{service.daily_token_counter:03d}"
