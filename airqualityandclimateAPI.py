
import pandas as pd
import geopandas as gpd 
import requests 
import json
from datetime import datetime
from io import StringIO
import csv




## Climate Data Request from NCEI API: 
def temprequest(fip, param):
    # Define parameters for the API request
    scope = 'county'
    parameter = param  # Average Temperature
    timescale = 'ytd'
    month = 0  # all months
    begYear = 2016
    endYear = 2024
    data_format = 'csv'


    # Initialize an empty list to store data for all counties
    all_county_data = []

    # Loop through each county FIPS code and make the API request
    # for fips in wi_county_fips:
    # url = f"https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/{scope}/time-series/{fip}/{parameter}/{timescale}/{month}/{begYear}-{endYear}/data.{data_format}"
    url = f"https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/{scope}/time-series/{fip}/{parameter}/{timescale}/{month}/{begYear}-{endYear}/data.{data_format}"
    response = requests.get(url)

    if response.status_code == 200:
        # Read the CSV data into a DataFrame
        csv_data = StringIO(response.text)
        county_data = pd.read_csv(csv_data)
        county_data['FIPS'] = fip  # Add a column for the FIPS code
        # all_county_data.append(csv_reader)
        all_county_data.append(county_data)
        all_county_data = pd.DataFrame(all_county_data[0])
        all_county_data.columns = ['Date', param, 'FIPS']
        all_county_data.drop(index=0, inplace=True)
        all_county_data.drop(index=1, inplace= True)

        # Dates:
        all_county_data['Date'] = pd.to_datetime(all_county_data['Date'], format='%Y%m')
        all_county_data['Year'] = all_county_data['Date'].dt.year

        # Grouping and averaging yearly temps:
        all_county_data[param] = [float(i) for i in all_county_data[param] ]

        annualavgtemp = all_county_data.groupby(['Year', 'FIPS'])[param].mean().reset_index()

        # Changing county codes to names:
        dictmap = {"FIP":"countyname"}

        annualavgtemp['County'] = annualavgtemp['FIPS'].map(dictmap)
        annualavgtemp.drop(columns=['FIPS'], inplace=True)
        response = annualavgtemp
    else:
        response = f"Failed to retrieve data for {fip}: {response.status_code}"
        

    
    print('climate API passed')
    print(response)
    return response

def totaltemps(fips, param, filename):
    total_df = None
    for fip in fips:
        tempdf = temprequest(fip, param)
        if total_df is None:
            total_df = tempdf
        else:
            total_df = pd.concat([total_df, tempdf], ignore_index=True)

    filepath = f"C:/Users/griff/OneDrive/AAE636/{filename}.csv"
    return total_df, total_df.to_csv(filepath)


########### AIR QUALITY API REQUEST #############

def airquality(statecode, county, PMcodes = False):
    # https://aqs.epa.gov/data/api/list/countiesByState?email=test@aqs.api&key=test&state=37
    email = 'griffinberonio@gmail.com'
    key = 'bluefrog75'

    PMurl = f"https://aqs.epa.gov/data/api/list/parametersByClass?email={email}&key={key}&pc=SPECIATION"
    url = f"https://aqs.epa.gov/data/api/list/sitesByCounty?email={email}&key={key}&state={statecode}&county={county}"
    testurl = f"https://aqs.epa.gov/data/api/dailyData/byCounty?email={email}&key={key}&param=88101&bdate=20170618&edate=20170618&state={statecode}&county={county}"
    #Above test url finds FRM PM 2.5 daily summary data from between 06/01/2017 and 06/18/2017
    if PMcodes == True:
        response = requests.get(PMurl)
        if response.status_code == 200:
            output = json.loads(response.text)
            outputheader = output['Header']
            PMcodeddf = pd.DataFrame.from_dict(output['Data'], orient='columns')
            return PMcodeddf
    
        else:
            print(f"Error: {response.status_code}")
            
    else:
        response = requests.get(testurl)
        if response.status_code == 200:
            output = json.loads(response.text)
            outputheader = output['Header']
            outputdata = pd.DataFrame.from_dict(output['Data'], orient='columns')
            return outputdata
        else:
            print(f"Error: {response.status_code}")

###################################################################################


if __name__ == '__main__':

    #Parameters for climate data requests:
    chicagofip = 'IL-031'
    test_fips = ["WI-001","WI-003", "WI-005"]
    # chidf = temprequest(chicagofip, 'tavg')

    #Parameters for air quality requests:
        #Structure: Service, filter, endpoint, email, key, param, begindate, enddate, state, county
        #services: 'list','monitors', sampleData, dailyData, annualData
        #filters: bySite, byCounty
        #endpoint: would be like dailyData/byCounty?email&key
        #parameter classes can be found with lis/classes?

    #PM 2.5 parameter codes in a dict: 
    pmdict = {}

    filter = 'byCounty'
    illinoiscode = '17'
    cookcode = '031'
    extra = 'none'

    airdf = print(airquality(illinoiscode, cookcode))
    siteaddresses = print(airdf['site_address'].unique())
    


    # df = totaltemps(wi_county_fips, "tmax", "tmaxdata")
    # print(df.head(10))




