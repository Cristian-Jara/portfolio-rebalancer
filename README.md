# Portfolio Rebalancer

A lightweight, zero-runtime-dependency portfolio management and rebalancing engine built in Python. Given a collection of current stock holdings, live market prices, and target allocation weights (e.g., 40% `META`, 60% `AAPL`), the module computes deterministic `BUY`, `SELL`, and `HOLD` directives to bring the portfolio back into balance.

## AI Usage Disclosure
An LLM was used as a collaborative assistant throughout this project—including financial formula validation, architectural design, Python implementation, unit test generation and documentation. The full conversation log is available in [`docs/llm-conversations.md`](docs/llm-conversations.md).


---

## Project Structure

```text
portfolio-rebalancer/
├── src/
│   ├── exceptions.py     # Domain exception hierarchy & centralized error templates
│   ├── order.py          # TradeAction enum & immutable RebalanceOrder model
│   ├── portfolio.py      # Portfolio valuation, weight tracking & rebalancing engine
│   ├── stock.py          # Stock entity encapsulating stock_id and current_price()
│   └── validation.py     # Finite Decimal coercion & numeric input guards
├── test/
│   ├── test_exceptions.py
│   ├── test_order.py
│   ├── test_portfolio.py
│   ├── test_stock.py
│   └── test_validation.py
├── pyproject.toml        # Project metadata & Ruff linter/formatter configuration
└── README.md
```

---

## Environment Setup (`pyproject.toml` & Ruff)

### Prerequisites
* **Python 3.11+** (required for `enum.StrEnum` and `X | Y` union type syntax)
* **Ruff** (for linting, import sorting, and code formatting)

### 1. Create and Activate a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows (PowerShell)
```

### 2. Install Development Tools

```bash
pip install --upgrade pip
pip install -e ".[dev]"
```

*(Alternatively, if you do not want an editable package install, run `pip install ruff` directly.)*

---

## Usage Example

```python
from decimal import Decimal

from src.portfolio import Portfolio
from src.stock import Stock

# 1. Initialize tradable stocks with their latest market prices
meta = Stock("META", "500.00")
aapl = Stock("AAPL", "200.00")

# 2. Build the portfolio with current holdings ($5,000 META + $5,000 AAPL = $10,000)
portfolio = Portfolio()
portfolio.add_holding(meta, 10)
portfolio.add_holding(aapl, 25)

# 3. Set target allocation policy (40% META, 60% AAPL)
portfolio.set_target_allocations(
    {
        meta: Decimal("0.40"),
        aapl: Decimal("0.60"),
    }
)

# 4. Compute rebalance directives (non-mutating)
for order in portfolio.rebalance():
    print(
        f"{order.stock_id}: {order.action.value} {order.shares} shares "
        f"(${order.amount:.2f}) | weight {order.current_weight:.0%} -> {order.target_weight:.0%}"
    )
```

**Output:**
```text
AAPL: BUY 5 shares ($1000.00) | weight 50% -> 60%
META: SELL 2 shares ($1000.00) | weight 50% -> 40%
```

---

## Testing & Code Quality

### Run the Unit Test Suite

The test suite uses Python's built-in `unittest` framework with zero third-party test dependencies:

```bash
# Run all tests
python3 -m unittest

# Run with verbose output
python3 -m unittest discover -s test -v
```

### Lint and Format with Ruff

```bash
# Check lint rules and formatting (CI mode)
ruff check . && ruff format --check .

# Auto-fix lint issues, sort imports, and format code
ruff check --fix . && ruff format .
```

---

## Architecture & Design Decisions

1. **Exact Base-10 Arithmetic (`decimal.Decimal`):** Binary floating-point types introduce sub-cent rounding drift. Every price, share count, and weight is coerced through `to_decimal()` (rejecting booleans, `NaN`, and `Infinity`) so self-financing conservation of value holds strictly.
2. **Separation of Concerns:**
   * `Stock` represents an asset's identity (`stock_id`) and latest market quote (`current_price()`), independent of any portfolio.
   * `Portfolio` isolates current holdings (`_holdings`) from target weights (`_allocations`).
   * `rebalance()` returns immutable `RebalanceOrder` directives without mutating internal holdings, decoupling calculation from broker execution.
3. **Set-Union Universe ($\mathcal{H} \cup \mathcal{T}$):** Rebalancing iterates over the union of held stocks ($\mathcal{H}$) and target-allocated stocks ($\mathcal{T}$), guaranteeing that orphan holdings ($w_i^* = 0$) generate full `SELL` orders and unheld targets ($N_i = 0$) generate initial `BUY` orders.
4. **Algorithmic Complexity:** For $n$ unique stocks in $\mathcal{H} \cup \mathcal{T}$, valuation and order generation run in $\mathcal{O}(n)$ time and $\mathcal{O}(n)$ space.

---

## Mathematical Model & References

For each stock $i$ in the portfolio universe $\mathcal{U} = \mathcal{H} \cup \mathcal{T}$, given held shares $N_i \ge 0$, current price $P_i > 0$, and target weight $w_i^* \in [0, 1]$ where $\sum w_i^* = 1$:

| Step | Formula | Description |
| :--- | :--- | :--- |
| **Position & Total Value** | $V_i = N_i \cdot P_i, \quad V_{\text{total}} = \sum_{i} V_i$ | Current market valuation of each holding and the total portfolio. |
| **Actual Weight & Drift** | $w_i = \dfrac{V_i}{V_{\text{total}}}, \quad \Delta w_i = w_i - w_i^*$ | Current allocation share and deviation from target policy. |
| **Target Value & Delta** | $V_i^* = w_i^* \cdot V_{\text{total}}, \quad \Delta V_i = V_i^* - V_i$ | Monetary trade required ($\sum \Delta V_i = 0$ under self-financing). |
| **Share Delta** | $\Delta N_i = \dfrac{\Delta V_i}{P_i}$ | Shares to `BUY` ($\Delta N_i > 0$), `SELL` ($\Delta N_i < 0$), or `HOLD` ($\Delta N_i = 0$). |
