from dotenv import load_dotenv
from langchain_core.tools import tool
from ddgs import DDGS
import os
import requests
import json
from langgraph.prebuilt import ToolNode

load_dotenv()

@tool
def search_tool(query: str) -> str:
    """DuckDuckGoSearchRun module to search any query over web and provide the response back."""
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=5)
        if not results:
            return "No results found."
        return "\n\n".join(
            f"Title: {r['title']}\nURL: {r['href']}\nSummary: {r['body']}"
            for r in results
        )

@tool
def calculator(first_number: float , second_number: float , operator: str) -> float:
    """Perform basic arithmetic operation on two numbers.
    Supported Operations are: add , sub, mul, div
    """
    if operator.lower() == "add":
        result = first_number + second_number
    elif operator.lower() == "sub":
        result = first_number - second_number
    elif operator.lower() == "mul":
        result = first_number * second_number
    elif operator.lower() == "div":
        if second_number == 0:
            return {"error" : "Division by Zero is not allowed."}
        result = first_number / second_number
    else:
        return {"error" : f"Unsupported arithmetic operation {operator}"}
        
    return {"first_number": first_number,"second_number": second_number,"operator": operator,"result" : result}

@tool
def bulk_calculator(values: list[float],operator:str) -> float:
    """Perform basic arithmetic operation on provided values on list.
    Supported Operations are: add , sub, mul, div
    example: values = [1,2,3,4,5] & operator= "add"
    result: 1+2+3+4+5 = 15
    """
    if operator in ["add","sub"]:
        result = 0
    elif operator in ["mul","div"]:
        result = 1
        
    for i in values:
        if operator == "add":
            result += i
        elif operator == "sub":
            result -= i
        elif operator == "mul":
            result *= i
        elif operator == "div":
            if i == 0:
                return {"error" : "Division by Zero is not allowed."}
            result /= i
        else:
            return {"error" : f"Unsupported arithmetic operation {operator}"}
    return {"result" : result}

@tool
def get_global_mkt_stock_price(company_symbol:str) -> float:
   # """Function to retrieve latest stock price for given company symbol from Global US Market"""
    """Retrieve the LATEST stock price (in USD - US Dollars) for a company listed on the
    US Global Market (NYSE/NASDAQ) using its ticker symbol (e.g., 'ORCL' for Oracle,
    'AAPL' for Apple).
    IMPORTANT: The price returned is in USD. If the final valuation currency is INR or EUR(destination currency),
    you MUST call getConversationRatio('USD','INR') to get the exchange rate, then call
    convert() to convert this USD price to INR before using it in calculations.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={company_symbol}&apikey={os.getenv('alphavantage_api')}"
    
    result = requests.get(url).json()
    #print(f"indian mkt price for {company_symbol} is {result}")
    return result 

@tool
def get_indian_mkt_stock_price(company_name:str) -> float:
    """Retrieve the LATEST stock price (in INR - Indian Rupees) for a company listed on
    the Indian National Stock Exchange (NSE/BSE).
    Use the full company name (e.g., 'Infosys', 'TCS', 'Reliance').
    IMPORTANT: The price returned is already in INR. If the final valuation currency is USD or EUR(destination currency),
    you MUST call getConversationRatio('INR','USD') to get the exchange rate, then call
    convert() to convert this USD price to INR before using it in calculations.
    """
    response = requests.get("https://stock.indianapi.in/stock",
    headers={
      "Accept": "application/json",
      "x-api-key": os.getenv('INDIAN_STOCK_API')
    },
    params={
      "name": company_name
    }
    )
    content = json.loads(response.content)

    price = content.get("currentPrice").get('NSE','BSE')
    #print(f"indian mkt price for {company_name} is {price}")
    return price 

@tool
def getConversationRatio(BaseCurrency: str,TargetCurrency: str) -> float:
    #"""Function will fetch only realtime conversation rate between base currency and target currency. Example like from US Dollar to Indian Rupees."""
    """Fetch the REAL-TIME exchange/conversion rate between two currencies.
    Use currency codes: 'USD' for US Dollar, 'INR' for Indian Rupee, 'EUR' for Euro, etc.
    Example: getConversationRatio('USD', 'INR') returns how many INR equal 1 USD.
    MANDATORY: Call this tool whenever a stock price is in a different currency than the
    requested valuation currency. For example, if ORCL price is in USD but valuation is
    asked in INR, call getConversationRatio('USD', 'INR') before converting the price.
    """
    
    url = f"https://v6.exchangerate-api.com/v6/{os.getenv('exchangerate_api')}/pair/{BaseCurrency}/{TargetCurrency}"
    response = requests.get(url).json()
    conversation_rate = response.get("conversion_rate")
    #print(f"Conversation rate between {BaseCurrency} and {TargetCurrency} is {conversation_rate}")
    return conversation_rate

@tool
def convert(base_currency_value: float,conversation_rate: float) -> float:
    #"""Given real time conversation rate , this function will calculate currency value from given base currency value"""
    """Convert a monetary value from one currency to another using a conversion rate.
    Formula: converted_value = base_currency_value * conversion_rate
    Example: convert(150.0, 83.5) converts $150 USD to INR using rate 83.5 = ₹12,525
    Always call getConversationRatio first to get the rate, then pass it here.
    """
    #print("Got a call to convert currancy rate")
    return conversation_rate * base_currency_value

tools = [search_tool,get_global_mkt_stock_price,get_indian_mkt_stock_price,calculator,getConversationRatio,convert,bulk_calculator]

tool_node = ToolNode(tools)