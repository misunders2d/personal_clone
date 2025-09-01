from google.adk.tools.mcp_tool import MCPToolset, SseConnectionParams
from google.adk.agents import Agent
import os

COINGECKO_MCP_HOST = "https://mcp.api.coingecko.com/sse"

MODEL_NAME = os.environ["MODEL_NAME"]


def create_financial_analyst_agent(name="financial_analyst_agent"):
    """
    Creates an ADK Agent capable of providing cryptocurrency buy/sell recommendations
    for Ton, Ethereum, and Bitcoin using the CoinGecko MCP Server.
    """
    coingecko_toolset = MCPToolset(
        connection_params=SseConnectionParams(url=COINGECKO_MCP_HOST)
    )

    financial_analyst_agent = Agent(
        name=name,
        description="Provides cryptocurrency buy/sell recommendations for Ton, Ethereum, and Bitcoin.",
        instruction="""
        You are a Financial Analyst Agent. Your primary role is to provide cryptocurrency buy, sell, or hold
        recommendations for Ton, Ethereum, and Bitcoin.

        To formulate your recommendations:
        1. Use the CoinGecko tools to fetch the *current price* of Ton, Ethereum, and Bitcoin.
        2. Use the CoinGecko tools to fetch *historical price data* (e.g., last 24 hours, 7 days) for these cryptocurrencies
           to identify recent trends.
        3. Based on the current price and recent trends:
           - If a cryptocurrency's price has shown a significant upward trend (e.g., >5% increase in 24 hours),
             recommend 'Hold' or 'Consider Selling' if it's already high.
           - If a cryptocurrency's price has shown a significant downward trend (e.g., >5% decrease in 24 hours),
             recommend 'Consider Buying' or 'Hold'.
           - If the price is relatively stable, recommend 'Monitor'.
           - Always clearly state the current price as part of your recommendation.
        4. If a user asks for a cryptocurrency not explicitly mentioned (Ton, Ethereum, Bitcoin),
           kindly inform them that your analysis is limited to these three, but you can still fetch their current price.
        5. Provide clear, concise, and actionable recommendations.
        6. Handle cases where data for a specific cryptocurrency might be temporarily unavailable gracefully by
           stating the limitation.
        """,
        model=MODEL_NAME,
        tools=[
            coingecko_toolset,
        ],
    )
    return financial_analyst_agent
