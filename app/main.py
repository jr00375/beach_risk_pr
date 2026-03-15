import folium
import streamlit as st
from streamlit_folium import folium_static
import pandas as pd
import boto3
import streamlit_analytics
s3_bucket_name = st.secrets["S3_BUCKET_NAME"]
s3_directory = st.secrets["S3_BUCKET_DIRECTORY"]


def s3_uri(key: str) -> str:
    return s3_directory.rstrip('/') + '/' + key.lstrip('/')

aws_access_key_id = st.secrets["AWS_ACCESS_KEY_ID"]
aws_secret_access_key = st.secrets["AWS_SECRET_ACCESS_KEY"]


@st.cache_data(ttl=3600)
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

    # Find the most recent CSV file (LastModified is already in the listing)
    csv_objects = [obj for obj in response['Contents'] if obj['Key'].lower().endswith('.csv')]
    most_recent_csv = max(csv_objects, key=lambda obj: obj['LastModified'])['Key']

    clean_data = pd.read_csv(s3_uri(most_recent_csv), sep='|')

    return clean_data


@st.cache_data(ttl=3600)
def get_geocode_data():
    return pd.read_csv(s3_uri('clean_data/highres_geocode_beaches.csv'))


def filter_df_with_input(df):
    """
    Filter dataframe based on user input
    """
    beach_names = list(set(df["name"]))
    beach_names.append('All Beaches')

    # Enter user input, where default input is "all beaches"
    options = st.multiselect('Choose a beach:', beach_names, default=beach_names[-1])
    return options


def plot_beach_map():
    df = get_beach_data()
    df["color"] = df["color"].replace({'gray': 'green', 'yellow': 'orange', 'red': 'red'})

    # Show last updated timestamp
    last_updated = pd.to_datetime(df["date_time"]).max()
    st.caption(f"Last updated: {last_updated.strftime('%B %d, %Y %I:%M %p')}")

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
        ).add_to(m)

    # Plot the map
    folium_static(m, width=900, height=500)

    return df


def beach_table(beach_selection):
    df = get_geocode_data()
    df = df.query("name.isin(@beach_selection['name'].tolist())")
    df['beach_town'] = df['town'].combine_first(df['county']).combine_first(df['city'])
    display_columns = ['name', 'google_maps_link', 'risk_level', 'beach_town']
    df = df[display_columns]

    def highlight_df(val):
        if val and 'LOW' in val:
            return 'background-color: green;'
        elif val and 'MODERATE' in val:
            return 'background-color: orange;'
        elif val and 'HIGH' in val:
            return 'background-color: red;'

    styled_df = df.style.applymap(highlight_df, subset=['risk_level'])

    return styled_df


st.set_page_config(layout="wide", page_title="Puerto Rico Beach Rip Currents")

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
    beach_table(beach_selection),
    column_order=("name", "risk_level", "beach_town", "google_maps_link"),
    column_config={
        "name": "Beach Name",
        "beach_town": "Town in Puerto Rico",
        "risk_level": "Risk Level",
        "google_maps_link": st.column_config.LinkColumn("Location Link"),
    },
    hide_index=True, use_container_width=True
)
