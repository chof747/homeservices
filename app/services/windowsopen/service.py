from datetime import datetime
import logging
import os
from typing import Annotated, Dict, List, Union
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from ...dependencies import influxdb
from .predictor import WindowPredictor
from influxdb_client import QueryApi
from pydantic import BaseModel
from urllib.parse import unquote

logging.basicConfig(level = logging.DEBUG)
logger = logging.getLogger('WindowPredictor')


endpoint = APIRouter(prefix="/windowsopen")
influxDependency = Annotated[QueryApi, Depends(influxdb.fluxQuery)]

class WindowPrediction(BaseModel):
    room: str
    open: bool
    start: datetime = datetime.now() 


@endpoint.get("/test")
async def shakedown():
  return f"{os.environ}"

"""
API Call to predict if in a specific room/rooms the windows have been open
"""
@endpoint.get("/predict", tags=["windowsopen"], 
               response_model=Union[Dict[str, WindowPrediction], str],
               responses={
                  503 : {
                     "description" : "Model is not trained and cannot predict data",
                     "model" : dict,
                     "content" : {
                        "application/json": {
                           "example" : {
                            "error_message" : "The model is not ready for predictions, run train first!"
                           }
                        }
                     }
                  }
               })
async def predict(rooms:str, fluxquery : influxDependency) -> Union[Dict[str, WindowPrediction], str]:

  predictor = WindowPredictor(fluxquery)
  if (not predictor.predictable):
     return JSONResponse(content={
        "error_message" : "The model is not ready for predictions, run train first!"
     }, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
  
  rooms_splitted = rooms.split(',')
  result = {
     room: WindowPrediction(room=room, open=p) 
     for room, p in predictor.predict(rooms_splitted)
  }

  return result


"""
API Call to initiate training of the model
"""
@endpoint.post("/train", tags="windowsopen",
               response_model=Union[bool, str],
               responses={
                 500: {
                   "description" : "Model is not trained and cannot predict data",
                   "model" : dict,
                   "content" : {
                     "application/json": {
                        "example" : {
                           "error_message" : "The model cannot be predicted. Contact your Admin!"
                           }
                        }
                     }
                  }
               })
async def train(fluxquery : influxDependency) -> Union[bool, str]:
  predictor = WindowPredictor(fluxquery)

  error_msg = "The model cannot be predicted. Contact your Admin!"

  try:
    if predictor.train(): 
      return True
  except Exception as e:
    pass

  return JSONResponse(content={
    "error_message" : error_msg
  }, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)