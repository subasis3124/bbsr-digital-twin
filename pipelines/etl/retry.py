import time
import functools
from pipelines.etl.logging import get_etl_logger

logger = get_etl_logger("ETL.Retry")

def retry_operation(max_retries=3, backoff_factor=2.0, exceptions=(Exception,)):
    """
    Decorator to retry an operation with exponential backoff.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            delay = 1.0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Operation {func.__name__} failed after {max_retries} attempts: {e}")
                        raise
                    logger.warning(f"Operation {func.__name__} failed ({e}). Retrying in {delay:.1f}s (Attempt {retries}/{max_retries})...")
                    time.sleep(delay)
                    delay *= backoff_factor
            return func(*args, **kwargs)
        return wrapper
    return decorator
