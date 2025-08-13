class FinancialAnalystAgent:
    def __init__(self):
        self.name = "financial_analyst_agent"
        self.description = "An agent that analyzes financial data and provides insights."

    def process_data(self, financial_data):
        # Basic example: just print the data
        print(f"Analyzing financial data: {financial_data}")
        # In a real scenario, this would involve complex financial analysis
        return "Financial data processed successfully."

    def recommend_action(self, analysis_result):
        # Basic example: always recommend to invest
        print(f"Based on analysis: {analysis_result}")
        # In a real scenario, this would involve sophisticated recommendation logic
        return "Recommendation: Consider investing in diversified assets."
