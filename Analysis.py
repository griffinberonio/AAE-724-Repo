import pandas as pd
import geopandas as gpd 
import requests 
import json
from datetime import datetime
from io import StringIO
import csv
import time
import os
import airqualityandclimateAPI

################### Downloading Data ##################################
#climate data:
climatedatapath = f"/Users/griffinberonio/Documents/AAE 724/Datasets/climatedata/totalclimatedata.csv"
climatedata = pd.read_csv(climatedatapath)

#Air Quality Data:
airqualitydatapath = f'/Users/griffinberonio/Documents/AAE 724/Datasets/master_aqs_df_17_031.csv'
airqualitydata = pd.read_csv(airqualitydatapath)

#Renewable Energy Data: 
renewablespath = '/Users/griffinberonio/Documents/AAE 724/Datasets/RenewableGeneratorsRegisteredinGATS_20260203_110659.csv'
renewablesdata = pd.read_csv(renewablespath, encoding='latin-1')

#Daily Emissions Data:
emissionspath = f'/Users/griffinberonio/Documents/AAE 724/Datasets/IL_Daily_Emissions.csv'
emissiondata = pd.read_csv(emissionspath)

#Daily Energy Demand:
energydemandpath = f'/Users/griffinberonio/Documents/AAE 724/Datasets/Energy_Demand_CHIPJM.csv'
energydemanddata = pd.read_csv(energydemandpath)

#Traffic Data:
trafficdatapath = 




















########################################################################################################
if __name__ == '__main__':
    print('burger')
