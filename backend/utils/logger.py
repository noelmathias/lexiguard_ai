from loguru import logger
import sys

logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")
logger.add("logs/app.log", rotation="10 MB", retention="7 days")
