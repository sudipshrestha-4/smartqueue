from datetime import datetime, timedelta

# Nepal Standard Time (UTC+5:45) — used for daily counter reset boundaries
NPT_OFFSET = timedelta(hours=5, minutes=45)


def get_business_date():
    """Return today's date in Nepal Standard Time."""
    return (datetime.utcnow() + NPT_OFFSET).date()


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
