import folium
import streamlit as st
from streamlit_folium import folium_static
import pandas as pd
import boto3
import streamlit_analytics

s3_bucket_name = st.secrets["S3_BUCKET_NAME"]
s3_directory = st.secrets["S3_BUCKET_DIRECTORY"]

aws_access_key_id = st.secrets["AWS_ACCESS_KEY_ID"]
aws_secret_access_key = st.secrets["AWS_SECRET_ACCESS_KEY"]


def get_beach_data():
    """
    Retrieve processed beach data from S3
    """
    s3 = boto3.session.Session().client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )

    # List objects in the bucket
    response = s3.list_objects_v2(Bucket=s3_bucket_name, Prefix='clean_data')

    # Find CSV files
    csv_files = [obj['Key'] for obj in response['Contents'] if obj['Key'].lower().endswith('.csv')]

    # # Get the most recent CSV file
    most_recent_csv = max(csv_files, key=lambda obj: s3.head_object(Bucket=s3_bucket_name, Key=obj)['LastModified'])

    clean_data = pd.read_csv('s3://' + s3_bucket_name + '/' + most_recent_csv, sep='|')

    return clean_data


def filter_df_with_input(df):
    """
    Filter dataframe based on user input
    """
    # beach_names = list(gdf["name"].unique())
    beach_names = list(set(df["name"]))

    beach_names.append('All Beaches')

    # Enter user input, where default input is "all beaches"
    options = st.multiselect('Choose a beach:', beach_names, default=beach_names[-1])
    return options


def plot_beach_map():
    df = get_beach_data()
    df["color"] = df["color"].replace({'gray': 'green', 'yellow': 'orange', 'red': 'red'})

    # Provide list of beaches so user has options to choose from
    options = filter_df_with_input(df)
    if 'All Beaches' in options:
        beach_filter = df["name"].tolist()
    else:
        beach_filter = options

    # Filter by user selection
    df = df.query("name.isin(@beach_filter)")

    # Initialize plot of folium map
    m = folium.Map(location=[18.2208, -66.22], zoom_start=9)

    # Specify map markers based on risk level and associated colors (e.g. red=high risk)
    for _, r in df.iterrows():
        lon = r["long"]
        lat = r["lat"]
        folium.Marker(
            location=[lat, lon],
            popup="{}".format(r["name"]),
            icon=folium.Icon(color=r["color"], icon_color=r["color"], icon="empty")
            # popup="{} <br>".format(r["name"]),
        ).add_to(m)

    # Plot the map
    folium_static(m, width=900, height=500)

    return df


def beach_table(beach_selection):

    df = pd.read_csv(s3_directory + '/highres_geocode_beaches.csv')
    # df = df.query("name.isin(@beach_selection)")
    df['beach_town'] = df['town'].combine_first(df['county']).combine_first(df['city'])
    display_columns = ['name', 'google_maps_link', 'risk_level', 'beach_town']
    df = df[display_columns]

    def highlight_df(val):
        """
        Function to apply conditional styling to pandas dataframe
        """
        if 'LOW' in val:
            return 'background-color: green;'
        elif 'MODERATE' in val:
            return 'background-color: orange;'
        elif 'HIGH' in val:
            return 'background-color: red;'

    # Apply the styling function to the DataFrame
    styled_df = df.style.applymap(highlight_df, subset=['risk_level'])

    return styled_df


st.set_page_config(layout="wide", page_title="Puerto Rico Beach Rip Currents")  # Adjust layout based on content

streamlit_analytics.start_tracking()

st.title('Puerto Rico Beach Risk Levels')
st.markdown(
    """
    This is experimental rip current risk data (sourced primarily from the National Weather Prediction Service). 
    Maritime conditions can change quickly, so please always be cautious when going to the beach. For more information on rip current safety, visit https://www.weather.gov/safety/ripcurrent . 
    """
)
streamlit_analytics.stop_tracking()


beach_selection = plot_beach_map()

st.dataframe(
    beach_table(beach_selection),  # provide filtered df
    column_order=("name", "risk_level", "beach_town", "google_maps_link"),
    column_config={
        "name": "Beach Name",
        "beach_town": "Town in Puerto Rico",
        "risk_level": "Risk Level",
        "google_maps_link": st.column_config.LinkColumn("Location Link"),
    },
    hide_index=True, use_container_width=True
)





