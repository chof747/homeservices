import os
from typing import Dict, List
from influxdb_client import QueryApi
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from ...services import MODEL_PATH
import logging

# Configure logging

class MissingParameters(Exception):
  pass

class WindowPredictor:

  PREDICTOR_MODEL_PATH = Path(MODEL_PATH) / "windowpredictor" / "modelparameter.csv"

  def __init__(self, influx_query_api: QueryApi):
    """
    Initializes the WindowPredictor with an InfluxDB query API.

    :param influx_query_api: The InfluxDB query API to be used for fetching data.
    """
    self.influx_engine = influx_query_api
    self.myPath = Path(__file__).parent
    self.parameters: pd.DateFrame = None
    self.data: pd.DataFrame = None

    logging.basicConfig(level = logging.DEBUG)
    self.logger = logging.getLogger('WindowPredictor')

    self.predictable = self._loadModel()

  def _createFluxQuery(self, rooms: List[str], predict: bool = True) -> str:
    """
    Creates the Flux query based on the jinja template.

    :param room: The room that is queried.
    :return str: the flux query string.
    """

    params = {
      'room': rooms,
      'timeRangeStart': '-10m' if predict else None
    }

    fluxTemplateEnv = Environment(loader=FileSystemLoader(self.myPath / "flux"))
    fluxTemplate = fluxTemplateEnv.get_template('humidity-temp.flux.jinja2')
    flux_query = fluxTemplate.render(influxBucket = os.environ['INFLUX_BUCKET'], **params)
    self.logger.debug(flux_query)
    return flux_query
  
  def _fetchData(self, querystr: str) -> pd.DataFrame:
    """
    Execute a flux query and fetch the data
    """
    df = self.influx_engine.query_data_frame(querystr)
    if isinstance(df, list):
      # Concatenate all DataFrames in the list
      df = pd.concat(df, ignore_index=True)    
    
    return df
  
  def _prepareData(self, df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare the obtained timeseries data.
    :param df: The dataframe to prepare
    """
    df['delta_T'] = df.groupby('Room')['Temperatur'].diff()
    df['delta_H'] = df.groupby('Room')['Luftfeuchtigkeit'].diff()
    df['_time'] = pd.to_datetime(df['_time'], format='mixed')
    
    return df.dropna()
  

  def _saveModel(self) -> None:
    """
    Saves the model in the model data space and creates the directory if it does not exist
    """
    
    if not WindowPredictor.PREDICTOR_MODEL_PATH.is_file():
      WindowPredictor.PREDICTOR_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    self.parameters.to_csv(WindowPredictor.PREDICTOR_MODEL_PATH)


  def _loadModel(self) -> bool:
    """
    Loads the model from the model location and returns True if it was present
    """

    if not WindowPredictor.PREDICTOR_MODEL_PATH.is_file():
      return False
    
    try:
      self.parameters = pd.read_csv(WindowPredictor.PREDICTOR_MODEL_PATH)
      return self._validateParameters()

    except (FileNotFoundError, pd.errors.EmptyDataError):
      self.logger.warn("The parameter file was not found or is empty. Recalculation of model parameters needed!")
    except (PermissionError, OSError) as e:
      self.logger.error(f"There are problems accessing the file: {e}")
    except (pd.errors.ParserError, ValueError):
      self.logger.warn("The parameter file could not be parsed. Recalculation of model parameters needed!")
    except Exception as e:
      self.logger.error(f"An unexpected error occurred: {e}")


  def _validateParameters(self) -> bool:
    """
    Validates the loaded model parameters
    """

    RECALC_TEXT = "Recalculation of model parameters needed!"

    if not self.parameters.index.name == 'room':
      self.logger.warn(
        f"Parameter file does not have the proper index. {RECALC_TEXT}")
      return False
    
    for col in ['delta_H_threshold', 'delta_T_threshold']:
      if not (col in self.parameters.columns):
        self.logger.warn(
          f"{col} column is missing. {RECALC_TEXT}")
        return False
      if not (pd.api.types.is_numeric_dtype(self.parameters[col])):
        self.logger.warn(
          f"{col} column is not numeric. {RECALC_TEXT}")
        return False
      
    return True

  
  
  def predict(self, rooms: List[str]) -> Dict[str, bool]:
    """
    Predicts whether a window has been opened recently in the specified room.

    :param room: The name of the room to predict the window status for.
    :return: True if a window has been opened recently, False otherwise.
    """
    if not self.predictable:
      raise MissingParameters("Prediction Model for WindowPredictor is not parameterized!")

    self.data = self._prepareData(
      self._fetchData(
        self._createFluxQuery(rooms)))

    return False
    

  def train(self) -> bool:
    """
    Trains the model based on historical data.

    The details of this method will be defined later.
    """
    # Implement the training logic here.
    # This method will prepare the model for making predictions based on historical data.
    raise NotImplementedError("The train method is not yet implemented.")