from .base import *  # noqa: F403


APP_ENV = "development"
DEBUG = True
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", ["127.0.0.1", "localhost", "testserver"])
BACKGROUND_TASK_BACKEND = "threading"
