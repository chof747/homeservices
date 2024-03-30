from typing import Union

from fastapi import FastAPI
from .services.windowsopen import service

app = FastAPI()

app.include_router(service.endpoint)
