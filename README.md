# 📈 Stock Portfolio Valuation Agent

A LangGraph-powered AI agent that calculates the **real-time total valuation** of a stock portfolio spanning both **Indian (NSE/BSE)** and **US Global (NYSE/NASDAQ)** markets, with automatic multi-currency conversion to any target currency (e.g., INR).

---

## 🧩 Problem Statement

Retail investors often hold stocks across multiple exchanges — Indian (NSE/BSE) and US Global (NYSE/NASDAQ). Calculating the total portfolio value requires:

1. Fetching live prices from **different market APIs** (Indian vs US).
2. **Currency conversion** — US stocks are priced in USD, but an Indian investor wants the total in INR.
3. Computing per-stock valuations and summing them into a single total.

Doing this manually is tedious and error-prone. This project solves it using an **LLM-driven agentic workflow** that autonomously calls the right tools in the right order, performs currency conversion when needed, and returns an accurate total portfolio valuation.

---

## 🏗️ Architecture

```
User Query
    │
    ▼
┌─────────────┐      tool_calls?      ┌──────────────────┐
│   Agent     │ ───── YES ──────────► │  execute_tools   │
│ (GPT-4o +   │                       │  (tool_map loop) │
│  tools)     │ ◄──── results ────────┘                  │
└─────────────┘                                           │
      │                                                   │
   no tool_calls                                          │
      │                                                   │
      ▼                                                   │
┌──────────────┐                                          │
│ set_valuation│ ──────────────────────────────► END      │
└──────────────┘
```

**Graph nodes:**
- `agent` — LLM decides which tools to call next, or produces the final answer
- `execute_tools` — Executes all tool calls from the agent's last message
- `set_valuation` — Extracts and stores the final valuation from the agent's response

**Routing:**
- If the agent's last message contains `tool_calls` → route to `execute_tools`
- Otherwise → route to `set_valuation` → END

---

## 🛠️ Tools

| Tool | Purpose | Returns |
|---|---|---|
| `get_indian_mkt_stock_price` | Fetches live price from Indian NSE/BSE | Price in **INR** |
| `get_global_mkt_stock_price` | Fetches live price from US NYSE/NASDAQ via Alpha Vantage | Price in **USD** |
| `getConversationRatio` | Fetches real-time exchange rate between two currencies | Conversion rate (float) |
| `convert` | Converts a monetary value using a given exchange rate | Converted value (float) |
| `calculator` | Performs arithmetic: `add`, `sub`, `mul`, `div` | Result (float) |
| `bulk_calculator`| Performs arithmetic: `add`, `sub`, `mul`, `div` (expecting values in List) | Result (float) |
| `search_tool` | General web search via DuckDuckGo | Search results (string) |

---

## 🔄 Agent Reasoning Workflow

The agent follows this **mandatory step-by-step reasoning** (enforced via system prompt):

```
1. IDENTIFY   → Parse user query: company names, share quantities, exchange (Indian vs US)
2. FETCH      → get_indian_mkt_stock_price() for NSE/BSE stocks (returns INR)
               → get_global_mkt_stock_price() for NYSE/NASDAQ stocks (returns USD)
3. CONVERT    → getConversationRatio('USD', 'INR') for every US stock
               → convert(usd_price, rate) to get INR price per share
4. CALCULATE  → calculator(quantity, price_in_inr, 'mul') per stock
5. SUM        → calculator(val1, val2, 'add') repeatedly for total
6. REPORT     → Final breakdown: per-stock valuations + total portfolio value
```

---

## 📁 Project Structure

```
portfolio_valuation/
│
├── workflow.py          # LangGraph graph definition, nodes, and agent logic
├── tools.py             # Tool definitions with @tool decorator
├── .env                 # API keys (not committed to git)
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/portfolio-valuation-agent.git
cd portfolio-valuation-agent
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Alpha Vantage (US Global Market)
alphavantage_api=your_alphavantage_api_key

# Indian Stock Exchange API
INDIAN_STOCK_API=your_indian_stock_api_key

# Exchange Rate API
exchangerate_api=your_exchangerate_api_key
```

> **API Sources:**
> - OpenAI: https://platform.openai.com
> - Alpha Vantage (US stocks): https://www.alphavantage.co/support/#api-key
> - Indian Stock API: https://indianapi.in
> - Exchange Rate API: https://www.exchangerate-api.com

---

## ▶️ Usage

```bash
python workflow.py
```

**Example query (editable in `workflow.py`):**

```python
initial_state = {
    "message": HumanMessage(
        content=(
            "From India's Exchange I have 100 Infosys shares & 50 TCS shares, "
            "and from US Global market I have 10 ORACLE shares. "
            "What is the current total portfolio valuation in INR (Indian Rupee)?"
        )
    )
}
```

**Example output:**

<img width="757" height="607" alt="image" src="https://github.com/user-attachments/assets/595c83c6-6b3e-40b8-91a2-7233eafd3a2d" />

---

## 📦 Dependencies

```
langgraph
langchain
langchain-openai
langchain-core
python-dotenv
requests
duckduckgo-search
```

Full list in `requirements.txt`.

---

## 🔑 Key Design Decisions

- **System Prompt as Guardrail** — A detailed `SystemMessage` enforces the correct tool-calling sequence. Without it, the LLM skips currency conversion for US stocks.
- **GPT-4o** — Selected over GPT-3.5-turbo for reliable multi-step tool chaining.
- **Custom `execute_tools` node** — Instead of `ToolNode` from `langgraph.prebuilt`, a custom executor is used for full visibility and control over tool call logging.
- **`add_messages` reducer** — Ensures the message list accumulates correctly across agent↔tool cycles without overwriting state.

---

## ⚠️ Limitations

- Alpha Vantage free tier has **25 API calls/day** — for production use, upgrade to a paid plan.
- Indian Stock API availability may vary; ensure your key is active.
- The agent relies on LLM reasoning to pick the right tools — GPT-4o is strongly recommended over GPT-3.5.

---
