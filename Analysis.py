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
import statsmodels.api as sm

from statsmodels.stats.outliers_influence \
     import variance_inflation_factor as VIF
from statsmodels.stats.anova import anova_lm

from ISLP import load_data
from ISLP.models import (ModelSpec as MS,
                         summarize,
                         poly)
from linearmodels.panel import PanelOLS

################### Downloading Data ##################################
#climate data:
climatedatapath = f"/Users/griffinberonio/Documents/AAE 724/Datasets/climatedata/totalclimatedata.csv"
climatedata = pd.read_csv(climatedatapath)

#Air Quality Data:
airqualitydatapath = f'/Users/griffinberonio/Documents/AAE 724/Datasets/master_aqs_df_17_031.csv'
airqualitydata = pd.read_csv(airqualitydatapath)

#Renewable Energy Data: 
renewablespath = '/Users/griffinberonio/Documents/AAE 724/Datasets/CookCountyRenewablesData.csv'
renewablesdata = pd.read_csv(renewablespath, encoding='latin-1')

#Daily Emissions Data:
emissionspath = f'/Users/griffinberonio/Documents/AAE 724/Datasets/IL_Daily_Emissions.csv'
emissiondata = pd.read_csv(emissionspath)

#Daily Energy Demand:
energydemandpath = f'/Users/griffinberonio/Documents/AAE 724/Datasets/Energy_Demand_CHIPJM.csv'
energydemanddata = pd.read_csv(energydemandpath)

#Traffic Data:
trafficdatapath = '/Users/griffinberonio/Documents/AAE 724/Datasets/DailyTrafficData_Chicago.csv'

#Total Data From Notebook:
totaldatapath = '/Users/griffinberonio/Documents/AAE 724/Datasets/totaldata.csv'
totaldf = pd.read_csv(totaldatapath)

def totaldata():

    totaldatapath = '/Users/griffinberonio/Documents/AAE 724/Datasets/totaldata.csv'
    totaldf = pd.read_csv(totaldatapath)


    return totaldf

def cleaning_total_data(df,variables):
    dependent_vars = ['aqi','arithmetic_mean','first_max_value']
    needed_vars = variables 

    num_missing = {}
    for col in variables:
        num_missing[col] = df[col].isna().sum()

    # print(df.shape)
    print(num_missing)
    tempdf = df.dropna(subset=variables)
    print(tempdf.head())

    return tempdf

# come back to this:
class totaldataclass:
    def __init__(self, matrixname, columns=[]):
        data = totaldf
        self.name = matrixname
        self.matrix = data[columns]

#Model 1:
# Model1: Regressing PM 2.5 on a matrix of climate variables alone:

def model_1(data, x, y, fe):
    df = data
    xmatrix = x
    totalcols = xmatrix + y + fe
    # print(totalcols)

    df = df[totalcols]
    df['DATE'] = pd.to_datetime(df['DATE'])
    clusters = df['CLIMATE_STATION_NAME']

    # df['YEAR'] = df['DATE'].dt.year.astype(str)
    df['YEAR'] = pd.to_numeric(df['DATE'].dt.year)

    df = df.dropna(subset=totalcols)

    # df_with_dummies = pd.get_dummies(
    #     df, 
    #     columns=['CLIMATE_STATION_NAME','YEAR'], 
    #     drop_first=True
    # )
    df_with_dummies = pd.get_dummies(
        df,
        columns=['CLIMATE_STATION_NAME','YEAR'],
        drop_first=True
        )
    
    cols = df_with_dummies.columns

    for col in cols:
        if col != 'CLIMATE_STATION_NAME_CHICAGO PALWAUKEE AIRPORT, IL US':
            df_with_dummies[col] = pd.to_numeric(df_with_dummies[col], errors='coerce')
    df_with_dummies = df_with_dummies.dropna()

    Y = df_with_dummies['arithmetic_mean'] 
    X = df_with_dummies.drop(columns=['arithmetic_mean','DATE'])
    
    X_final = sm.add_constant(X)

    
    ols_model = sm.OLS(Y, X_final.astype(float))

    results = ols_model.fit(cov_type='cluster', cov_kwds={'groups': clusters.loc[df_with_dummies.index]})
    summary = summarize(results)
    summary2 = pd.DataFrame(summary).reset_index()

    print(summary2)

    return summary2
    

#Panel Two Way Fixed Effects Model with Date and Station-based fixed effects: 


def model_1_panel(df, x, y, fe):
    df['DATE'] = pd.to_datetime(df['DATE'])
    totalcols = x + y + fe
    df = df[totalcols]

    # Convert all predictors and Y to numeric
    for col in x + y:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Drop rows with any missing values
    model_df = df.dropna()

    # Set MultiIndex
    df_panel = df.set_index(['CLIMATE_STATION_NAME', 'DATE'])

    # Define X and Y
    Y = df_panel[y[0]]  # assuming y = ['arithmetic_mean']
    X = df_panel[x]

    # Fit the model
    model = PanelOLS(
        Y,
        X,
        entity_effects=True,
        time_effects=True
    )

    results = model.fit(cov_type='clustered', cluster_entity=True)
    print(results)
    return results


def model_2(data, fe):






########################################################################################################
if __name__ == '__main__':
    dependent_vars = ['arithmetic_mean','first_max_value']
    # cleaning_total_data(totaldf,dependent_vars)

    # Model 1:
    xclimate = ['DailyAverageDryBulbTemperature', 'DailyAverageWindSpeed','DailyMaximumDryBulbTemperature',
       'DailyMinimumDryBulbTemperature', 'DailyPeakWindSpeed',
       'DailyPrecipitation','DailySustainedWindSpeed', 'DailySustainedWindDirection_sin', 'DailySustainedWindDirection_cos',
       'DailyAveragePrecipitation', 'DailyAveragePressureChange',
       'DailyAverageRelativeHumidity',]

    y = ['arithmetic_mean']

    fe = ['DATE','CLIMATE_STATION_NAME']

    # model_1(totaldf, xclimate, y, fe)
    # model_1_panel(totaldf, xclimate,y,fe)

   
