from dotenv import load_dotenv
load_dotenv()

import etl_operations as etl

# Extract and clean data from national predictive weather services; assign rip current risk level to beaches in PR
clean_data = etl.assign_beach_risk_level()

# Load transformed data to S3
etl.save_to_s3(clean_data)