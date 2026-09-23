
# AIRWISE – India Air Quality Intelligence Dashboard

## Project Overview

This project, "AIRWISE – India Air Quality Intelligence Dashboard," is a professional Streamlit application designed to provide comprehensive insights into air quality across various states and cities in India. Utilizing an uploaded CSV dataset, the dashboard offers interactive visualizations and data-driven insights to help understand pollutant levels, geographical distributions, and temporal trends.

## Features

The dashboard is structured into several interactive sections:

1.  **National Overview:** Key Performance Indicators (KPIs) and an overall analysis of air quality, showing average pollutant levels, and highlighting states/cities with extreme conditions.
2.  **India Map:** An interactive geographical map displaying pollutant levels across India, with filters for states, cities, and specific pollutants.
3.  **Pollutant Analysis:** Charts for comparing different pollutants, allowing users to examine their concentrations across various states and cities.
4.  **State & City Comparison:** Detailed rankings and comparisons of air quality metrics between different states and cities, identifying top/bottom performers.
5.  **AI/Data-Driven Insights:** Automatically generated textual insights summarizing key findings and trends from the displayed data, providing quick actionable information.

## Dataset

The project uses the `Air quality in india.csv` dataset, which contains information on:

*   `country`, `state`, `city`, `station`
*   `last_update`: Timestamp of the data entry
*   `latitude`, `longitude`: Geographical coordinates of the station
*   `pollutant_id`: Type of pollutant (e.g., PM2.5, NO2, SO2)
*   `pollutant_min`, `pollutant_max`, `pollutant_avg`: Minimum, maximum, and average pollutant levels

## Technologies Used

*   **Python:** The core programming language.
*   **Streamlit:** For building the interactive web application.
*   **Pandas:** For data manipulation and analysis.
*   **NumPy:** For numerical operations.
*   **Plotly Express:** For creating interactive and visually appealing charts and maps.

## How to Run the Project

To run this Streamlit application locally, follow these steps:

1.  **Save the files:** Ensure you have `app.py`, `requirements.txt`, and the `Air quality in india.csv` dataset in the same directory.
2.  **Install dependencies:** Open your terminal or command prompt, navigate to the project directory, and install the required Python packages using pip:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the Streamlit app:** Execute the following command in your terminal:
    ```bash
    streamlit run app.py
    ```
4.  **Access the dashboard:** Streamlit will launch the application in your default web browser. If it doesn't open automatically, it will provide a local URL (usually `http://localhost:8501`) that you can copy and paste into your browser.

Enjoy exploring the India Air Quality Intelligence Dashboard!
