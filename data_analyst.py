import io
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from google.adk.agents import Agent
import os

def create_visualization_from_data(data: str, chart_type: str, title: str) -> dict:
    \"\"\"
    Creates a visualization from data and returns the image as bytes.

    Args:
        data (str): The data to visualize, in a CSV string format.
        chart_type (str): The type of chart to create (e.g., 'bar', 'line', 'pie').
        title (str): The title of the chart.

    Returns:
        dict: A dictionary containing the image of the chart as bytes, chart type, and title.
    \"\"\"
    # Use a string IO object to read the CSV data
    data_io = io.StringIO(data)
    df = pd.read_csv(data_io)

    plt.figure(figsize=(10, 6))
    
    if chart_type == 'bar':
        sns.barplot(data=df, x=df.columns[0], y=df.columns[1])
    elif chart_type == 'line':
        sns.lineplot(data=df, x=df.columns[0], y=df.columns[1])
    elif chart_type == 'pie':
        df.set_index(df.columns[0])[df.columns[1]].plot.pie(autopct='%1.1f%%')
        plt.ylabel('') # Hide the y-label for pie charts
    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    plt.title(title)
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save the plot to an in-memory buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    
    # Clear the current figure
    plt.clf()
    
    return {
        "image_bytes": buf.getvalue(),
        "chart_type": chart_type,
        "title": title
    }

def create_data_analyst_agent():
    \"\"\"
    Creates the data analyst agent.
    \"\"\"
    return Agent(
        name=\"data_analyst_agent\",
        description=\"An agent that can create visualizations from data.\",
        model = os.environ[\"MODEL_NAME\"],\
        instruction = \"You are a data analyst agent capable of plotting data\",
        tools=[create_visualization_from_data]
    )