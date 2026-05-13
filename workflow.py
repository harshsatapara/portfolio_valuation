from typing import TypedDict,Annotated
from langgraph.graph import StateGraph,START,END
from tools import tools
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage,HumanMessage,SystemMessage
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
import os
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from pathlib import Path

llm = ChatOpenAI(model='gpt-4o')
llm_with_tools = llm.bind_tools(tools)
tool_map = {tool.name:tool for tool in tools }
load_dotenv()
#print(os.getenv("INDIAN_STOCK_API"))


SYSTEM_PROMPT = SystemMessage(content="""
You are a stock portfolio valuation assistant. 
Your job is to calculate the TOTAL portfolio valuation in the currency requested by the user.
 
Follow these steps STRICTLY and IN ORDER using the available tools:
 
STEP 1 — IDENTIFY STOCKS & EXCHANGES
  - Parse the user message and identify each company, the number of shares, and which 
    exchange it belongs to (Indian market: NSE/BSE  OR  US Global market: NYSE/NASDAQ).
 
STEP 2 — FETCH STOCK PRICES
  - For each INDIAN market stock: call get_indian_mkt_stock_price(company_name).
    The returned price is in INR. No conversion needed for INR valuation.
  - For each US GLOBAL market stock: call get_global_mkt_stock_price(company_symbol).
    The returned price is in USD. You MUST convert it to INR if valuation is in INR.
 
STEP 3 — CURRENCY CONVERSION (MANDATORY for USD→INR)
  - For every US stock whose price is in USD and the target valuation currency is INR:
      a. Call getConversationRatio('USD', 'INR') to get the live exchange rate.
      b. Call convert(usd_price, conversion_rate) to get the INR price of one share.
  - Do NOT skip this step. Do NOT assume any fixed exchange rate.
 
STEP 4 — CALCULATE PER-STOCK VALUATION
  - For each stock, call calculator(quantity, price_in_target_currency, 'mul').
    This gives: stock_valuation = quantity * price_per_share (in target currency).
 
STEP 5 — SUM ALL STOCK VALUATIONS
  - Add up all individual stock valuations using bulk_calculator(values, 'add').
 
STEP 6 — REPORT
  - Present the final total portfolio valuation clearly with:
      • Each stock: name, quantity, price per share (in target currency), stock valuation
      • Total portfolio valuation in the requested currency
      
RULES:
  - Never guess or assume a stock price or exchange rate. Always fetch via tools.
  - Never skip currency conversion for USD-priced stocks when INR is requested.
  - Always complete ALL steps before giving the final answer.
""")

class StockState(TypedDict):
    messages: Annotated[list[str],add_messages]
    portfolio_data: dict
    total_valuation: float
    
def valuation_agent(state: StockState):
    """Agent node: decides which tool to call next or produces the final answer."""
    messages = state.get("messages")
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SYSTEM_PROMPT] + list(messages)
        
    response = llm_with_tools.invoke(messages)
    #print(f"\n[agent] response: {response}\n")
    return {"messages": [response]}

#print(valuation_agent())
def execute_tools(state:StockState):
    """Tool-execution node: runs every tool call in the last agent message."""
    last_message = state.get("messages")[-1]
    results=[]
    if hasattr(last_message,"tool_calls") and last_message.tool_calls:
        for tool in last_message.tool_calls:
            tool_func = tool_map[tool["name"]]
            tool_args = tool["args"]
            tool_id = tool["id"]
            #print(f"[tool] calling {tool['name']} with args={tool_args}")
            tool_output = tool_func.invoke(tool_args)
            #print(f"[tool] {tool['name']} result: {tool_output}")
            results.append(ToolMessage(content=tool_output,tool_call_id = tool_id))
            
        return {"messages": results}
    else:
        return {}
            
    
def set_valuation(state: StockState):
    """Final node after all the tool call completes and final valuation receieved"""
    last_message = state.get("messages")[-1]
    
    if last_message.content:
        return {"total_valuation" : last_message.content}
    else:
        return {}
    
def condition_check(state: StockState):
    last_messages = state.get("messages")[-1]
    
    if hasattr(last_messages,"tool_calls") and last_messages.tool_calls:
        return "tools"
    else:
        return "set_valuation"
    
graph = StateGraph(StockState)


graph.add_node("agent",valuation_agent)
graph.add_node("execute_tools",execute_tools)
graph.add_node("set_valuation",set_valuation)

graph.add_edge(START,"agent")
#graph.set_entry_point("agent")
graph.add_conditional_edges("agent",condition_check,{"tools":"execute_tools","set_valuation":"set_valuation"})
graph.add_edge("execute_tools","agent")
graph.add_edge("set_valuation",END)

DB_PATH = Path(__file__).resolve().parent / "chatbot.db"

conn = sqlite3.connect(DB_PATH,check_same_thread=False) #,database='chatbot.db'

checkpointer = SqliteSaver(conn=conn)

workflow = graph.compile(checkpointer=checkpointer)

def retrieve_threads():
    threads = set()
    for checkpoint in checkpointer.list(None):
        threads.add(checkpoint.config["configurable"].get("thread_id"))
    return list(threads)


# if __name__ == "__main__":
#     initial_state = {"message": HumanMessage(content="From India's Exhance I have 100 infosys share & 50 TCS share and from US Global market I have 10 ORACLE shares. What is current valuation as in US Dollar")}
#     #initial_state = {"message": HumanMessage(content="What is the capital of India?")}

#     final_state = workflow.invoke(initial_state)
#     print("\n" + "="*60)
#     print("FINAL PORTFOLIO VALUATION")
#     print("="*60)
#     print(final_state.get("total_valuation"))
#     # for event in workflow.stream(initial_state):
#     #     #print('event',event)
#     #     for key,value in event.items():
#     #         print(f"Node {key} executed")
            