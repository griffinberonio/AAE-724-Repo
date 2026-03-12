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
    totaldf['DATE'] = pd.to_datetime(totaldf['DATE'])
    totaldf['DailyPrecipitation'] = totaldf['DailyPrecipitation'].replace('T',0)
    totaldf['DailyPrecipitation'] = totaldf['DailyPrecipitation'].astype(float)
    totaldf['YEAR'] = totaldf['DATE'].dt.year

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
    # df['YEAR'] = df['DATE'].dt.year
    totalcols = x + y + fe
    df = df[totalcols]

    # Convert all predictors and Y to numeric
    for col in x + y:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Drop rows with any missing values
    model_df = df.dropna()

    # Set MultiIndex
    df_panel = df.set_index(['CLIMATE_STATION_NAME', 'YEAR'])

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


def model_2_aqi(data, x, y, fe):

    df = data
    df['DATE'] = pd.to_datetime(df['DATE'])
    df['YEAR'] = df['DATE'].dt.year
    totalcols = x + y + fe
    df = df[totalcols]

    # Convert all predictors and Y to numeric
    for col in x + y:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Drop rows with any missing values
    model_df = df.dropna()
    print(model_df.head())
    # Set MultiIndex
    df_panel = model_df.set_index(fe)

    # Define X and Y
    Y = df_panel[y[0]]  # assuming y = ['aqi']
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


# Model 3: Regressing Energy demand on climate variables: 
# Rexamine which variables are included, add a few more 
# Include Seasonal column (4 categories, broken up by season based on month)
def model_3_energy_climate(data, x, y, fe):
    df = data
    df['DATE'] = pd.to_datetime(df['DATE'])
    df['MONTH'] = df['DATE'].dt.month
    df['YEAR'] = df['DATE'].dt.year
    # df['MONTH'] = df['MONTH'].astype('category')
    # seasons = {
    #     '12':'1','1':'1','2':'1',  #winter
    #      '3':'2','4':'2','5':'1',  #Spring
    #      '6':'3','7':'3','8':'3',  #Summer
    #      '9':'4','10':'4','11':'4' #Fall
    # }
    # df['month'] = df['MONTH'].astype(str)
    # df['SEASON'] = df['month'].map(seasons)
    # df['SEASON'] = df['SEASON'].astype('category')
    # df = df.drop(columns='month')
    # x.append('SEASON')

    totalcols = x+y+fe

    for col in x + y:
        df[col] = pd.to_numeric(df[col],errors='coerce')

    df = df[totalcols]
    model_df = df.dropna()

    # print(model_df.head())

    df_panel = model_df.set_index(fe)

    Y = df_panel[y[0]] 
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


    


    

# Model 4: Fossil fuel generation output (MWh) based on above metrics ^
# Model 5: Regressing Pm2.5/ aqi on renewables, controlling. for climate metrics 
#Model 6-7: adding all the things together. 

########################################################################################################
if __name__ == '__main__':

    total = totaldata()

    dependent_vars = ['arithmetic_mean','first_max_value']
    # cleaning_total_data(totaldf,dependent_vars)

    # Variables:
    xclimate = ['DailyAverageDryBulbTemperature', 'DailyAverageWindSpeed','DailyMaximumDryBulbTemperature',
       'DailyMinimumDryBulbTemperature', 'DailyPeakWindSpeed',
       'DailyPrecipitation','DailySustainedWindSpeed', 'DailySustainedWindDirection_sin', 'DailySustainedWindDirection_cos',
       'DailyAveragePrecipitation', 'DailyAveragePressureChange',
       'DailyAverageRelativeHumidity',]

    y = ['arithmetic_mean']
    yaqi = ['aqi']

    fe = ['CLIMATE_STATION_NAME','YEAR']

    xenergy= ['DailyAverageDryBulbTemperature', 'DailyAverageWindSpeed',
        'DailyDepartureFromNormalAverageTemperature',
        'DailyMaximumDryBulbTemperature',
       'DailyMinimumDryBulbTemperature', 'DailyPeakWindSpeed',
       'DailyPrecipitation',
       'DailySustainedWindSpeed',
       'DailyPeakWindDirection_sin', 'DailyPeakWindDirection_cos',
       'DailySustainedWindDirection_sin', 'DailySustainedWindDirection_cos',
       'DailyAverageDewPointTemperature',
       'DailyAveragePrecipitation', 'DailyAveragePressureChange',
       'DailyAverageRelativeHumidity', 'DailyAverageSeaLevelPressure',
       'DailyAverageStationPressure', 'DailyAverageWetBulbTemperature',
       'DailyAverageWindGustSpeed', 'DailyAverageWindDirection_sin',
       'DailyAverageWindDirection_cos']
    
    yenergy = ['Demand']
    feenergy = ['CLIMATE_STATION_NAME','MONTH']

    # model_1(totaldf, xclimate, y, fe)
    model_1_panel(total, xenergy, y, fe)

    # model_2_aqi(totaldata(), xclimate, yaqi, fe)

    

    #Energy Demand: 
    # model_3_energy_climate(total, xenergy, yenergy, feenergy)

    #Fossil Fuel Dispatch Output Generation: 
    yfossil = ['Gross Load (MWh)']

    # model_3_energy_climate(total,xenergy,yfossil, feenergy)

    #PM mean on renewables and capacity controlling for climate with year and station FE:
    xenergyandrenewables = xenergy + ['Number', 'Capacity']
    
    # model_3_energy_climate(total, xenergyandrenewables, y,fe)

    # AQI on renewables and capacity controlling for climate with year and station FE:
    # model_3_energy_climate(total,xenergyandrenewables,yaqi,fe)




   
