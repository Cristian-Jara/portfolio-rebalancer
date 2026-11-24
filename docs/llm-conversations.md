# Prompt

Need to resolve this problem, but i don't want the code. I need the more important parts to consider about a portfolio management module and the necessary equations with the references to an official document.
 
- You’re building a portfolio management module, part of a personal investments and trading app
- Construct a simple Portfolio class that has a collection of Stocks. Assume each Stock has a “Current Price” method that receives the last available price. Also, the Portfolio class has a collection of “allocated” Stocks that represents the distribution of the Stocks the Portfolio is aiming (i.e. 40% META, 60% APPL)
- Provide a portfolio rebalance method to know which Stocks should be sold and which ones should be bought to have a balanced Portfolio based on the portfolio’s allocation.
- Add documentation/comments to understand your thinking process and solution

# Response

Designing a portfolio rebalancing module requires separating **domain state** (what you own and current market prices) from **target policy** (desired allocation weights) and **order generation** (the trades required to close the gap).

---

## 1. Key Parts to Consider in the Module Design

### A. Domain Model & Separation of Concerns

* **Stock / Asset Representation:** Acts solely as a price-aware entity exposing its identifier (ticker) and its latest market valuation (`current_price`). It should not store portfolio-specific quantities or target weights, as the same stock can exist across multiple portfolios.
* **Current Holdings vs. Target Allocations:** Keep current positions (ticker $\to$ share quantity $N_i$) separate from target allocations (ticker $\to$ target weight $w_i^*$). Blending them into a single structure makes it difficult to handle stocks you own that are no longer in your target plan, or target stocks you do not yet own.
* **Rebalance Output (Trade Instructions):** The rebalance method should return structured trade directives—specifying the ticker, action (`BUY`, `SELL`, or `HOLD`), monetary amount, and share quantity—rather than mutating holdings directly. Separating calculation from execution lets the trading engine validate liquidity, fees, and user confirmation before committing orders.

### B. Validation & Mathematical Invariants

* **Weight Normalization:** Target weights must be non-negative ($w_i^* \ge 0$) and sum to $1.0$ ($100\%$). In practice, systems check that $\left\vert{}\sum w_i^* - 1\right\vert{} \le \epsilon$ (where $\epsilon$ is a tiny tolerance like $10^{-6}$) to accommodate decimal rounding.
* **Positive Prices:** Every asset involved in valuation must have a strictly positive price ($P_i \gt 0$) to prevent division-by-zero errors when converting dollar targets into share quantities.

### C. Critical Set-Theory Edge Cases

To avoid missing positions, compute rebalancing across the **union** of held tickers ($\mathcal{H}$) and target-allocated tickers ($\mathcal{T}$): $\mathcal{U} = \mathcal{H} \cup \mathcal{T}$.

* **Orphan Holdings ($i \in \mathcal{H},\ i \notin \mathcal{T}$):** Stocks currently held ($N_i \gt 0$) that have been removed from the target allocation ($w_i^* = 0$). The module must generate a full `SELL` order for all held shares.
* **Unheld Target Positions ($i \notin \mathcal{H},\ i \in \mathcal{T}$):** Stocks with a positive target weight ($w_i^* \gt 0$) that currently have zero shares ($N_i = 0$). The module must generate a `BUY` order from scratch.
* **Zero-Value Portfolio ($V_{\text{total}} = 0$):** If the portfolio holds no shares and no cash, no trades can be self-financed.

### D. Practical Trading & Precision Constraints

* **Fractional vs. Whole Shares:** Fractional trading allows exact dollar alignment. If the broker only supports whole shares, rounding buys down (flooring) prevents overspending available cash, leaving a small uninvested residual balance (*cash drag*).
* **Self-Financing & Execution Order:** Unless external cash is injected, total `BUY` value must equal total `SELL` value. In live execution, `SELL` orders must be placed and settled before `BUY` orders to ensure cash liquidity.
* **Drift Thresholds (Tolerance Bands):** Rebalancing on every minor price fluctuation creates unnecessary fees and tax events. Real-world modules often trigger trades only when an asset's actual weight deviates from its target by more than a defined corridor $\delta$ (e.g., $\pm 5\%$).
* **Fixed-Point Arithmetic:** Monetary values and share quantities should use exact decimal arithmetic rather than binary floating-point types to prevent sub-cent rounding discrepancies.

---

## 2. Necessary Equations

Let $n$ be the total number of distinct stocks in the portfolio universe $\mathcal{U} = \mathcal{H} \cup \mathcal{T}$. For each stock $i \in \{1, \dots, n\}$:

* $N_i$ = current number of shares held ($N_i \ge 0$)
* $P_i$ = current market price per share ($P_i \gt 0$)
* $w_i^*$ = target allocation weight ($0 \le w_i^* \le 1$, with $\sum_{i=1}^{n} w_i^* = 1$)
* $C$ = uninvested cash balance available in the portfolio ($C = 0$ for a strictly stock-only self-financing model)

### Step 1: Current Position Value & Total Portfolio Value

The current market value $V_i$ of each holding and the total portfolio valuation $V_{\text{total}}$ are:

$$V_i = N_i \cdot P_i$$

$$V_{\text{total}} = C + \sum_{i=1}^{n} V_i = C + \sum_{i=1}^{n} (N_i \cdot P_i)$$

### Step 2: Actual Weight & Allocation Drift

Each stock's current weight $w_i$ and its drift $\Delta w_i$ from the target weight are:

$$w_i = \frac{V_i}{V_{\text{total}}}$$

$$\Delta w_i = w_i - w_i^*$$

* If $\Delta w_i \gt 0$, the stock is **overweight** (requires selling).
* If $\Delta w_i \lt 0$, the stock is **underweight** (requires buying).

### Step 3: Target Value & Monetary Trade Delta

The target monetary value $V_i^*$ and the signed monetary adjustment $\Delta V_i$ needed to restore equilibrium are:

$$V_i^* = w_i^* \cdot V_{\text{total}}$$

$$\Delta V_i = V_i^* - V_i = (w_i^* \cdot V_{\text{total}}) - (N_i \cdot P_i)$$

By conservation of value (when $C = 0$ and $\sum w_i^* = 1$), the net sum of all trades equals zero:

$$\sum_{i=1}^{n} \Delta V_i = 0$$

### Step 4: Share Quantity Delta & Action Rule

Dividing the monetary delta by the stock's current price yields the required change in shares $\Delta N_i$:

$$\Delta N_i = \frac{\Delta V_i}{P_i} = \frac{w_i^* \cdot V_{\text{total}}}{P_i} - N_i$$

$$\text{Action}_i = \begin{cases} \text{BUY } \Delta N_i \text{ shares} & \text{if } \Delta N_i \gt 0 \\ \text{SELL } \vert{}\Delta N_i\vert{} \text{ shares} & \text{if } \Delta N_i \lt 0 \\ \text{HOLD} & \text{if } \Delta N_i = 0 \end{cases}$$

*(Optional Whole-Share Constraint)*: If fractional shares are not permitted, buy orders are floored so total outlays never exceed total proceeds:

$$\Delta N_i^{\text{buy}} = \left\lfloor \frac{\Delta V_i}{P_i} \right\rfloor$$

---

## 3. References to Official & Authoritative Documents

| Concept / Equation | Official / Authoritative Source | Key Principle Referenced |
| --- | --- | --- |
| **Portfolio Weighting & Normalization** ($\sum w_i^* = 1$) | **Harry Markowitz**, *"Portfolio Selection"*, *The Journal of Finance*, Vol. 7, No. 1 (1952), pp. 77–91 | Establishes Modern Portfolio Theory (MPT), defining portfolio allocation as a vector of non-negative asset weights summing to unity. |
| **Mechanics of Drift & Rebalancing** ($\Delta V_i = V_i^* - V_i$) | **U.S. Securities and Exchange Commission (SEC)** — Office of Investor Education and Advocacy, *Beginners' Guide to Asset Allocation, Diversification, and Rebalancing* (Investor.gov / SEC.gov) | Defines portfolio drift caused by unequal asset returns and specifies rebalancing as selling overweight holdings and buying underweight holdings to restore target weights. |
| **Rebalancing Cash Flows & Concentration Risk** | **Financial Industry Regulatory Authority (FINRA)**, *Asset Allocation and Diversification* (FINRA Investor Education) | Details concentration risk from drifted positions and outlines the two rebalancing mechanisms: reallocating proceeds from overweight sales vs. directing new cash inflows to lagging positions. |
| **Tolerance Corridors, Transaction Costs & Liquidity** | **CFA Institute**, *CFA Program Curriculum — Asset Allocation* (*Overview of Asset Allocation* & *Asset Allocation with Real-World Constraints*) | Formalizes strategic asset allocation weights ($w_i^*$), actual drifted weights ($w_i$), calendar vs. range-based (corridor) triggers, and transaction-cost/liquidity constraints. |
| **Risk-Control Objective & Hybrid Triggers** | **Vanguard Investment Strategy Group** (Jaconetti, Kinniry Jr., & Zilbering), *Best Practices for Portfolio Rebalancing* | Demonstrates that the primary objective of rebalancing is risk control relative to the target allocation rather than return maximization, comparing calendar, threshold, and hybrid ("time-and-threshold") triggers. |

---

## 4. Documenting Your Thinking Process (For Your Submission)

To satisfy the documentation requirement cleanly without clutter, structure your written notes around four short blocks:

1. **Assumptions & Scope:** Explicitly state whether your design assumes fractional shares, zero transaction fees, and a self-financing rebalance ($C = 0$).
2. **Invariants:** Document that target weights are validated to sum to $100\%$ and prices are verified to be strictly positive.
3. **Edge-Case Handling:** Explain why you iterate over the union of held and target tickers ($\mathcal{H} \cup \mathcal{T}$) so unallocated holdings are liquidated and new target positions are purchased.
4. **Complexity Analysis:** Note that computing portfolio value and trade deltas runs in linear time $\mathcal{O}(n)$ and linear space $\mathcal{O}(n)$ relative to the number of unique tickers $n$.


# Prompt

Generate the code in python and generate the respective tests

# Response

The solution is organized into two files: **`portfolio.py`** (the core domain models and rebalancing engine) and **`test_portfolio.py`** (a zero-dependency unit test suite using Python's built-in `unittest` module). Run the tests directly via `python -m unittest test_portfolio.py`.

### `portfolio.py`

```python
"""
Portfolio Management & Rebalancing Module.

Design Philosophy & Architectural Decisions:
1. Precision (`Decimal` over `float`):
   Binary floating-point arithmetic introduces sub-cent rounding drift
   (e.g., 0.1 + 0.2 != 0.3). All prices, share counts, and target weights are
   normalized to `decimal.Decimal` so conservation of value holds strictly.

2. Separation of Concerns:
   - `Stock` encapsulates market identity (ticker) and current market price.
     It does not store share quantities or target weights, allowing the same
     asset definition to be shared across portfolios.
   - `Portfolio` separates current holdings (`_holdings`) from desired policy
     (`_allocations`), while maintaining a `_stocks` registry so every asset
     in either set has an accessible `current_price()`.
   - `rebalance()` is a pure calculation that returns immutable `RebalanceOrder`
     instructions rather than mutating holdings directly. Separating order
     generation from execution lets a broker layer validate liquidity, fees,
     or user confirmation before committing trades.

3. Set-Union Rebalancing (`held_tickers | target_tickers`):
   Iterating over the union of held and allocated tickers guarantees that:
   - Orphan holdings (held > 0, target == 0%) generate full SELL orders.
   - Unheld targets (held == 0, target > 0%) generate initial BUY orders.

4. Complexity:
   For `n` distinct stocks in the portfolio universe, both valuation and
   rebalance order computation run in O(n) time and O(n) space.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Dict, List, Union

Number = Union[int, float, str, Decimal]


def _to_decimal(value: Number, field_name: str) -> Decimal:
    """Safely convert numeric inputs into finite Decimal values."""
    if isinstance(value, bool):
        raise ValueError(f"{field_name} cannot be a boolean.")
    try:
        # Convert floats via str() to avoid inheriting binary float artifacts.
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric value for {field_name}: {value!r}") from exc

    if not result.is_finite():
        raise ValueError(f"{field_name} must be a finite number.")
    return result


class TradeAction(str, Enum):
    """Supported trade directives emitted by the rebalancing engine."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class RebalanceOrder:
    """
    Immutable trade instruction for a single stock.

    Attributes:
        ticker: Stock symbol (e.g., 'META', 'AAPL').
        action: BUY, SELL, or HOLD directive.
        shares: Non-negative quantity of shares to buy or sell (0 for HOLD).
        amount: Non-negative monetary value of the trade (0 for HOLD).
        current_weight: Asset's weight in the portfolio prior to rebalancing.
        target_weight: Asset's desired weight in the portfolio.
    """

    ticker: str
    action: TradeAction
    shares: Decimal
    amount: Decimal
    current_weight: Decimal
    target_weight: Decimal


class Stock:
    """
    Represents a tradable equity with a ticker and latest available market price.

    Note on `current_price`:
    Exposes `current_price()` as the canonical accessor for the last available
    price, paired with `update_price()` to ingest subsequent market ticks.
    """

    def __init__(self, ticker: str, last_price: Number) -> None:
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError("Stock ticker must be a non-empty string.")
        self.ticker: str = ticker.strip().upper()
        self._last_price: Decimal = self._validate_price(last_price)

    @staticmethod
    def _validate_price(price: Number) -> Decimal:
        decimal_price = _to_decimal(price, "price")
        if decimal_price <= Decimal("0"):
            raise ValueError("Stock price must be strictly greater than zero.")
        return decimal_price

    def current_price(self) -> Decimal:
        """Return the last available market price for this stock."""
        return self._last_price

    def update_price(self, new_price: Number) -> None:
        """Update the stock's last available market price."""
        self._last_price = self._validate_price(new_price)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Stock):
            return NotImplemented
        return self.ticker == other.ticker

    def __hash__(self) -> int:
        return hash(self.ticker)

    def __repr__(self) -> str:
        return f"Stock(ticker={self.ticker!r}, current_price={self._last_price})"


class Portfolio:
    """
    Manages current stock holdings, target allocation weights, and rebalancing.

    Assumptions:
    - Fractional shares are supported (exact dollar-to-share alignment).
    - Rebalancing is self-financing (total BUY value == total SELL value).
    - Target allocation weights must sum to 1.0 (100%) within `WEIGHT_TOLERANCE`.
    """

    WEIGHT_TOLERANCE = Decimal("1e-6")
    SHARE_TOLERANCE = Decimal("1e-9")

    def __init__(self) -> None:
        # Registry mapping ticker -> Stock instance so `.current_price()` is
        # always accessible for both held and newly allocated positions.
        self._stocks: Dict[str, Stock] = {}
        # Current positions: ticker -> share quantity held (>= 0).
        self._holdings: Dict[str, Decimal] = {}
        # Target policy: ticker -> target weight in [0, 1].
        self._allocations: Dict[str, Decimal] = {}

    def add_holding(self, stock: Stock, shares: Number) -> None:
        """
        Add shares of a Stock to the portfolio's current holdings.
        Calling this multiple times for the same ticker accumulates shares.
        """
        if not isinstance(stock, Stock):
            raise TypeError("Expected a Stock instance.")
        qty = _to_decimal(shares, "shares")
        if qty < Decimal("0"):
            raise ValueError("Share quantity cannot be negative.")

        self._stocks[stock.ticker] = stock
        self._holdings[stock.ticker] = (
            self._holdings.get(stock.ticker, Decimal("0")) + qty
        )

    def set_target_allocations(self, allocations: Dict[Stock, Number]) -> None:
        """
        Define the desired portfolio distribution (e.g., {meta: 0.40, aapl: 0.60}).

        Validates that all weights are non-negative and sum to 1.0 (100%).
        Replaces any previously configured target allocation.
        """
        if not allocations:
            raise ValueError("Target allocations cannot be empty.")

        normalized_allocations: Dict[str, Decimal] = {}
        registered_stocks: Dict[str, Stock] = {}
        total_weight = Decimal("0")

        for stock, raw_weight in allocations.items():
            if not isinstance(stock, Stock):
                raise TypeError("Allocation keys must be Stock instances.")
            weight = _to_decimal(raw_weight, f"weight for {stock.ticker}")
            if weight < Decimal("0"):
                raise ValueError(
                    f"Target weight for {stock.ticker} cannot be negative."
                )
            if stock.ticker in normalized_allocations:
                raise ValueError(
                    f"Duplicate ticker in target allocations: {stock.ticker}"
                )

            normalized_allocations[stock.ticker] = weight
            registered_stocks[stock.ticker] = stock
            total_weight += weight

        if abs(total_weight - Decimal("1")) > self.WEIGHT_TOLERANCE:
            raise ValueError(
                f"Target allocation weights must sum to 1.0 (100%), got {total_weight}."
            )

        self._stocks.update(registered_stocks)
        self._allocations = normalized_allocations

    def total_value(self) -> Decimal:
        """Calculate total market value of all current holdings: sum(N_i * P_i)."""
        total = Decimal("0")
        for ticker, shares in self._holdings.items():
            price = self._stocks[ticker].current_price()
            total += shares * price
        return total

    def current_weights(self) -> Dict[str, Decimal]:
        """Return actual portfolio weight (w_i = V_i / V_total) for each stock."""
        total = self.total_value()
        if total == Decimal("0"):
            return {}
        return {
            ticker: (shares * self._stocks[ticker].current_price()) / total
            for ticker, shares in self._holdings.items()
            if shares > Decimal("0")
        }

    def rebalance(self) -> List[RebalanceOrder]:
        """
        Compute BUY, SELL, and HOLD instructions to align holdings with targets.

        Equations applied per asset `i` in (held_tickers | target_tickers):
            V_total = sum(N_i * P_i)
            V_i     = N_i * P_i
            V_i*    = w_i* * V_total
            dV_i    = V_i* - V_i
            dN_i    = dV_i / P_i

        Returns:
            A deterministic list of `RebalanceOrder` objects sorted by ticker.
            Returns an empty list if the portfolio has zero total value.
        """
        if not self._allocations:
            raise ValueError("Target allocations must be set before rebalancing.")

        total = self.total_value()
        if total == Decimal("0"):
            # Cannot execute a self-financing rebalance with $0 in assets.
            return []

        orders: List[RebalanceOrder] = []
        # Union ensures orphan holdings are sold and unheld targets are bought.
        universe = sorted(set(self._holdings.keys()) | set(self._allocations.keys()))

        for ticker in universe:
            stock = self._stocks[ticker]
            price = stock.current_price()

            current_shares = self._holdings.get(ticker, Decimal("0"))
            current_value = current_shares * price
            current_weight = current_value / total

            target_weight = self._allocations.get(ticker, Decimal("0"))
            target_value = target_weight * total

            delta_value = target_value - current_value
            delta_shares = delta_value / price

            if abs(delta_shares) <= self.SHARE_TOLERANCE:
                orders.append(
                    RebalanceOrder(
                        ticker=ticker,
                        action=TradeAction.HOLD,
                        shares=Decimal("0"),
                        amount=Decimal("0"),
                        current_weight=current_weight,
                        target_weight=target_weight,
                    )
                )
            elif delta_shares > Decimal("0"):
                orders.append(
                    RebalanceOrder(
                        ticker=ticker,
                        action=TradeAction.BUY,
                        shares=delta_shares,
                        amount=delta_value,
                        current_weight=current_weight,
                        target_weight=target_weight,
                    )
                )
            else:
                orders.append(
                    RebalanceOrder(
                        ticker=ticker,
                        action=TradeAction.SELL,
                        shares=abs(delta_shares),
                        amount=abs(delta_value),
                        current_weight=current_weight,
                        target_weight=target_weight,
                    )
                )

        return orders
```

---

### `test_portfolio.py`

```python
"""
Unit tests for `portfolio.py`.

Covers domain validation, standard rebalancing (META / AAPL), price drift,
self-financing conservation, orphan liquidation, unheld target initiation,
fractional shares, and non-mutation guarantees.
"""

import unittest
from decimal import Decimal

from portfolio import Portfolio, Stock, TradeAction


class TestStock(unittest.TestCase):
    def test_stock_initialization_and_current_price(self) -> None:
        meta = Stock("meta", 500.25)
        self.assertEqual(meta.ticker, "META")
        self.assertEqual(meta.current_price(), Decimal("500.25"))

    def test_update_price(self) -> None:
        aapl = Stock("AAPL", 200)
        aapl.update_price("215.50")
        self.assertEqual(aapl.current_price(), Decimal("215.50"))

    def test_invalid_stock_inputs_raise_value_error(self) -> None:
        with self.assertRaises(ValueError):
            Stock("", 100)
        with self.assertRaises(ValueError):
            Stock("   ", 100)
        with self.assertRaises(ValueError):
            Stock("AAPL", 0)
        with self.assertRaises(ValueError):
            Stock("AAPL", -50)

        aapl = Stock("AAPL", 100)
        with self.assertRaises(ValueError):
            aapl.update_price(0)


class TestPortfolioValidation(unittest.TestCase):
    def test_negative_shares_rejected(self) -> None:
        portfolio = Portfolio()
        meta = Stock("META", 500)
        with self.assertRaises(ValueError):
            portfolio.add_holding(meta, -1)

    def test_target_allocations_must_sum_to_one(self) -> None:
        portfolio = Portfolio()
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)

        with self.assertRaises(ValueError):
            portfolio.set_target_allocations(
                {meta: Decimal("0.40"), aapl: Decimal("0.50")}
            )

        with self.assertRaises(ValueError):
            portfolio.set_target_allocations(
                {meta: Decimal("0.60"), aapl: Decimal("0.60")}
            )

    def test_negative_target_weight_rejected(self) -> None:
        portfolio = Portfolio()
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)

        with self.assertRaises(ValueError):
            portfolio.set_target_allocations(
                {meta: Decimal("-0.20"), aapl: Decimal("1.20")}
            )

    def test_rebalance_without_allocations_raises_error(self) -> None:
        portfolio = Portfolio()
        portfolio.add_holding(Stock("META", 500), 10)
        with self.assertRaises(ValueError):
            portfolio.rebalance()


class TestPortfolioRebalance(unittest.TestCase):
    def test_standard_rebalance_meta_and_aapl(self) -> None:
        """
        Scenario:
        - Hold 10 META @ $500 ($5,000 -> 50%) and 25 AAPL @ $200 ($5,000 -> 50%)
        - Total value = $10,000
        - Target: 40% META ($4,000) and 60% AAPL ($6,000)
        - Expected: SELL 2 META ($1,000), BUY 5 AAPL ($1,000)
        """
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)

        portfolio = Portfolio()
        portfolio.add_holding(meta, 10)
        portfolio.add_holding(aapl, 25)
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        orders = {order.ticker: order for order in portfolio.rebalance()}

        self.assertEqual(orders["META"].action, TradeAction.SELL)
        self.assertEqual(orders["META"].shares, Decimal("2"))
        self.assertEqual(orders["META"].amount, Decimal("1000.00"))
        self.assertEqual(orders["META"].current_weight, Decimal("0.5"))
        self.assertEqual(orders["META"].target_weight, Decimal("0.40"))

        self.assertEqual(orders["AAPL"].action, TradeAction.BUY)
        self.assertEqual(orders["AAPL"].shares, Decimal("5"))
        self.assertEqual(orders["AAPL"].amount, Decimal("1000.00"))
        self.assertEqual(orders["AAPL"].current_weight, Decimal("0.5"))
        self.assertEqual(orders["AAPL"].target_weight, Decimal("0.60"))

    def test_rebalance_after_market_price_drift(self) -> None:
        """Portfolio starts balanced (40/60), then price drift triggers rebalance."""
        meta = Stock("META", 400)
        aapl = Stock("AAPL", 200)

        portfolio = Portfolio()
        # Initial: 10 META ($4,000 = 40%) + 30 AAPL ($6,000 = 60%) = $10,000
        portfolio.add_holding(meta, 10)
        portfolio.add_holding(aapl, 30)
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        # Confirm balanced initially
        initial_orders = portfolio.rebalance()
        self.assertTrue(all(o.action == TradeAction.HOLD for o in initial_orders))

        # META surges to $700, AAPL stays $200 -> Total = $7,000 + $6,000 = $13,000
        # Target META = 40% of $13,000 = $5,200 (sell $1,800 -> 1800/700 shares)
        # Target AAPL = 60% of $13,000 = $7,800 (buy $1,800 -> 9 shares)
        meta.update_price(700)
        orders = {o.ticker: o for o in portfolio.rebalance()}

        self.assertEqual(orders["META"].action, TradeAction.SELL)
        self.assertEqual(orders["META"].amount, Decimal("1800.00"))
        self.assertAlmostEqual(
            orders["META"].shares, Decimal("1800") / Decimal("700"), places=9
        )

        self.assertEqual(orders["AAPL"].action, TradeAction.BUY)
        self.assertEqual(orders["AAPL"].amount, Decimal("1800.00"))
        self.assertEqual(orders["AAPL"].shares, Decimal("9"))

    def test_orphan_holding_liquidated_and_unheld_target_bought(self) -> None:
        """
        Held stock omitted from target allocations must be sold completely;
        target stock with 0 held shares must be bought from scratch.
        """
        goog = Stock("GOOG", 200)
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 250)

        portfolio = Portfolio()
        portfolio.add_holding(goog, 5)  # $1,000 (orphan)
        portfolio.add_holding(meta, 2)  # $1,000 (already at 50% target)
        # Total = $2,000. Target: 50% META ($1,000), 50% AAPL ($1,000)
        portfolio.set_target_allocations({meta: Decimal("0.50"), aapl: Decimal("0.50")})

        orders = {o.ticker: o for o in portfolio.rebalance()}

        self.assertEqual(orders["GOOG"].action, TradeAction.SELL)
        self.assertEqual(orders["GOOG"].shares, Decimal("5"))
        self.assertEqual(orders["GOOG"].amount, Decimal("1000.00"))

        self.assertEqual(orders["META"].action, TradeAction.HOLD)
        self.assertEqual(orders["META"].shares, Decimal("0"))

        self.assertEqual(orders["AAPL"].action, TradeAction.BUY)
        self.assertEqual(orders["AAPL"].shares, Decimal("4"))
        self.assertEqual(orders["AAPL"].amount, Decimal("1000.00"))

    def test_self_financing_conservation_of_value(self) -> None:
        """Sum of BUY amounts must always equal sum of SELL amounts."""
        stocks = [
            Stock("META", 512.35),
            Stock("AAPL", 227.80),
            Stock("MSFT", 418.10),
            Stock("NVDA", 135.45),
        ]
        portfolio = Portfolio()
        portfolio.add_holding(stocks[0], 7)
        portfolio.add_holding(stocks[1], 19)
        portfolio.add_holding(stocks[2], 3)
        # stocks[3] (NVDA) has 0 shares initially

        portfolio.set_target_allocations(
            {
                stocks[0]: Decimal("0.25"),
                stocks[1]: Decimal("0.35"),
                stocks[2]: Decimal("0.15"),
                stocks[3]: Decimal("0.25"),
            }
        )

        orders = portfolio.rebalance()
        total_buy = sum(o.amount for o in orders if o.action == TradeAction.BUY)
        total_sell = sum(o.amount for o in orders if o.action == TradeAction.SELL)

        self.assertAlmostEqual(total_buy, total_sell, places=9)

    def test_empty_portfolio_returns_no_orders(self) -> None:
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)
        portfolio = Portfolio()
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        self.assertEqual(portfolio.total_value(), Decimal("0"))
        self.assertEqual(portfolio.rebalance(), [])

    def test_rebalance_does_not_mutate_holdings(self) -> None:
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)
        portfolio = Portfolio()
        portfolio.add_holding(meta, 10)
        portfolio.add_holding(aapl, 25)
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        before_weights = portfolio.current_weights()
        _ = portfolio.rebalance()
        after_weights = portfolio.current_weights()

        self.assertEqual(before_weights, after_weights)


if __name__ == "__main__":
    unittest.main()
```

Separate into different files

The codebase is split into a modular `portfolio_manager` package (separating numeric validation, the `Stock` entity, trade order models, and the `Portfolio` rebalancing engine) alongside a dedicated `tests` directory.

```text
project_root/
├── portfolio_manager/
│   ├── __init__.py
│   ├── validation.py
│   ├── stock.py
│   ├── order.py
│   └── portfolio.py
└── tests/
    ├── __init__.py
    ├── test_stock.py
    └── test_portfolio.py

```

Run the full test suite from `project_root/` with:

```bash
python -m unittest discover -s tests -v

```

---

### `portfolio_manager/validation.py`

```python
"""
Numeric coercion and validation utilities.

Centralizes conversion to `decimal.Decimal` so all domain modules enforce
exact base-10 arithmetic and reject booleans, NaNs, or non-numeric inputs.
"""

from decimal import Decimal, InvalidOperation
from typing import Union

Number = Union[int, float, str, Decimal]


def to_decimal(value: Number, field_name: str) -> Decimal:
    """Safely convert numeric inputs into finite Decimal values."""
    if isinstance(value, bool):
        raise ValueError(f"{field_name} cannot be a boolean.")
    try:
        # Convert floats via str() to avoid binary floating-point artifacts.
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric value for {field_name}: {value!r}") from exc

    if not result.is_finite():
        raise ValueError(f"{field_name} must be a finite number.")
    return result
```

---

### `portfolio_manager/stock.py`

```python
"""
Stock domain entity.

Encapsulates an asset's ticker identity and latest available market price,
decoupled from portfolio-specific share quantities or target weights.
"""

from decimal import Decimal

from portfolio_manager.validation import Number, to_decimal


class Stock:
    """Represents a tradable equity with a ticker and last available price."""

    def __init__(self, ticker: str, last_price: Number) -> None:
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError("Stock ticker must be a non-empty string.")
        self.ticker: str = ticker.strip().upper()
        self._last_price: Decimal = self._validate_price(last_price)

    @staticmethod
    def _validate_price(price: Number) -> Decimal:
        decimal_price = to_decimal(price, "price")
        if decimal_price <= Decimal("0"):
            raise ValueError("Stock price must be strictly greater than zero.")
        return decimal_price

    def current_price(self) -> Decimal:
        """Return the last available market price for this stock."""
        return self._last_price

    def update_price(self, new_price: Number) -> None:
        """Update the stock's last available market price."""
        self._last_price = self._validate_price(new_price)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Stock):
            return NotImplemented
        return self.ticker == other.ticker

    def __hash__(self) -> int:
        return hash(self.ticker)

    def __repr__(self) -> str:
        return f"Stock(ticker={self.ticker!r}, current_price={self._last_price})"
```

---

### `portfolio_manager/order.py`

```python
"""
Rebalance trade directive models.

Defines immutable output structures produced by the rebalancing engine so
order calculation remains decoupled from trade execution.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class TradeAction(str, Enum):
    """Supported trade directives emitted by the rebalancing engine."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class RebalanceOrder:
    """
    Immutable trade instruction for a single stock.

    Attributes:
        ticker: Stock symbol (e.g., 'META', 'AAPL').
        action: BUY, SELL, or HOLD directive.
        shares: Non-negative quantity of shares to buy or sell (0 for HOLD).
        amount: Non-negative monetary value of the trade (0 for HOLD).
        current_weight: Asset's weight in the portfolio prior to rebalancing.
        target_weight: Asset's desired weight in the portfolio.
    """

    ticker: str
    action: TradeAction
    shares: Decimal
    amount: Decimal
    current_weight: Decimal
    target_weight: Decimal
```

---

### `portfolio_manager/portfolio.py`

```python
"""
Portfolio management and rebalancing engine.

Architectural Notes:
- Separates current holdings (`_holdings`) from target policy (`_allocations`)
  while maintaining a `_stocks` registry so `.current_price()` is always
  available for both held and newly allocated positions.
- Computes trades across the set union (`held_tickers | target_tickers`) so
  orphan holdings are fully liquidated and unheld targets are initiated.
- Runs in O(n) time and O(n) space for `n` distinct stocks.
"""

from decimal import Decimal
from typing import Dict, List

from portfolio_manager.order import RebalanceOrder, TradeAction
from portfolio_manager.stock import Stock
from portfolio_manager.validation import Number, to_decimal


class Portfolio:
    """
    Manages current stock holdings, target allocation weights, and rebalancing.

    Assumptions:
    - Fractional shares are supported (exact dollar-to-share alignment).
    - Rebalancing is self-financing (total BUY value == total SELL value).
    - Target allocation weights must sum to 1.0 (100%) within `WEIGHT_TOLERANCE`.
    """

    WEIGHT_TOLERANCE = Decimal("1e-6")
    SHARE_TOLERANCE = Decimal("1e-9")

    def __init__(self) -> None:
        self._stocks: Dict[str, Stock] = {}
        self._holdings: Dict[str, Decimal] = {}
        self._allocations: Dict[str, Decimal] = {}

    def add_holding(self, stock: Stock, shares: Number) -> None:
        """
        Add shares of a Stock to the portfolio's current holdings.
        Calling this multiple times for the same ticker accumulates shares.
        """
        if not isinstance(stock, Stock):
            raise TypeError("Expected a Stock instance.")
        qty = to_decimal(shares, "shares")
        if qty < Decimal("0"):
            raise ValueError("Share quantity cannot be negative.")

        self._stocks[stock.ticker] = stock
        self._holdings[stock.ticker] = (
            self._holdings.get(stock.ticker, Decimal("0")) + qty
        )

    def set_target_allocations(self, allocations: Dict[Stock, Number]) -> None:
        """
        Define the desired portfolio distribution (e.g., {meta: 0.40, aapl: 0.60}).

        Validates that all weights are non-negative and sum to 1.0 (100%).
        Replaces any previously configured target allocation.
        """
        if not allocations:
            raise ValueError("Target allocations cannot be empty.")

        normalized_allocations: Dict[str, Decimal] = {}
        registered_stocks: Dict[str, Stock] = {}
        total_weight = Decimal("0")

        for stock, raw_weight in allocations.items():
            if not isinstance(stock, Stock):
                raise TypeError("Allocation keys must be Stock instances.")
            weight = to_decimal(raw_weight, f"weight for {stock.ticker}")
            if weight < Decimal("0"):
                raise ValueError(
                    f"Target weight for {stock.ticker} cannot be negative."
                )
            if stock.ticker in normalized_allocations:
                raise ValueError(
                    f"Duplicate ticker in target allocations: {stock.ticker}"
                )

            normalized_allocations[stock.ticker] = weight
            registered_stocks[stock.ticker] = stock
            total_weight += weight

        if abs(total_weight - Decimal("1")) > self.WEIGHT_TOLERANCE:
            raise ValueError(
                f"Target allocation weights must sum to 1.0 (100%), got {total_weight}."
            )

        self._stocks.update(registered_stocks)
        self._allocations = normalized_allocations

    def total_value(self) -> Decimal:
        """Calculate total market value of all current holdings: sum(N_i * P_i)."""
        total = Decimal("0")
        for ticker, shares in self._holdings.items():
            price = self._stocks[ticker].current_price()
            total += shares * price
        return total

    def current_weights(self) -> Dict[str, Decimal]:
        """Return actual portfolio weight (w_i = V_i / V_total) for each stock."""
        total = self.total_value()
        if total == Decimal("0"):
            return {}
        return {
            ticker: (shares * self._stocks[ticker].current_price()) / total
            for ticker, shares in self._holdings.items()
            if shares > Decimal("0")
        }

    def rebalance(self) -> List[RebalanceOrder]:
        """
        Compute BUY, SELL, and HOLD instructions to align holdings with targets.

        Equations applied per asset `i` in (held_tickers | target_tickers):
            V_total = sum(N_i * P_i)
            V_i     = N_i * P_i
            V_i*    = w_i* * V_total
            dV_i    = V_i* - V_i
            dN_i    = dV_i / P_i

        Returns:
            A deterministic list of `RebalanceOrder` objects sorted by ticker.
            Returns an empty list if the portfolio has zero total value.
        """
        if not self._allocations:
            raise ValueError("Target allocations must be set before rebalancing.")

        total = self.total_value()
        if total == Decimal("0"):
            return []

        orders: List[RebalanceOrder] = []
        universe = sorted(set(self._holdings.keys()) | set(self._allocations.keys()))

        for ticker in universe:
            stock = self._stocks[ticker]
            price = stock.current_price()

            current_shares = self._holdings.get(ticker, Decimal("0"))
            current_value = current_shares * price
            current_weight = current_value / total

            target_weight = self._allocations.get(ticker, Decimal("0"))
            target_value = target_weight * total

            delta_value = target_value - current_value
            delta_shares = delta_value / price

            if abs(delta_shares) <= self.SHARE_TOLERANCE:
                orders.append(
                    RebalanceOrder(
                        ticker=ticker,
                        action=TradeAction.HOLD,
                        shares=Decimal("0"),
                        amount=Decimal("0"),
                        current_weight=current_weight,
                        target_weight=target_weight,
                    )
                )
            elif delta_shares > Decimal("0"):
                orders.append(
                    RebalanceOrder(
                        ticker=ticker,
                        action=TradeAction.BUY,
                        shares=delta_shares,
                        amount=delta_value,
                        current_weight=current_weight,
                        target_weight=target_weight,
                    )
                )
            else:
                orders.append(
                    RebalanceOrder(
                        ticker=ticker,
                        action=TradeAction.SELL,
                        shares=abs(delta_shares),
                        amount=abs(delta_value),
                        current_weight=current_weight,
                        target_weight=target_weight,
                    )
                )

        return orders
```

---

### `portfolio_manager/__init__.py`

```python
"""Public package interface for the portfolio management module."""

from portfolio_manager.order import RebalanceOrder, TradeAction
from portfolio_manager.portfolio import Portfolio
from portfolio_manager.stock import Stock

__all__ = [
    "Portfolio",
    "RebalanceOrder",
    "Stock",
    "TradeAction",
]
```

---

### `tests/__init__.py`

```python
"""Test suite package for portfolio_manager."""
```

---

### `tests/test_stock.py`

```python
"""Unit tests for `portfolio_manager.stock`."""

import unittest
from decimal import Decimal

from portfolio_manager.stock import Stock


class TestStock(unittest.TestCase):
    def test_stock_initialization_and_current_price(self) -> None:
        meta = Stock("meta", 500.25)
        self.assertEqual(meta.ticker, "META")
        self.assertEqual(meta.current_price(), Decimal("500.25"))

    def test_update_price(self) -> None:
        aapl = Stock("AAPL", 200)
        aapl.update_price("215.50")
        self.assertEqual(aapl.current_price(), Decimal("215.50"))

    def test_equality_and_hashing_by_ticker(self) -> None:
        s1 = Stock("aapl", 200)
        s2 = Stock("AAPL", 210)
        self.assertEqual(s1, s2)
        self.assertEqual(hash(s1), hash(s2))

    def test_invalid_stock_inputs_raise_value_error(self) -> None:
        with self.assertRaises(ValueError):
            Stock("", 100)
        with self.assertRaises(ValueError):
            Stock("   ", 100)
        with self.assertRaises(ValueError):
            Stock("AAPL", 0)
        with self.assertRaises(ValueError):
            Stock("AAPL", -50)
        with self.assertRaises(ValueError):
            Stock("AAPL", True)

        aapl = Stock("AAPL", 100)
        with self.assertRaises(ValueError):
            aapl.update_price(0)


if __name__ == "__main__":
    unittest.main()
```

---

### `tests/test_portfolio.py`

```python
"""Unit tests for `portfolio_manager.portfolio` and rebalancing logic."""

import unittest
from decimal import Decimal

from portfolio_manager import Portfolio, Stock, TradeAction


class TestPortfolioValidation(unittest.TestCase):
    def test_negative_shares_rejected(self) -> None:
        portfolio = Portfolio()
        meta = Stock("META", 500)
        with self.assertRaises(ValueError):
            portfolio.add_holding(meta, -1)

    def test_target_allocations_must_sum_to_one(self) -> None:
        portfolio = Portfolio()
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)

        with self.assertRaises(ValueError):
            portfolio.set_target_allocations(
                {meta: Decimal("0.40"), aapl: Decimal("0.50")}
            )

        with self.assertRaises(ValueError):
            portfolio.set_target_allocations(
                {meta: Decimal("0.60"), aapl: Decimal("0.60")}
            )

    def test_negative_target_weight_rejected(self) -> None:
        portfolio = Portfolio()
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)

        with self.assertRaises(ValueError):
            portfolio.set_target_allocations(
                {meta: Decimal("-0.20"), aapl: Decimal("1.20")}
            )

    def test_rebalance_without_allocations_raises_error(self) -> None:
        portfolio = Portfolio()
        portfolio.add_holding(Stock("META", 500), 10)
        with self.assertRaises(ValueError):
            portfolio.rebalance()


class TestPortfolioRebalance(unittest.TestCase):
    def test_standard_rebalance_meta_and_aapl(self) -> None:
        """
        Hold 10 META @ $500 ($5,000 -> 50%) and 25 AAPL @ $200 ($5,000 -> 50%).
        Total = $10,000. Target: 40% META ($4,000), 60% AAPL ($6,000).
        Expected: SELL 2 META ($1,000), BUY 5 AAPL ($1,000).
        """
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)

        portfolio = Portfolio()
        portfolio.add_holding(meta, 10)
        portfolio.add_holding(aapl, 25)
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        orders = {order.ticker: order for order in portfolio.rebalance()}

        self.assertEqual(orders["META"].action, TradeAction.SELL)
        self.assertEqual(orders["META"].shares, Decimal("2"))
        self.assertEqual(orders["META"].amount, Decimal("1000.00"))
        self.assertEqual(orders["META"].current_weight, Decimal("0.5"))
        self.assertEqual(orders["META"].target_weight, Decimal("0.40"))

        self.assertEqual(orders["AAPL"].action, TradeAction.BUY)
        self.assertEqual(orders["AAPL"].shares, Decimal("5"))
        self.assertEqual(orders["AAPL"].amount, Decimal("1000.00"))
        self.assertEqual(orders["AAPL"].current_weight, Decimal("0.5"))
        self.assertEqual(orders["AAPL"].target_weight, Decimal("0.60"))

    def test_rebalance_after_market_price_drift(self) -> None:
        """Portfolio starts balanced (40/60), then price drift triggers rebalance."""
        meta = Stock("META", 400)
        aapl = Stock("AAPL", 200)

        portfolio = Portfolio()
        portfolio.add_holding(meta, 10)
        portfolio.add_holding(aapl, 30)
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        initial_orders = portfolio.rebalance()
        self.assertTrue(all(o.action == TradeAction.HOLD for o in initial_orders))

        # META surges to $700, AAPL stays $200 -> Total = $13,000
        meta.update_price(700)
        orders = {o.ticker: o for o in portfolio.rebalance()}

        self.assertEqual(orders["META"].action, TradeAction.SELL)
        self.assertEqual(orders["META"].amount, Decimal("1800.00"))
        self.assertAlmostEqual(
            orders["META"].shares, Decimal("1800") / Decimal("700"), places=9
        )

        self.assertEqual(orders["AAPL"].action, TradeAction.BUY)
        self.assertEqual(orders["AAPL"].amount, Decimal("1800.00"))
        self.assertEqual(orders["AAPL"].shares, Decimal("9"))

    def test_orphan_holding_liquidated_and_unheld_target_bought(self) -> None:
        """
        Held stock omitted from target allocations is sold completely;
        target stock with 0 held shares is bought from scratch.
        """
        goog = Stock("GOOG", 200)
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 250)

        portfolio = Portfolio()
        portfolio.add_holding(goog, 5)
        portfolio.add_holding(meta, 2)
        portfolio.set_target_allocations({meta: Decimal("0.50"), aapl: Decimal("0.50")})

        orders = {o.ticker: o for o in portfolio.rebalance()}

        self.assertEqual(orders["GOOG"].action, TradeAction.SELL)
        self.assertEqual(orders["GOOG"].shares, Decimal("5"))
        self.assertEqual(orders["GOOG"].amount, Decimal("1000.00"))

        self.assertEqual(orders["META"].action, TradeAction.HOLD)
        self.assertEqual(orders["META"].shares, Decimal("0"))

        self.assertEqual(orders["AAPL"].action, TradeAction.BUY)
        self.assertEqual(orders["AAPL"].shares, Decimal("4"))
        self.assertEqual(orders["AAPL"].amount, Decimal("1000.00"))

    def test_self_financing_conservation_of_value(self) -> None:
        """Sum of BUY amounts must always equal sum of SELL amounts."""
        stocks = [
            Stock("META", 512.35),
            Stock("AAPL", 227.80),
            Stock("MSFT", 418.10),
            Stock("NVDA", 135.45),
        ]
        portfolio = Portfolio()
        portfolio.add_holding(stocks[0], 7)
        portfolio.add_holding(stocks[1], 19)
        portfolio.add_holding(stocks[2], 3)

        portfolio.set_target_allocations(
            {
                stocks[0]: Decimal("0.25"),
                stocks[1]: Decimal("0.35"),
                stocks[2]: Decimal("0.15"),
                stocks[3]: Decimal("0.25"),
            }
        )

        orders = portfolio.rebalance()
        total_buy = sum(o.amount for o in orders if o.action == TradeAction.BUY)
        total_sell = sum(o.amount for o in orders if o.action == TradeAction.SELL)

        self.assertAlmostEqual(total_buy, total_sell, places=9)

    def test_empty_portfolio_returns_no_orders(self) -> None:
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)
        portfolio = Portfolio()
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        self.assertEqual(portfolio.total_value(), Decimal("0"))
        self.assertEqual(portfolio.rebalance(), [])

    def test_rebalance_does_not_mutate_holdings(self) -> None:
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)
        portfolio = Portfolio()
        portfolio.add_holding(meta, 10)
        portfolio.add_holding(aapl, 25)
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        before_weights = portfolio.current_weights()
        _ = portfolio.rebalance()
        after_weights = portfolio.current_weights()

        self.assertEqual(before_weights, after_weights)


if __name__ == "__main__":
    unittest.main()
```

# Prompt

Y los tests para validation.py?

# Response

Agrega el archivo **`tests/test_validation.py`** dentro de la carpeta `tests/`:

### `tests/test_validation.py`

```python
"""Unit tests for `portfolio_manager.validation`."""

import math
import unittest
from decimal import Decimal

from portfolio_manager.validation import to_decimal


class TestToDecimal(unittest.TestCase):
    def test_valid_integers(self) -> None:
        self.assertEqual(to_decimal(0, "amount"), Decimal("0"))
        self.assertEqual(to_decimal(42, "shares"), Decimal("42"))
        self.assertEqual(to_decimal(-10, "delta"), Decimal("-10"))

    def test_valid_floats_avoid_binary_artifacts(self) -> None:
        self.assertEqual(to_decimal(0.1, "weight"), Decimal("0.1"))
        self.assertEqual(to_decimal(0.2, "weight"), Decimal("0.2"))
        self.assertEqual(to_decimal(500.25, "price"), Decimal("500.25"))

    def test_valid_strings(self) -> None:
        self.assertEqual(to_decimal("100", "price"), Decimal("100"))
        self.assertEqual(to_decimal("215.50", "price"), Decimal("215.50"))
        self.assertEqual(to_decimal("  12.34  ", "price"), Decimal("12.34"))
        self.assertEqual(to_decimal("1e-6", "tolerance"), Decimal("1e-6"))

    def test_valid_decimal_passthrough(self) -> None:
        value = Decimal("123.456")
        result = to_decimal(value, "price")
        self.assertIs(result, value)

    def test_booleans_raise_value_error(self) -> None:
        for invalid_bool in (True, False):
            with self.subTest(value=invalid_bool):
                with self.assertRaisesRegex(ValueError, "shares cannot be a boolean"):
                    to_decimal(invalid_bool, "shares")

    def test_non_numeric_inputs_raise_value_error(self) -> None:
        invalid_values = ["", "   ", "abc", None, [1], {"a": 1}, object()]
        for invalid in invalid_values:
            with self.subTest(value=invalid):
                with self.assertRaisesRegex(
                    ValueError, "Invalid numeric value for price"
                ):
                    to_decimal(invalid, "price")  # type: ignore[arg-type]

    def test_non_finite_numbers_raise_value_error(self) -> None:
        non_finite_values = [
            float("nan"),
            float("inf"),
            float("-inf"),
            math.nan,
            math.inf,
            Decimal("NaN"),
            Decimal("Infinity"),
            Decimal("-Infinity"),
            "NaN",
            "Infinity",
            "-Infinity",
        ]
        for invalid in non_finite_values:
            with self.subTest(value=invalid):
                with self.assertRaisesRegex(
                    ValueError, "price must be a finite number"
                ):
                    to_decimal(invalid, "price")


if __name__ == "__main__":
    unittest.main()
```

### Estructura final de `tests/`

```text
tests/
├── __init__.py
├── test_validation.py
├── test_stock.py
└── test_portfolio.py

```

Para ejecutar toda la suite (incluyendo `test_validation.py`) desde `project_root/`:

```bash
python -m unittest discover -s tests -v

```

# Prompt

Generate a file with all the exception for better practice with the error strings

# Response

Centralizing exceptions in **`portfolio_manager/exceptions.py`** with a base `PortfolioError` class and an `ErrorMessages` registry provides three main benefits:

* **Granular or Broad Catching:** Callers can catch specific errors (e.g., `InvalidAllocationError`), any domain error (`PortfolioError`), or standard Python exceptions (`ValueError` / `TypeError`) via dual inheritance.
* **Single Source of Truth:** Error message templates live in one place, preventing string drift between production code and unit tests.
* **Clean Package API:** All exceptions are re-exported from `portfolio_manager/__init__.py`.

```text
project_root/
├── portfolio_manager/
│   ├── __init__.py
│   ├── exceptions.py   <-- New centralized exceptions & error messages
│   ├── validation.py
│   ├── stock.py
│   ├── order.py
│   └── portfolio.py
└── tests/
    ├── __init__.py
    ├── test_validation.py
    ├── test_stock.py
    └── test_portfolio.py

```

---

### 1. `portfolio_manager/exceptions.py`

```python
"""
Domain exception hierarchy and centralized error message templates.

All custom exceptions inherit from `PortfolioError` as well as standard
Python built-in exceptions (`ValueError` or `TypeError`) so consumers can
catch either domain-specific errors or standard built-in types.
"""


class ErrorMessages:
    """Centralized error message templates for the portfolio_manager package."""

    # Numeric & Validation
    BOOLEAN_NOT_ALLOWED = "{field_name} cannot be a boolean."
    INVALID_NUMERIC_VALUE = "Invalid numeric value for {field_name}: {value!r}."
    NON_FINITE_NUMBER = "{field_name} must be a finite number."

    # Stock
    EMPTY_TICKER = "Stock ticker must be a non-empty string."
    NON_POSITIVE_PRICE = "Stock price must be strictly greater than zero."

    # Portfolio & Holdings
    EXPECTED_STOCK_INSTANCE = "Expected a Stock instance."
    NEGATIVE_SHARES = "Share quantity cannot be negative."

    # Allocations & Rebalancing
    EMPTY_ALLOCATIONS = "Target allocations cannot be empty."
    INVALID_ALLOCATION_KEY = "Allocation keys must be Stock instances."
    NEGATIVE_TARGET_WEIGHT = "Target weight for {ticker} cannot be negative."
    DUPLICATE_ALLOCATION_TICKER = "Duplicate ticker in target allocations: {ticker}."
    WEIGHT_SUM_MISMATCH = (
        "Target allocation weights must sum to 1.0 (100%), got {total_weight}."
    )
    MISSING_TARGET_ALLOCATIONS = "Target allocations must be set before rebalancing."


class PortfolioError(Exception):
    """Base exception for all errors raised by the portfolio_manager package."""


class InvalidNumericError(PortfolioError, ValueError):
    """Raised when a numeric input is a boolean, unparseable, or non-finite."""


class InvalidStockError(PortfolioError, ValueError):
    """Base exception for invalid Stock attributes."""


class InvalidTickerError(InvalidStockError):
    """Raised when a stock ticker symbol is missing or blank."""


class InvalidPriceError(InvalidStockError):
    """Raised when a stock price is zero, negative, or invalid."""


class InvalidAssetTypeError(PortfolioError, TypeError):
    """Raised when an object other than a Stock instance is provided."""


class InvalidHoldingError(PortfolioError, ValueError):
    """Raised when a portfolio holding operation receives invalid parameters."""


class InvalidAllocationError(PortfolioError, ValueError):
    """Raised when target allocation weights or keys violate domain invariants."""


class MissingAllocationError(PortfolioError, ValueError):
    """Raised when rebalancing is attempted before target allocations are set."""
```

---

### 2. Updated Package Modules

#### `portfolio_manager/validation.py`

```python
"""
Numeric coercion and validation utilities.

Centralizes conversion to `decimal.Decimal` so all domain modules enforce
exact base-10 arithmetic and reject booleans, NaNs, or non-numeric inputs.
"""

from decimal import Decimal, InvalidOperation
from typing import Union

from portfolio_manager.exceptions import ErrorMessages, InvalidNumericError

Number = Union[int, float, str, Decimal]


def to_decimal(value: Number, field_name: str) -> Decimal:
    """Safely convert numeric inputs into finite Decimal values."""
    if isinstance(value, bool):
        raise InvalidNumericError(
            ErrorMessages.BOOLEAN_NOT_ALLOWED.format(field_name=field_name)
        )
    try:
        # Convert floats via str() to avoid binary floating-point artifacts.
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise InvalidNumericError(
            ErrorMessages.INVALID_NUMERIC_VALUE.format(
                field_name=field_name, value=value
            )
        ) from exc

    if not result.is_finite():
        raise InvalidNumericError(
            ErrorMessages.NON_FINITE_NUMBER.format(field_name=field_name)
        )
    return result
```

#### `portfolio_manager/stock.py`

```python
"""
Stock domain entity.

Encapsulates an asset's ticker identity and latest available market price,
decoupled from portfolio-specific share quantities or target weights.
"""

from decimal import Decimal

from portfolio_manager.exceptions import (
    ErrorMessages,
    InvalidPriceError,
    InvalidTickerError,
)
from portfolio_manager.validation import Number, to_decimal


class Stock:
    """Represents a tradable equity with a ticker and last available price."""

    def __init__(self, ticker: str, last_price: Number) -> None:
        if not isinstance(ticker, str) or not ticker.strip():
            raise InvalidTickerError(ErrorMessages.EMPTY_TICKER)
        self.ticker: str = ticker.strip().upper()
        self._last_price: Decimal = self._validate_price(last_price)

    @staticmethod
    def _validate_price(price: Number) -> Decimal:
        decimal_price = to_decimal(price, "price")
        if decimal_price <= Decimal("0"):
            raise InvalidPriceError(ErrorMessages.NON_POSITIVE_PRICE)
        return decimal_price

    def current_price(self) -> Decimal:
        """Return the last available market price for this stock."""
        return self._last_price

    def update_price(self, new_price: Number) -> None:
        """Update the stock's last available market price."""
        self._last_price = self._validate_price(new_price)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Stock):
            return NotImplemented
        return self.ticker == other.ticker

    def __hash__(self) -> int:
        return hash(self.ticker)

    def __repr__(self) -> str:
        return f"Stock(ticker={self.ticker!r}, current_price={self._last_price})"
```

#### `portfolio_manager/portfolio.py`

```python
"""
Portfolio management and rebalancing engine.

Architectural Notes:
- Separates current holdings (`_holdings`) from target policy (`_allocations`)
  while maintaining a `_stocks` registry so `.current_price()` is always
  available for both held and newly allocated positions.
- Computes trades across the set union (`held_tickers | target_tickers`) so
  orphan holdings are fully liquidated and unheld targets are initiated.
- Runs in O(n) time and O(n) space for `n` distinct stocks.
"""

from decimal import Decimal
from typing import Dict, List

from portfolio_manager.exceptions import (
    ErrorMessages,
    InvalidAllocationError,
    InvalidAssetTypeError,
    InvalidHoldingError,
    MissingAllocationError,
)
from portfolio_manager.order import RebalanceOrder, TradeAction
from portfolio_manager.stock import Stock
from portfolio_manager.validation import Number, to_decimal


class Portfolio:
    """
    Manages current stock holdings, target allocation weights, and rebalancing.

    Assumptions:
    - Fractional shares are supported (exact dollar-to-share alignment).
    - Rebalancing is self-financing (total BUY value == total SELL value).
    - Target allocation weights must sum to 1.0 (100%) within `WEIGHT_TOLERANCE`.
    """

    WEIGHT_TOLERANCE = Decimal("1e-6")
    SHARE_TOLERANCE = Decimal("1e-9")

    def __init__(self) -> None:
        self._stocks: Dict[str, Stock] = {}
        self._holdings: Dict[str, Decimal] = {}
        self._allocations: Dict[str, Decimal] = {}

    def add_holding(self, stock: Stock, shares: Number) -> None:
        """
        Add shares of a Stock to the portfolio's current holdings.
        Calling this multiple times for the same ticker accumulates shares.
        """
        if not isinstance(stock, Stock):
            raise InvalidAssetTypeError(ErrorMessages.EXPECTED_STOCK_INSTANCE)
        qty = to_decimal(shares, "shares")
        if qty < Decimal("0"):
            raise InvalidHoldingError(ErrorMessages.NEGATIVE_SHARES)

        self._stocks[stock.ticker] = stock
        self._holdings[stock.ticker] = (
            self._holdings.get(stock.ticker, Decimal("0")) + qty
        )

    def set_target_allocations(self, allocations: Dict[Stock, Number]) -> None:
        """
        Define the desired portfolio distribution (e.g., {meta: 0.40, aapl: 0.60}).

        Validates that all weights are non-negative and sum to 1.0 (100%).
        Replaces any previously configured target allocation.
        """
        if not allocations:
            raise InvalidAllocationError(ErrorMessages.EMPTY_ALLOCATIONS)

        normalized_allocations: Dict[str, Decimal] = {}
        registered_stocks: Dict[str, Stock] = {}
        total_weight = Decimal("0")

        for stock, raw_weight in allocations.items():
            if not isinstance(stock, Stock):
                raise InvalidAssetTypeError(ErrorMessages.INVALID_ALLOCATION_KEY)
            weight = to_decimal(raw_weight, f"weight for {stock.ticker}")
            if weight < Decimal("0"):
                raise InvalidAllocationError(
                    ErrorMessages.NEGATIVE_TARGET_WEIGHT.format(ticker=stock.ticker)
                )
            if stock.ticker in normalized_allocations:
                raise InvalidAllocationError(
                    ErrorMessages.DUPLICATE_ALLOCATION_TICKER.format(
                        ticker=stock.ticker
                    )
                )

            normalized_allocations[stock.ticker] = weight
            registered_stocks[stock.ticker] = stock
            total_weight += weight

        if abs(total_weight - Decimal("1")) > self.WEIGHT_TOLERANCE:
            raise InvalidAllocationError(
                ErrorMessages.WEIGHT_SUM_MISMATCH.format(total_weight=total_weight)
            )

        self._stocks.update(registered_stocks)
        self._allocations = normalized_allocations

    def total_value(self) -> Decimal:
        """Calculate total market value of all current holdings: sum(N_i * P_i)."""
        total = Decimal("0")
        for ticker, shares in self._holdings.items():
            price = self._stocks[ticker].current_price()
            total += shares * price
        return total

    def current_weights(self) -> Dict[str, Decimal]:
        """Return actual portfolio weight (w_i = V_i / V_total) for each stock."""
        total = self.total_value()
        if total == Decimal("0"):
            return {}
        return {
            ticker: (shares * self._stocks[ticker].current_price()) / total
            for ticker, shares in self._holdings.items()
            if shares > Decimal("0")
        }

    def rebalance(self) -> List[RebalanceOrder]:
        """
        Compute BUY, SELL, and HOLD instructions to align holdings with targets.

        Equations applied per asset `i` in (held_tickers | target_tickers):
            V_total = sum(N_i * P_i)
            V_i     = N_i * P_i
            V_i*    = w_i* * V_total
            dV_i    = V_i* - V_i
            dN_i    = dV_i / P_i

        Returns:
            A deterministic list of `RebalanceOrder` objects sorted by ticker.
            Returns an empty list if the portfolio has zero total value.
        """
        if not self._allocations:
            raise MissingAllocationError(ErrorMessages.MISSING_TARGET_ALLOCATIONS)

        total = self.total_value()
        if total == Decimal("0"):
            return []

        orders: List[RebalanceOrder] = []
        universe = sorted(set(self._holdings.keys()) | set(self._allocations.keys()))

        for ticker in universe:
            stock = self._stocks[ticker]
            price = stock.current_price()

            current_shares = self._holdings.get(ticker, Decimal("0"))
            current_value = current_shares * price
            current_weight = current_value / total

            target_weight = self._allocations.get(ticker, Decimal("0"))
            target_value = target_weight * total

            delta_value = target_value - current_value
            delta_shares = delta_value / price

            if abs(delta_shares) <= self.SHARE_TOLERANCE:
                orders.append(
                    RebalanceOrder(
                        ticker=ticker,
                        action=TradeAction.HOLD,
                        shares=Decimal("0"),
                        amount=Decimal("0"),
                        current_weight=current_weight,
                        target_weight=target_weight,
                    )
                )
            elif delta_shares > Decimal("0"):
                orders.append(
                    RebalanceOrder(
                        ticker=ticker,
                        action=TradeAction.BUY,
                        shares=delta_shares,
                        amount=delta_value,
                        current_weight=current_weight,
                        target_weight=target_weight,
                    )
                )
            else:
                orders.append(
                    RebalanceOrder(
                        ticker=ticker,
                        action=TradeAction.SELL,
                        shares=abs(delta_shares),
                        amount=abs(delta_value),
                        current_weight=current_weight,
                        target_weight=target_weight,
                    )
                )

        return orders
```

#### `portfolio_manager/__init__.py`

```python
"""Public package interface for the portfolio management module."""

from portfolio_manager.exceptions import (
    ErrorMessages,
    InvalidAllocationError,
    InvalidAssetTypeError,
    InvalidHoldingError,
    InvalidNumericError,
    InvalidPriceError,
    InvalidStockError,
    InvalidTickerError,
    MissingAllocationError,
    PortfolioError,
)
from portfolio_manager.order import RebalanceOrder, TradeAction
from portfolio_manager.portfolio import Portfolio
from portfolio_manager.stock import Stock

__all__ = [
    "ErrorMessages",
    "InvalidAllocationError",
    "InvalidAssetTypeError",
    "InvalidHoldingError",
    "InvalidNumericError",
    "InvalidPriceError",
    "InvalidStockError",
    "InvalidTickerError",
    "MissingAllocationError",
    "Portfolio",
    "PortfolioError",
    "RebalanceOrder",
    "Stock",
    "TradeAction",
]
```

---

### 3. Updated Unit Tests Using `ErrorMessages` & Specific Exceptions

#### `tests/test_validation.py`

```python
"""Unit tests for `portfolio_manager.validation`."""

import math
import re
import unittest
from decimal import Decimal

from portfolio_manager.exceptions import (
    ErrorMessages,
    InvalidNumericError,
    PortfolioError,
)
from portfolio_manager.validation import to_decimal


class TestToDecimal(unittest.TestCase):
    def test_valid_integers(self) -> None:
        self.assertEqual(to_decimal(0, "amount"), Decimal("0"))
        self.assertEqual(to_decimal(42, "shares"), Decimal("42"))
        self.assertEqual(to_decimal(-10, "delta"), Decimal("-10"))

    def test_valid_floats_avoid_binary_artifacts(self) -> None:
        self.assertEqual(to_decimal(0.1, "weight"), Decimal("0.1"))
        self.assertEqual(to_decimal(0.2, "weight"), Decimal("0.2"))
        self.assertEqual(to_decimal(500.25, "price"), Decimal("500.25"))

    def test_valid_strings(self) -> None:
        self.assertEqual(to_decimal("100", "price"), Decimal("100"))
        self.assertEqual(to_decimal("215.50", "price"), Decimal("215.50"))
        self.assertEqual(to_decimal("  12.34  ", "price"), Decimal("12.34"))
        self.assertEqual(to_decimal("1e-6", "tolerance"), Decimal("1e-6"))

    def test_valid_decimal_passthrough(self) -> None:
        value = Decimal("123.456")
        self.assertIs(to_decimal(value, "price"), value)

    def test_booleans_raise_invalid_numeric_error(self) -> None:
        expected_msg = re.escape(
            ErrorMessages.BOOLEAN_NOT_ALLOWED.format(field_name="shares")
        )
        for invalid_bool in (True, False):
            with self.subTest(value=invalid_bool):
                with self.assertRaisesRegex(InvalidNumericError, expected_msg):
                    to_decimal(invalid_bool, "shares")

    def test_non_numeric_inputs_raise_invalid_numeric_error(self) -> None:
        invalid_values = ["", "   ", "abc", None, [1], {"a": 1}, object()]
        for invalid in invalid_values:
            expected_msg = re.escape(
                ErrorMessages.INVALID_NUMERIC_VALUE.format(
                    field_name="price", value=invalid
                )
            )
            with self.subTest(value=invalid):
                with self.assertRaisesRegex(InvalidNumericError, expected_msg):
                    to_decimal(invalid, "price")  # type: ignore[arg-type]

    def test_non_finite_numbers_raise_invalid_numeric_error(self) -> None:
        expected_msg = re.escape(
            ErrorMessages.NON_FINITE_NUMBER.format(field_name="price")
        )
        non_finite_values = [
            float("nan"),
            float("inf"),
            float("-inf"),
            math.nan,
            math.inf,
            Decimal("NaN"),
            Decimal("Infinity"),
            Decimal("-Infinity"),
            "NaN",
            "Infinity",
            "-Infinity",
        ]
        for invalid in non_finite_values:
            with self.subTest(value=invalid):
                with self.assertRaisesRegex(InvalidNumericError, expected_msg):
                    to_decimal(invalid, "price")

    def test_exception_inheritance(self) -> None:
        self.assertTrue(issubclass(InvalidNumericError, PortfolioError))
        self.assertTrue(issubclass(InvalidNumericError, ValueError))


if __name__ == "__main__":
    unittest.main()
```

#### `tests/test_stock.py`

```python
"""Unit tests for `portfolio_manager.stock`."""

import re
import unittest
from decimal import Decimal

from portfolio_manager.exceptions import (
    ErrorMessages,
    InvalidNumericError,
    InvalidPriceError,
    InvalidStockError,
    InvalidTickerError,
    PortfolioError,
)
from portfolio_manager.stock import Stock


class TestStock(unittest.TestCase):
    def test_stock_initialization_and_current_price(self) -> None:
        meta = Stock("meta", 500.25)
        self.assertEqual(meta.ticker, "META")
        self.assertEqual(meta.current_price(), Decimal("500.25"))

    def test_update_price(self) -> None:
        aapl = Stock("AAPL", 200)
        aapl.update_price("215.50")
        self.assertEqual(aapl.current_price(), Decimal("215.50"))

    def test_equality_and_hashing_by_ticker(self) -> None:
        s1 = Stock("aapl", 200)
        s2 = Stock("AAPL", 210)
        self.assertEqual(s1, s2)
        self.assertEqual(hash(s1), hash(s2))

    def test_invalid_ticker_raises_invalid_ticker_error(self) -> None:
        expected_msg = re.escape(ErrorMessages.EMPTY_TICKER)
        for bad_ticker in ("", "   "):
            with self.assertRaisesRegex(InvalidTickerError, expected_msg):
                Stock(bad_ticker, 100)

    def test_non_positive_price_raises_invalid_price_error(self) -> None:
        expected_msg = re.escape(ErrorMessages.NON_POSITIVE_PRICE)
        for bad_price in (0, -50, "-0.01"):
            with self.assertRaisesRegex(InvalidPriceError, expected_msg):
                Stock("AAPL", bad_price)

        aapl = Stock("AAPL", 100)
        with self.assertRaisesRegex(InvalidPriceError, expected_msg):
            aapl.update_price(0)

    def test_boolean_price_raises_invalid_numeric_error(self) -> None:
        with self.assertRaises(InvalidNumericError):
            Stock("AAPL", True)

    def test_exception_hierarchy(self) -> None:
        self.assertTrue(issubclass(InvalidTickerError, InvalidStockError))
        self.assertTrue(issubclass(InvalidPriceError, InvalidStockError))
        self.assertTrue(issubclass(InvalidStockError, PortfolioError))
        self.assertTrue(issubclass(InvalidStockError, ValueError))


if __name__ == "__main__":
    unittest.main()
```

#### `tests/test_portfolio.py`

```python
"""Unit tests for `portfolio_manager.portfolio` and rebalancing logic."""

import re
import unittest
from decimal import Decimal

from portfolio_manager import (
    ErrorMessages,
    InvalidAllocationError,
    InvalidAssetTypeError,
    InvalidHoldingError,
    MissingAllocationError,
    Portfolio,
    PortfolioError,
    Stock,
    TradeAction,
)


class TestPortfolioValidation(unittest.TestCase):
    def test_invalid_stock_type_rejected(self) -> None:
        portfolio = Portfolio()
        with self.assertRaisesRegex(
            InvalidAssetTypeError, re.escape(ErrorMessages.EXPECTED_STOCK_INSTANCE)
        ):
            portfolio.add_holding("META", 10)  # type: ignore[arg-type]

        with self.assertRaisesRegex(
            InvalidAssetTypeError, re.escape(ErrorMessages.INVALID_ALLOCATION_KEY)
        ):
            portfolio.set_target_allocations({"META": Decimal("1.0")})  # type: ignore[dict-item]

    def test_negative_shares_rejected(self) -> None:
        portfolio = Portfolio()
        meta = Stock("META", 500)
        with self.assertRaisesRegex(
            InvalidHoldingError, re.escape(ErrorMessages.NEGATIVE_SHARES)
        ):
            portfolio.add_holding(meta, -1)

    def test_empty_allocations_rejected(self) -> None:
        portfolio = Portfolio()
        with self.assertRaisesRegex(
            InvalidAllocationError, re.escape(ErrorMessages.EMPTY_ALLOCATIONS)
        ):
            portfolio.set_target_allocations({})

    def test_target_allocations_must_sum_to_one(self) -> None:
        portfolio = Portfolio()
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)

        with self.assertRaisesRegex(
            InvalidAllocationError,
            re.escape(
                ErrorMessages.WEIGHT_SUM_MISMATCH.format(total_weight=Decimal("0.90"))
            ),
        ):
            portfolio.set_target_allocations(
                {meta: Decimal("0.40"), aapl: Decimal("0.50")}
            )

        with self.assertRaisesRegex(
            InvalidAllocationError,
            re.escape(
                ErrorMessages.WEIGHT_SUM_MISMATCH.format(total_weight=Decimal("1.20"))
            ),
        ):
            portfolio.set_target_allocations(
                {meta: Decimal("0.60"), aapl: Decimal("0.60")}
            )

    def test_negative_target_weight_rejected(self) -> None:
        portfolio = Portfolio()
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)

        expected_msg = re.escape(
            ErrorMessages.NEGATIVE_TARGET_WEIGHT.format(ticker="META")
        )
        with self.assertRaisesRegex(InvalidAllocationError, expected_msg):
            portfolio.set_target_allocations(
                {meta: Decimal("-0.20"), aapl: Decimal("1.20")}
            )

    def test_rebalance_without_allocations_raises_missing_allocation_error(
        self,
    ) -> None:
        portfolio = Portfolio()
        portfolio.add_holding(Stock("META", 500), 10)
        with self.assertRaisesRegex(
            MissingAllocationError,
            re.escape(ErrorMessages.MISSING_TARGET_ALLOCATIONS),
        ):
            portfolio.rebalance()

    def test_all_domain_exceptions_inherit_from_portfolio_error(self) -> None:
        for exc_cls in (
            InvalidAssetTypeError,
            InvalidHoldingError,
            InvalidAllocationError,
            MissingAllocationError,
        ):
            self.assertTrue(issubclass(exc_cls, PortfolioError))


class TestPortfolioRebalance(unittest.TestCase):
    def test_standard_rebalance_meta_and_aapl(self) -> None:
        """
        Hold 10 META @ $500 ($5,000 -> 50%) and 25 AAPL @ $200 ($5,000 -> 50%).
        Total = $10,000. Target: 40% META ($4,000), 60% AAPL ($6,000).
        Expected: SELL 2 META ($1,000), BUY 5 AAPL ($1,000).
        """
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)

        portfolio = Portfolio()
        portfolio.add_holding(meta, 10)
        portfolio.add_holding(aapl, 25)
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        orders = {order.ticker: order for order in portfolio.rebalance()}

        self.assertEqual(orders["META"].action, TradeAction.SELL)
        self.assertEqual(orders["META"].shares, Decimal("2"))
        self.assertEqual(orders["META"].amount, Decimal("1000.00"))
        self.assertEqual(orders["META"].current_weight, Decimal("0.5"))
        self.assertEqual(orders["META"].target_weight, Decimal("0.40"))

        self.assertEqual(orders["AAPL"].action, TradeAction.BUY)
        self.assertEqual(orders["AAPL"].shares, Decimal("5"))
        self.assertEqual(orders["AAPL"].amount, Decimal("1000.00"))
        self.assertEqual(orders["AAPL"].current_weight, Decimal("0.5"))
        self.assertEqual(orders["AAPL"].target_weight, Decimal("0.60"))

    def test_rebalance_after_market_price_drift(self) -> None:
        """Portfolio starts balanced (40/60), then price drift triggers rebalance."""
        meta = Stock("META", 400)
        aapl = Stock("AAPL", 200)

        portfolio = Portfolio()
        portfolio.add_holding(meta, 10)
        portfolio.add_holding(aapl, 30)
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        initial_orders = portfolio.rebalance()
        self.assertTrue(all(o.action == TradeAction.HOLD for o in initial_orders))

        meta.update_price(700)
        orders = {o.ticker: o for o in portfolio.rebalance()}

        self.assertEqual(orders["META"].action, TradeAction.SELL)
        self.assertEqual(orders["META"].amount, Decimal("1800.00"))
        self.assertAlmostEqual(
            orders["META"].shares, Decimal("1800") / Decimal("700"), places=9
        )

        self.assertEqual(orders["AAPL"].action, TradeAction.BUY)
        self.assertEqual(orders["AAPL"].amount, Decimal("1800.00"))
        self.assertEqual(orders["AAPL"].shares, Decimal("9"))

    def test_orphan_holding_liquidated_and_unheld_target_bought(self) -> None:
        """
        Held stock omitted from target allocations is sold completely;
        target stock with 0 held shares is bought from scratch.
        """
        goog = Stock("GOOG", 200)
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 250)

        portfolio = Portfolio()
        portfolio.add_holding(goog, 5)
        portfolio.add_holding(meta, 2)
        portfolio.set_target_allocations({meta: Decimal("0.50"), aapl: Decimal("0.50")})

        orders = {o.ticker: o for o in portfolio.rebalance()}

        self.assertEqual(orders["GOOG"].action, TradeAction.SELL)
        self.assertEqual(orders["GOOG"].shares, Decimal("5"))
        self.assertEqual(orders["GOOG"].amount, Decimal("1000.00"))

        self.assertEqual(orders["META"].action, TradeAction.HOLD)
        self.assertEqual(orders["META"].shares, Decimal("0"))

        self.assertEqual(orders["AAPL"].action, TradeAction.BUY)
        self.assertEqual(orders["AAPL"].shares, Decimal("4"))
        self.assertEqual(orders["AAPL"].amount, Decimal("1000.00"))

    def test_self_financing_conservation_of_value(self) -> None:
        """Sum of BUY amounts must always equal sum of SELL amounts."""
        stocks = [
            Stock("META", 512.35),
            Stock("AAPL", 227.80),
            Stock("MSFT", 418.10),
            Stock("NVDA", 135.45),
        ]
        portfolio = Portfolio()
        portfolio.add_holding(stocks[0], 7)
        portfolio.add_holding(stocks[1], 19)
        portfolio.add_holding(stocks[2], 3)

        portfolio.set_target_allocations(
            {
                stocks[0]: Decimal("0.25"),
                stocks[1]: Decimal("0.35"),
                stocks[2]: Decimal("0.15"),
                stocks[3]: Decimal("0.25"),
            }
        )

        orders = portfolio.rebalance()
        total_buy = sum(o.amount for o in orders if o.action == TradeAction.BUY)
        total_sell = sum(o.amount for o in orders if o.action == TradeAction.SELL)

        self.assertAlmostEqual(total_buy, total_sell, places=9)

    def test_empty_portfolio_returns_no_orders(self) -> None:
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)
        portfolio = Portfolio()
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        self.assertEqual(portfolio.total_value(), Decimal("0"))
        self.assertEqual(portfolio.rebalance(), [])

    def test_rebalance_does_not_mutate_holdings(self) -> None:
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)
        portfolio = Portfolio()
        portfolio.add_holding(meta, 10)
        portfolio.add_holding(aapl, 25)
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        before_weights = portfolio.current_weights()
        _ = portfolio.rebalance()
        after_weights = portfolio.current_weights()

        self.assertEqual(before_weights, after_weights)


if __name__ == "__main__":
    unittest.main()
```

Run the updated test suite from `project_root/`:

```bash
python -m unittest discover -s tests -v

```

# Prompt

I modified the code, so let's go one by one reviewing the new code and the tests. First validation.py


"""Validation utilities for numeric inputs."""

from decimal import Decimal, InvalidOperation
from typing import Union
from src.exceptions import ErrorMessages, InvalidNumericError

Number = Union[int, float, str, Decimal]

def to_decimal(value: Number, field_name: str) -> Decimal:
    """Safely convert numeric inputs into finite Decimal values."""
    if isinstance(value, bool):
        raise InvalidNumericError(
            ErrorMessages.BOOLEAN_NOT_ALLOWED.format(field_name=field_name)
        )
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise InvalidNumericError(
          ErrorMessages.INVALID_NUMERIC_VALUE.format(
              field_name=field_name, value=value
          )
        ) from exc

    if not result.is_finite():
        raise InvalidNumericError(
          ErrorMessages.NON_FINITE_NUMBER.format(field_name=field_name)
        )
    return result

# Response

### Review of `src/validation.py`

**What works well**

* **Safe float conversion:** Converting floats via `Decimal(str(value))` prevents inheriting binary floating-point artifacts (e.g., `0.1` becoming `0.10000000000000000555...`).
* **Boolean guard:** Explicitly checking `isinstance(value, bool)` before numeric conversion prevents `True`/`False` from silently coercing into `Decimal("1")` and `Decimal("0")` (since `bool` subclasses `int` in Python).
* **Exception chaining & centralized messages:** Using `raise ... from exc` preserves the root traceback while exposing a clean domain exception (`InvalidNumericError`).
* **Namespace update:** Note that the import path changed from `portfolio_manager` to `src` (`from src.exceptions import ...`), so the test suite imports should be updated to match.

**Two small improvements to consider**

1. **Signaling NaN (`Decimal("sNaN")`) edge case:** Because `isinstance(value, Decimal)` skips `Decimal(str(value))`, passing `Decimal("sNaN")` reaches `result.is_finite()` *outside* the `try` block, where Python's `decimal` module raises an uncaught `InvalidOperation` instead of `InvalidNumericError`. Moving the `is_finite()` check inside the `try` block closes that gap.
2. **PEP 8 spacing & indentation:** Add two blank lines before the top-level `def to_decimal` function, and align the hanging indentation inside the second and third `raise InvalidNumericError(...)` blocks to 4 spaces so all three match.

#### Suggested Polish for `src/validation.py`

```python
"""Validation utilities for numeric inputs."""

from decimal import Decimal, InvalidOperation
from typing import Union

from src.exceptions import ErrorMessages, InvalidNumericError

Number = Union[int, float, str, Decimal]


def to_decimal(value: Number, field_name: str) -> Decimal:
    """Safely convert numeric inputs into finite Decimal values."""
    if isinstance(value, bool):
        raise InvalidNumericError(
            ErrorMessages.BOOLEAN_NOT_ALLOWED.format(field_name=field_name)
        )
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
        if not result.is_finite():
            raise InvalidNumericError(
                ErrorMessages.NON_FINITE_NUMBER.format(field_name=field_name)
            )
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise InvalidNumericError(
            ErrorMessages.INVALID_NUMERIC_VALUE.format(
                field_name=field_name, value=value
            )
        ) from exc

    return result
```

---

### Updated `tests/test_validation.py`

Updated to import from `src.validation` and `src.exceptions`, and expanded to cover `Decimal("sNaN")`:

```python
"""Unit tests for `src.validation`."""

import math
import re
import unittest
from decimal import Decimal

from src.exceptions import (
    ErrorMessages,
    InvalidNumericError,
    PortfolioError,
)
from src.validation import to_decimal


class TestToDecimal(unittest.TestCase):
    def test_valid_integers(self) -> None:
        self.assertEqual(to_decimal(0, "amount"), Decimal("0"))
        self.assertEqual(to_decimal(42, "shares"), Decimal("42"))
        self.assertEqual(to_decimal(-10, "delta"), Decimal("-10"))

    def test_valid_floats_avoid_binary_artifacts(self) -> None:
        self.assertEqual(to_decimal(0.1, "weight"), Decimal("0.1"))
        self.assertEqual(to_decimal(0.2, "weight"), Decimal("0.2"))
        self.assertEqual(to_decimal(500.25, "price"), Decimal("500.25"))

    def test_valid_strings(self) -> None:
        self.assertEqual(to_decimal("100", "price"), Decimal("100"))
        self.assertEqual(to_decimal("215.50", "price"), Decimal("215.50"))
        self.assertEqual(to_decimal("  12.34  ", "price"), Decimal("12.34"))
        self.assertEqual(to_decimal("1e-6", "tolerance"), Decimal("1e-6"))

    def test_valid_decimal_passthrough(self) -> None:
        value = Decimal("123.456")
        self.assertIs(to_decimal(value, "price"), value)

    def test_booleans_raise_invalid_numeric_error(self) -> None:
        expected_msg = re.escape(
            ErrorMessages.BOOLEAN_NOT_ALLOWED.format(field_name="shares")
        )
        for invalid_bool in (True, False):
            with self.subTest(value=invalid_bool):
                with self.assertRaisesRegex(InvalidNumericError, expected_msg):
                    to_decimal(invalid_bool, "shares")

    def test_non_numeric_inputs_raise_invalid_numeric_error(self) -> None:
        invalid_values = ["", "   ", "abc", None, [1], {"a": 1}, object()]
        for invalid in invalid_values:
            expected_msg = re.escape(
                ErrorMessages.INVALID_NUMERIC_VALUE.format(
                    field_name="price", value=invalid
                )
            )
            with self.subTest(value=invalid):
                with self.assertRaisesRegex(InvalidNumericError, expected_msg):
                    to_decimal(invalid, "price")  # type: ignore[arg-type]

    def test_non_finite_numbers_raise_invalid_numeric_error(self) -> None:
        expected_msg = re.escape(
            ErrorMessages.NON_FINITE_NUMBER.format(field_name="price")
        )
        non_finite_values = [
            float("nan"),
            float("inf"),
            float("-inf"),
            math.nan,
            math.inf,
            Decimal("NaN"),
            Decimal("sNaN"),
            Decimal("Infinity"),
            Decimal("-Infinity"),
            "NaN",
            "Infinity",
            "-Infinity",
        ]
        for invalid in non_finite_values:
            with self.subTest(value=invalid):
                with self.assertRaisesRegex(InvalidNumericError, expected_msg):
                    to_decimal(invalid, "price")

    def test_exception_inheritance(self) -> None:
        self.assertTrue(issubclass(InvalidNumericError, PortfolioError))
        self.assertTrue(issubclass(InvalidNumericError, ValueError))


if __name__ == "__main__":
    unittest.main()
```

Whenever you're ready, paste the next file (`exceptions.py` or `stock.py`) and we'll review it along with its tests.

# Prompt

Let's go with order.py

"""Order-related data structures for the portfolio rebalancer."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

class TradeAction(str, Enum):
    """Supported trade directives emitted by the rebalancing engine."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass(frozen=True)
class RebalanceOrder:
    """
    Immutable trade instruction for a single stock.

    Attributes:
        stock_id: Stock symbol (e.g., 'META', 'AAPL'). Changed from sticker to stock_id for clarity.
        action: BUY, SELL, or HOLD directive.
        shares: Non-negative quantity of shares to buy or sell (0 for HOLD).
        amount: Non-negative monetary value of the trade (0 for HOLD).
        current_weight: Asset's weight in the portfolio prior to rebalancing.
        target_weight: Asset's desired weight in the portfolio.
    """

    stock_id: str
    action: TradeAction
    shares: Decimal
    amount: Decimal
    current_weight: Decimal
    target_weight: Decimal

# Response

### Review of `src/order.py`

**What works well**

* **String-backed enum (`TradeAction(str, Enum)`):** Inheriting from `str` and `Enum` gives you type safety while allowing direct JSON serialization and string comparisons (`order.action == "BUY"`).
* **Immutability (`@dataclass(frozen=True)`):** Freezing `RebalanceOrder` prevents downstream execution or logging layers from accidentally mutating share counts or monetary amounts after the rebalancer computes them.
* **Domain naming (`stock_id`):** Renaming `ticker` to `stock_id` is clean and unambiguous—just make sure `Stock`, `Portfolio`, and `ErrorMessages` adopt `stock_id` consistently so the terminology matches across the whole `src` package.

**Small improvements to consider**

1. **Docstring clarity:** Remove *"Changed from sticker to stock_id for clarity."* from the `stock_id` attribute docstring—changelog notes belong in commit messages rather than API docs (and it avoids the `"sticker"` typo).
2. **PEP 8 spacing:** Leave two blank lines before top-level class definitions (`class TradeAction` and `class RebalanceOrder`).
3. **Optional invariant guard (`__post_init__`):** If `RebalanceOrder` will ever be instantiated outside `Portfolio.rebalance()` (e.g., from API payloads or test fixtures), adding a `__post_init__` check prevents constructing invalid states like negative `shares`/`amount` or a `HOLD` order with non-zero quantities.

#### Suggested Polish for `src/order.py`

```python
"""Order-related data structures for the portfolio rebalancer."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class TradeAction(str, Enum):
    """Supported trade directives emitted by the rebalancing engine."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class RebalanceOrder:
    """
    Immutable trade instruction for a single stock.

    Attributes:
        stock_id: Stock identifier or symbol (e.g., 'META', 'AAPL').
        action: BUY, SELL, or HOLD directive.
        shares: Non-negative quantity of shares to buy or sell (0 for HOLD).
        amount: Non-negative monetary value of the trade (0 for HOLD).
        current_weight: Asset's weight in the portfolio prior to rebalancing.
        target_weight: Asset's desired weight in the portfolio.
    """

    stock_id: str
    action: TradeAction
    shares: Decimal
    amount: Decimal
    current_weight: Decimal
    target_weight: Decimal
```

---

### Unit Tests: `tests/test_order.py`

Since `order.py` previously relied solely on indirect coverage from `test_portfolio.py`, here is a dedicated test file covering enum behavior, field assignments, equality/hashing, and immutability:

```python
"""Unit tests for `src.order`."""

import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal

from src.order import RebalanceOrder, TradeAction


class TestTradeAction(unittest.TestCase):
    def test_enum_values_and_string_behavior(self) -> None:
        self.assertEqual(TradeAction.BUY, "BUY")
        self.assertEqual(TradeAction.SELL, "SELL")
        self.assertEqual(TradeAction.HOLD, "HOLD")
        self.assertIsInstance(TradeAction.BUY, str)

    def test_enum_lookup_from_string(self) -> None:
        self.assertIs(TradeAction("BUY"), TradeAction.BUY)
        self.assertIs(TradeAction("SELL"), TradeAction.SELL)
        self.assertIs(TradeAction("HOLD"), TradeAction.HOLD)

    def test_invalid_action_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            TradeAction("SHORT")


class TestRebalanceOrder(unittest.TestCase):
    def setUp(self) -> None:
        self.order = RebalanceOrder(
            stock_id="META",
            action=TradeAction.SELL,
            shares=Decimal("2"),
            amount=Decimal("1000.00"),
            current_weight=Decimal("0.50"),
            target_weight=Decimal("0.40"),
        )

    def test_order_attributes(self) -> None:
        self.assertEqual(self.order.stock_id, "META")
        self.assertEqual(self.order.action, TradeAction.SELL)
        self.assertEqual(self.order.shares, Decimal("2"))
        self.assertEqual(self.order.amount, Decimal("1000.00"))
        self.assertEqual(self.order.current_weight, Decimal("0.50"))
        self.assertEqual(self.order.target_weight, Decimal("0.40"))

    def test_order_is_immutable(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            self.order.shares = Decimal("5")  # type: ignore[misc]

        with self.assertRaises(FrozenInstanceError):
            self.order.action = TradeAction.BUY  # type: ignore[misc]

    def test_order_equality_and_hashing(self) -> None:
        duplicate = RebalanceOrder(
            stock_id="META",
            action=TradeAction.SELL,
            shares=Decimal("2"),
            amount=Decimal("1000.00"),
            current_weight=Decimal("0.50"),
            target_weight=Decimal("0.40"),
        )
        different = RebalanceOrder(
            stock_id="AAPL",
            action=TradeAction.BUY,
            shares=Decimal("5"),
            amount=Decimal("1000.00"),
            current_weight=Decimal("0.50"),
            target_weight=Decimal("0.60"),
        )

        self.assertEqual(self.order, duplicate)
        self.assertEqual(hash(self.order), hash(duplicate))
        self.assertNotEqual(self.order, different)
        self.assertEqual(len({self.order, duplicate, different}), 2)


if __name__ == "__main__":
    unittest.main()
```

Send over the next file (`exceptions.py`, `stock.py`, or `portfolio.py`) whenever you're ready!

# Prompt

This is exceptions.py

"""Domain exception centralized error message templates."""


class ErrorMessages:
    """Centralized error message templates for the portfolio_manager package."""

    # Numeric & Validation
    BOOLEAN_NOT_ALLOWED = "{field_name} cannot be a boolean."
    INVALID_NUMERIC_VALUE = "Invalid numeric value for {field_name}: {value!r}."
    NON_FINITE_NUMBER = "{field_name} must be a finite number."

    # Stock
    EMPTY_STOCK_ID = "Stock Id (Ticker) must be a non-empty string."
    NON_POSITIVE_PRICE = "Stock price must be strictly greater than zero."

    # Portfolio & Holdings
    EXPECTED_STOCK_INSTANCE = "Expected a Stock instance."
    NEGATIVE_SHARES = "Share quantity cannot be negative."

    # Allocations & Rebalancing
    EMPTY_ALLOCATIONS = "Target allocations cannot be empty."
    INVALID_ALLOCATION_KEY = "Allocation keys must be Stock instances."
    NEGATIVE_TARGET_WEIGHT = "Target weight for {ticker} cannot be negative."
    DUPLICATE_ALLOCATION_TICKER = "Duplicate ticker in target allocations: {ticker}."
    WEIGHT_SUM_MISMATCH = (
        "Target allocation weights must sum to 1.0 (100%), got {total_weight}."
    )
    MISSING_TARGET_ALLOCATIONS = "Target allocations must be set before rebalancing."


class PortfolioError(Exception):
    """Base exception for all errors raised by the portfolio_manager package."""


class InvalidNumericError(PortfolioError, ValueError):
    """Raised when a numeric input is a boolean, unparseable, or non-finite."""


class InvalidStockError(PortfolioError, ValueError):
    """Base exception for invalid Stock attributes."""


class InvalidStockIdError(InvalidStockError):
    """Raised when a stock Id (ticker symbol) is missing or blank."""


class InvalidPriceError(InvalidStockError):
    """Raised when a stock price is zero, negative, or invalid."""


class InvalidAssetTypeError(PortfolioError, TypeError):
    """Raised when an object other than a Stock instance is provided."""


class InvalidHoldingError(PortfolioError, ValueError):
    """Raised when a portfolio holding operation receives invalid parameters."""


class InvalidAllocationError(PortfolioError, ValueError):
    """Raised when target allocation weights or keys violate domain invariants."""


class MissingAllocationError(PortfolioError, ValueError):
    """Raised when rebalancing is attempted before target allocations are set."""

# Response

### Review of `src/exceptions.py`

**What works well**

* **Consistent `stock_id` alignment:** Renaming `InvalidTickerError` to `InvalidStockIdError` and `EMPTY_TICKER` to `EMPTY_STOCK_ID` keeps the exception layer in sync with `RebalanceOrder.stock_id`.
* **Clean inheritance hierarchy:** Grouping `InvalidStockIdError` and `InvalidPriceError` under `InvalidStockError` (while keeping `PortfolioError` at the root and pairing with `ValueError`/`TypeError`) gives callers flexible granularity when catching errors.
* **Formatting & PEP 8:** Spacing, docstrings, and class organization are clean and consistent.

**One important catch to prevent a runtime `KeyError**`

* **Placeholder mismatch in `ErrorMessages`:** In the Allocations section, `NEGATIVE_TARGET_WEIGHT` and `DUPLICATE_ALLOCATION_TICKER` still use `{ticker}` in their format strings:
```python
NEGATIVE_TARGET_WEIGHT = "Target weight for {ticker} cannot be negative."
DUPLICATE_ALLOCATION_TICKER = "Duplicate ticker in target allocations: {ticker}."
```


If `portfolio.py` updates its formatting calls to `.format(stock_id=stock.stock_id)`, Python will raise a `KeyError: 'ticker'` at runtime. Updating both templates to `{stock_id}` (and renaming `DUPLICATE_ALLOCATION_TICKER` to `DUPLICATE_ALLOCATION_STOCK_ID`) eliminates that trap.

#### Suggested Polish for `src/exceptions.py`

```python
"""Domain exception hierarchy and centralized error message templates."""


class ErrorMessages:
    """Centralized error message templates for the portfolio rebalancer."""

    # Numeric & Validation
    BOOLEAN_NOT_ALLOWED = "{field_name} cannot be a boolean."
    INVALID_NUMERIC_VALUE = "Invalid numeric value for {field_name}: {value!r}."
    NON_FINITE_NUMBER = "{field_name} must be a finite number."

    # Stock
    EMPTY_STOCK_ID = "Stock Id (Ticker) must be a non-empty string."
    NON_POSITIVE_PRICE = "Stock price must be strictly greater than zero."

    # Portfolio & Holdings
    EXPECTED_STOCK_INSTANCE = "Expected a Stock instance."
    NEGATIVE_SHARES = "Share quantity cannot be negative."

    # Allocations & Rebalancing
    EMPTY_ALLOCATIONS = "Target allocations cannot be empty."
    INVALID_ALLOCATION_KEY = "Allocation keys must be Stock instances."
    NEGATIVE_TARGET_WEIGHT = "Target weight for {stock_id} cannot be negative."
    DUPLICATE_ALLOCATION_STOCK_ID = (
        "Duplicate stock Id in target allocations: {stock_id}."
    )
    WEIGHT_SUM_MISMATCH = (
        "Target allocation weights must sum to 1.0 (100%), got {total_weight}."
    )
    MISSING_TARGET_ALLOCATIONS = "Target allocations must be set before rebalancing."


class PortfolioError(Exception):
    """Base exception for all errors raised by the portfolio rebalancer."""


class InvalidNumericError(PortfolioError, ValueError):
    """Raised when a numeric input is a boolean, unparseable, or non-finite."""


class InvalidStockError(PortfolioError, ValueError):
    """Base exception for invalid Stock attributes."""


class InvalidStockIdError(InvalidStockError):
    """Raised when a stock Id (ticker symbol) is missing or blank."""


class InvalidPriceError(InvalidStockError):
    """Raised when a stock price is zero, negative, or invalid."""


class InvalidAssetTypeError(PortfolioError, TypeError):
    """Raised when an object other than a Stock instance is provided."""


class InvalidHoldingError(PortfolioError, ValueError):
    """Raised when a portfolio holding operation receives invalid parameters."""


class InvalidAllocationError(PortfolioError, ValueError):
    """Raised when target allocation weights or keys violate domain invariants."""


class MissingAllocationError(PortfolioError, ValueError):
    """Raised when rebalancing is attempted before target allocations are set."""
```

---

### Unit Tests: `tests/test_exceptions.py`

Here is a dedicated test suite verifying the exception hierarchy, dual inheritance with Python built-ins, and formatting safety for every template in `ErrorMessages`:

```python
"""Unit tests for `src.exceptions`."""

import unittest
from decimal import Decimal

from src.exceptions import (
    ErrorMessages,
    InvalidAllocationError,
    InvalidAssetTypeError,
    InvalidHoldingError,
    InvalidNumericError,
    InvalidPriceError,
    InvalidStockError,
    InvalidStockIdError,
    MissingAllocationError,
    PortfolioError,
)


class TestExceptionHierarchy(unittest.TestCase):
    def test_all_exceptions_inherit_from_portfolio_error(self) -> None:
        domain_exceptions = (
            InvalidNumericError,
            InvalidStockError,
            InvalidStockIdError,
            InvalidPriceError,
            InvalidAssetTypeError,
            InvalidHoldingError,
            InvalidAllocationError,
            MissingAllocationError,
        )
        for exc_cls in domain_exceptions:
            with self.subTest(exception=exc_cls.__name__):
                self.assertTrue(issubclass(exc_cls, PortfolioError))

    def test_value_error_subclasses(self) -> None:
        value_error_exceptions = (
            InvalidNumericError,
            InvalidStockError,
            InvalidStockIdError,
            InvalidPriceError,
            InvalidHoldingError,
            InvalidAllocationError,
            MissingAllocationError,
        )
        for exc_cls in value_error_exceptions:
            with self.subTest(exception=exc_cls.__name__):
                self.assertTrue(issubclass(exc_cls, ValueError))

    def test_type_error_subclasses(self) -> None:
        self.assertTrue(issubclass(InvalidAssetTypeError, TypeError))
        self.assertFalse(issubclass(InvalidAssetTypeError, ValueError))

    def test_stock_error_subclasses(self) -> None:
        self.assertTrue(issubclass(InvalidStockIdError, InvalidStockError))
        self.assertTrue(issubclass(InvalidPriceError, InvalidStockError))

    def test_catching_via_base_portfolio_error(self) -> None:
        with self.assertRaises(PortfolioError):
            raise InvalidStockIdError(ErrorMessages.EMPTY_STOCK_ID)

        with self.assertRaises(InvalidStockError):
            raise InvalidPriceError(ErrorMessages.NON_POSITIVE_PRICE)


class TestErrorMessages(unittest.TestCase):
    def test_parameterized_templates_format_cleanly(self) -> None:
        formatted_cases = [
            (
                ErrorMessages.BOOLEAN_NOT_ALLOWED.format(field_name="shares"),
                "shares cannot be a boolean.",
            ),
            (
                ErrorMessages.INVALID_NUMERIC_VALUE.format(
                    field_name="price", value="abc"
                ),
                "Invalid numeric value for price: 'abc'.",
            ),
            (
                ErrorMessages.NON_FINITE_NUMBER.format(field_name="weight"),
                "weight must be a finite number.",
            ),
            (
                ErrorMessages.NEGATIVE_TARGET_WEIGHT.format(stock_id="META"),
                "Target weight for META cannot be negative.",
            ),
            (
                ErrorMessages.DUPLICATE_ALLOCATION_STOCK_ID.format(stock_id="AAPL"),
                "Duplicate stock Id in target allocations: AAPL.",
            ),
            (
                ErrorMessages.WEIGHT_SUM_MISMATCH.format(total_weight=Decimal("0.90")),
                "Target allocation weights must sum to 1.0 (100%), got 0.90.",
            ),
        ]
        for rendered, expected in formatted_cases:
            with self.subTest(expected=expected):
                self.assertEqual(rendered, expected)

    def test_static_messages_are_non_empty_strings(self) -> None:
        static_messages = (
            ErrorMessages.EMPTY_STOCK_ID,
            ErrorMessages.NON_POSITIVE_PRICE,
            ErrorMessages.EXPECTED_STOCK_INSTANCE,
            ErrorMessages.NEGATIVE_SHARES,
            ErrorMessages.EMPTY_ALLOCATIONS,
            ErrorMessages.INVALID_ALLOCATION_KEY,
            ErrorMessages.MISSING_TARGET_ALLOCATIONS,
        )
        for msg in static_messages:
            self.assertIsInstance(msg, str)
            self.assertTrue(msg.strip())


if __name__ == "__main__":
    unittest.main()
```

Send over `stock.py` next whenever you're ready!

# Prompt

Stock.py

"""Stock domain entity representing a tradable equity."""

from decimal import Decimal

from src.validation import Number, to_decimal
from src.exceptions import ErrorMessages, InvalidPriceError, InvalidStockIdError

class Stock:
    """Represents a tradable equity with a stock_id (ticker) and last available price."""

    def __init__(self, stock_id: str, last_price: Number) -> None:
        if not isinstance(stock_id, str) or not stock_id.strip():
            raise InvalidStockIdError(
                ErrorMessages.EMPTY_STOCK_ID.format(ticker=stock_id)
            )
        self.stock_id: str = stock_id.strip().upper()
        self._last_price: Decimal = self._validate_price(last_price)

    @staticmethod
    def _validate_price(price: Number) -> Decimal:
        decimal_price = to_decimal(price, "price")
        if decimal_price <= Decimal("0"):
            raise InvalidPriceError(
                ErrorMessages.NON_POSITIVE_PRICE
            )
        return decimal_price

    def current_price(self) -> Decimal:
        """Return the last available market price for this stock."""
        return self._last_price

    def update_price(self, new_price: Number) -> None:
        """Update the stock's last available market price."""
        self._last_price = self._validate_price(new_price)

# Response

### Review of `src/stock.py`

**What works well**

* **Consistent domain naming:** Using `stock_id` (normalized with `.strip().upper()`) aligns cleanly with `RebalanceOrder.stock_id` and `InvalidStockIdError`.
* **Single validation path (`_validate_price`):** Routing both `__init__` and `update_price` through `_validate_price`—which delegates parsing to `to_decimal` before checking `<= Decimal("0")`—guarantees that initial prices and subsequent price ticks enforce the exact same invariants.
* **Encapsulation:** Keeping `_last_price` private behind `current_price()` and `update_price()` prevents external callers from bypassing validation.

**Three things to fix or improve**

1. **Missing `__eq__`, `__hash__`, and `__repr__` (Important):** Without custom `__eq__` and `__hash__`, Python falls back to object identity (`id(self)`), so `Stock("META", 500) == Stock("META", 500)` evaluates to `False`. Because `Stock` instances act as dictionary keys in `Portfolio.set_target_allocations(...)`, defining equality and hashing on `self.stock_id` ensures two `Stock` objects representing the same equity behave as the same key—and adding `__repr__` makes test failure outputs readable.
2. **Redundant `.format(ticker=stock_id)` call:** In `src/exceptions.py`, `ErrorMessages.EMPTY_STOCK_ID` is a static string with no placeholders (`"Stock Id (Ticker) must be a non-empty string."`). Calling `.format(ticker=stock_id)` does nothing and references the old `ticker` name, so it can be removed.
3. **Lowercase filename (`stock.py`) & PEP 8 spacing:** Make sure the file on disk is named lowercase `src/stock.py` (not `Stock.py`) so `from src.stock import Stock` works reliably on case-sensitive filesystems (such as Linux/Docker), and leave two blank lines before `class Stock`.

#### Suggested Polish for `src/stock.py`

```python
"""Stock domain entity representing a tradable equity."""

from decimal import Decimal

from src.exceptions import ErrorMessages, InvalidPriceError, InvalidStockIdError
from src.validation import Number, to_decimal


class Stock:
    """Represents a tradable equity with a stock_id (ticker) and last available price."""

    def __init__(self, stock_id: str, last_price: Number) -> None:
        if not isinstance(stock_id, str) or not stock_id.strip():
            raise InvalidStockIdError(ErrorMessages.EMPTY_STOCK_ID)
        self.stock_id: str = stock_id.strip().upper()
        self._last_price: Decimal = self._validate_price(last_price)

    @staticmethod
    def _validate_price(price: Number) -> Decimal:
        decimal_price = to_decimal(price, "price")
        if decimal_price <= Decimal("0"):
            raise InvalidPriceError(ErrorMessages.NON_POSITIVE_PRICE)
        return decimal_price

    def current_price(self) -> Decimal:
        """Return the last available market price for this stock."""
        return self._last_price

    def update_price(self, new_price: Number) -> None:
        """Update the stock's last available market price."""
        self._last_price = self._validate_price(new_price)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Stock):
            return NotImplemented
        return self.stock_id == other.stock_id

    def __hash__(self) -> int:
        return hash(self.stock_id)

    def __repr__(self) -> str:
        return f"Stock(stock_id={self.stock_id!r}, current_price={self._last_price})"
```

---

### Updated `tests/test_stock.py`

```python
"""Unit tests for `src.stock`."""

import re
import unittest
from decimal import Decimal

from src.exceptions import (
    ErrorMessages,
    InvalidNumericError,
    InvalidPriceError,
    InvalidStockError,
    InvalidStockIdError,
    PortfolioError,
)
from src.stock import Stock


class TestStock(unittest.TestCase):
    def test_stock_initialization_normalizes_id_and_sets_price(self) -> None:
        meta = Stock("  meta  ", 500.25)
        self.assertEqual(meta.stock_id, "META")
        self.assertEqual(meta.current_price(), Decimal("500.25"))

    def test_update_price(self) -> None:
        aapl = Stock("AAPL", 200)
        aapl.update_price("215.50")
        self.assertEqual(aapl.current_price(), Decimal("215.50"))

    def test_equality_and_hashing_by_stock_id(self) -> None:
        s1 = Stock("aapl", 200)
        s2 = Stock("AAPL", 210)
        s3 = Stock("META", 500)

        self.assertEqual(s1, s2)
        self.assertEqual(hash(s1), hash(s2))
        self.assertNotEqual(s1, s3)
        self.assertNotEqual(s1, "AAPL")

    def test_repr_contains_stock_id_and_price(self) -> None:
        meta = Stock("META", "500.25")
        self.assertEqual(repr(meta), "Stock(stock_id='META', current_price=500.25)")

    def test_invalid_stock_id_raises_invalid_stock_id_error(self) -> None:
        expected_msg = re.escape(ErrorMessages.EMPTY_STOCK_ID)
        invalid_ids = ["", "   ", "\t\n", None, 123]
        for bad_id in invalid_ids:
            with self.subTest(stock_id=bad_id):
                with self.assertRaisesRegex(InvalidStockIdError, expected_msg):
                    Stock(bad_id, 100)  # type: ignore[arg-type]

    def test_non_positive_price_raises_invalid_price_error(self) -> None:
        expected_msg = re.escape(ErrorMessages.NON_POSITIVE_PRICE)
        for bad_price in (0, -50, "-0.01"):
            with self.subTest(price=bad_price):
                with self.assertRaisesRegex(InvalidPriceError, expected_msg):
                    Stock("AAPL", bad_price)

        aapl = Stock("AAPL", 100)
        with self.assertRaisesRegex(InvalidPriceError, expected_msg):
            aapl.update_price(0)

    def test_invalid_numeric_price_raises_invalid_numeric_error(self) -> None:
        for bad_price in (True, False, "not-a-number", float("nan"), float("inf")):
            with self.subTest(price=bad_price):
                with self.assertRaises(InvalidNumericError):
                    Stock("AAPL", bad_price)  # type: ignore[arg-type]

    def test_exception_hierarchy(self) -> None:
        self.assertTrue(issubclass(InvalidStockIdError, InvalidStockError))
        self.assertTrue(issubclass(InvalidPriceError, InvalidStockError))
        self.assertTrue(issubclass(InvalidStockError, PortfolioError))
        self.assertTrue(issubclass(InvalidStockError, ValueError))


if __name__ == "__main__":
    unittest.main()
```

Send over `portfolio.py` whenever you're ready for the final file review!

# Prompt

portfolio.py

"""
Portfolio management and rebalancing engine.

Architectural Notes & Assumptions:
- Separates current holdings (`_holdings`) from target policy (`_allocations`)
  while maintaining a `_stocks` registry so `.current_price()` is always
  available for both held and newly allocated positions.
- Computes trades across the set union (`held_tickers | target_tickers`) so
  orphan holdings are fully liquidated and unheld targets are initiated.
- Runs in O(n) time and O(n) space for `n` distinct stocks.
- Fractional shares are supported (exact dollar-to-share alignment).
- Rebalancing is self-financing (total BUY value == total SELL value).
- Target allocation weights must sum to 1.0 (100%) within `WEIGHT_TOLERANCE`.
"""

from decimal import Decimal
from typing import Dict, List

from src.order import RebalanceOrder, TradeAction
from src.stock import Stock
from src.validation import Number, to_decimal
from src.exceptions import (
    ErrorMessages,
    InvalidAllocationError,
    InvalidAssetTypeError,
    InvalidHoldingError,
    MissingAllocationError,
)


class Portfolio:
    """
    Manages current stock holdings, target allocation weights, and rebalancing.
    """

    WEIGHT_TOLERANCE = Decimal("1e-6")
    SHARE_TOLERANCE = Decimal("1e-9")

    def __init__(self) -> None:
        self._stocks: Dict[str, Stock] = {}
        self._holdings: Dict[str, Decimal] = {}
        self._allocations: Dict[str, Decimal] = {}

    def add_holding(self, stock: Stock, shares: Number) -> None:
        """
        Add shares of a Stock to the portfolio's current holdings.
        Calling this multiple times for the same ticker accumulates shares.
        """
        if not isinstance(stock, Stock):
            raise InvalidAssetTypeError(ErrorMessages.EXPECTED_STOCK_INSTANCE)
        qty = to_decimal(shares, "shares")
        if qty < Decimal("0"):
            raise InvalidHoldingError(ErrorMessages.NEGATIVE_HOLDING)

        self._stocks[stock.stock_id] = stock
        self._holdings[stock.stock_id] = self._holdings.get(stock.stock_id, Decimal("0")) + qty

    def set_target_allocations(self, allocations: Dict[Stock, Number]) -> None:
        """
        Define the desired portfolio distribution (e.g., {meta: 0.40, aapl: 0.60}).

        Validates that all weights are non-negative and sum to 1.0 (100%).
        Replaces any previously configured target allocation.
        """
        if not allocations:
            raise InvalidAllocationError(ErrorMessages.EMPTY_TARGET_ALLOCATIONS)

        normalized_allocations: Dict[str, Decimal] = {}
        registered_stocks: Dict[str, Stock] = {}
        total_weight = Decimal("0")

        for stock, raw_weight in allocations.items():
            if not isinstance(stock, Stock):
                raise InvalidAssetTypeError(ErrorMessages.EXPECTED_STOCK_INSTANCE)
            weight = to_decimal(raw_weight, f"weight for {stock.stock_id}")
            if weight < Decimal("0"):
                raise InvalidAllocationError(
                    ErrorMessages.NEGATIVE_TARGET_WEIGHT.format(ticker=stock.stock_id)
                )
            if stock.stock_id in normalized_allocations:
                raise InvalidAllocationError(
                    ErrorMessages.DUPLICATE_TARGET_WEIGHT.format(ticker=stock.stock_id)
                )

            normalized_allocations[stock.stock_id] = weight
            registered_stocks[stock.stock_id] = stock
            total_weight += weight

        if abs(total_weight - Decimal("1")) > self.WEIGHT_TOLERANCE:
            raise InvalidAllocationError(
                ErrorMessages.TARGET_WEIGHTS_NOT_SUM_TO_ONE.format(total_weight=total_weight)
            )

        self._stocks.update(registered_stocks)
        self._allocations = normalized_allocations

    def total_value(self) -> Decimal:
        """Calculate total market value of all current holdings: sum(N_i * P_i)."""
        total = Decimal("0")
        for stock_id, shares in self._holdings.items():
            price = self._stocks[stock_id].current_price()
            total += shares * price
        return total

    def current_weights(self) -> Dict[str, Decimal]:
        """Return actual portfolio weight (w_i = V_i / V_total) for each stock."""
        total = self.total_value()
        if total == Decimal("0"):
            return {}
        return {
            stock_id: (shares * self._stocks[stock_id].current_price()) / total
            for stock_id, shares in self._holdings.items()
            if shares > Decimal("0")
        }

    def rebalance(self) -> List[RebalanceOrder]:
        """
        Compute BUY, SELL, and HOLD instructions to align holdings with targets.

        Equations applied per asset `i` in (held_tickers | target_tickers):
            V_total = sum(N_i * P_i)
            V_i     = N_i * P_i
            V_i*    = w_i* * V_total
            dV_i    = V_i* - V_i
            dN_i    = dV_i / P_i

        Returns:
            A deterministic list of `RebalanceOrder` objects sorted by ticker.
            Returns an empty list if the portfolio has zero total value.
        """
        if not self._allocations:
            raise MissingAllocationError(ErrorMessages.MISSING_TARGET_ALLOCATIONS)

        total = self.total_value()
        if total == Decimal("0"):
            return []

        orders: List[RebalanceOrder] = []
        universe = sorted(set(self._holdings.keys()) | set(self._allocations.keys()))

        for stock_id in universe:
            stock = self._stocks[stock_id]
            price = stock.current_price()

            current_shares = self._holdings.get(stock_id, Decimal("0"))
            current_value = current_shares * price
            current_weight = current_value / total

            target_weight = self._allocations.get(stock_id, Decimal("0"))
            target_value = target_weight * total

            delta_value = target_value - current_value
            delta_shares = delta_value / price

            if abs(delta_shares) <= self.SHARE_TOLERANCE:
                orders.append(
                    RebalanceOrder(
                        stock_id=stock_id,
                        action=TradeAction.HOLD,
                        shares=Decimal("0"),
                        amount=Decimal("0"),
                        current_weight=current_weight,
                        target_weight=target_weight,
                    )
                )
            elif delta_shares > Decimal("0"):
                orders.append(
                    RebalanceOrder(
                        stock_id=stock_id,
                        action=TradeAction.BUY,
                        shares=delta_shares,
                        amount=delta_value,
                        current_weight=current_weight,
                        target_weight=target_weight,
                    )
                )
            else:
                orders.append(
                    RebalanceOrder(
                        stock_id=stock_id,
                        action=TradeAction.SELL,
                        shares=abs(delta_shares),
                        amount=abs(delta_value),
                        current_weight=current_weight,
                        target_weight=target_weight,
                    )
                )

        return orders


# Response

### Review of `src/portfolio.py`

**What works well**

* **End-to-end `stock_id` consistency:** `_stocks`, `_holdings`, `_allocations`, and `RebalanceOrder(stock_id=...)` all use `stock_id` uniformly.
* **Clean architectural boundaries:** `rebalance()` stays pure (non-mutating), handles zero-value portfolios gracefully, and iterates over `sorted(set(self._holdings.keys()) | set(self._allocations.keys()))` in deterministic $\mathcal{O}(n)$ time.

**Critical Fix — `ErrorMessages` Attribute Mismatches**
Comparing `src/portfolio.py` against the `ErrorMessages` class you wrote in `src/exceptions.py`, four attribute names do not match and will raise an `AttributeError` at runtime when those validation paths run:

| Used in `src/portfolio.py` | Defined in `src/exceptions.py` |
| --- | --- |
| `ErrorMessages.NEGATIVE_HOLDING` | `ErrorMessages.NEGATIVE_SHARES` |
| `ErrorMessages.EMPTY_TARGET_ALLOCATIONS` | `ErrorMessages.EMPTY_ALLOCATIONS` |
| `ErrorMessages.DUPLICATE_TARGET_WEIGHT` | `ErrorMessages.DUPLICATE_ALLOCATION_TICKER` *(or `DUPLICATE_ALLOCATION_STOCK_ID`)* |
| `ErrorMessages.TARGET_WEIGHTS_NOT_SUM_TO_ONE` | `ErrorMessages.WEIGHT_SUM_MISMATCH` |

Two minor cleanups alongside that fix:

* **Allocation key error message:** In `set_target_allocations`, use `ErrorMessages.INVALID_ALLOCATION_KEY` (which you already defined in `exceptions.py`) when a dictionary key is not a `Stock` instance.
* **Format placeholder alignment:** Make sure the keyword in `.format(...)` for `NEGATIVE_TARGET_WEIGHT` and `DUPLICATE_ALLOCATION_*` matches the placeholder in `src/exceptions.py` (`{stock_id}` if you updated `exceptions.py`, or `{ticker}` if you kept it as-is).

---

### Suggested Polish for `src/portfolio.py`

*(Synced with the `ErrorMessages` definitions from `src/exceptions.py`)*

```python
"""
Portfolio management and rebalancing engine.

Architectural Notes & Assumptions:
- Separates current holdings (`_holdings`) from target policy (`_allocations`)
  while maintaining a `_stocks` registry so `.current_price()` is always
  available for both held and newly allocated positions.
- Computes trades across the set union (`held_stock_ids | target_stock_ids`) so
  orphan holdings are fully liquidated and unheld targets are initiated.
- Runs in O(n) time and O(n) space for `n` distinct stocks.
- Fractional shares are supported (exact dollar-to-share alignment).
- Rebalancing is self-financing (total BUY value == total SELL value).
- Target allocation weights must sum to 1.0 (100%) within `WEIGHT_TOLERANCE`.
"""

from decimal import Decimal
from typing import Dict, List

from src.exceptions import (
    ErrorMessages,
    InvalidAllocationError,
    InvalidAssetTypeError,
    InvalidHoldingError,
    MissingAllocationError,
)
from src.order import RebalanceOrder, TradeAction
from src.stock import Stock
from src.validation import Number, to_decimal


class Portfolio:
    """Manages current stock holdings, target allocation weights, and rebalancing."""

    WEIGHT_TOLERANCE = Decimal("1e-6")
    SHARE_TOLERANCE = Decimal("1e-9")

    def __init__(self) -> None:
        self._stocks: Dict[str, Stock] = {}
        self._holdings: Dict[str, Decimal] = {}
        self._allocations: Dict[str, Decimal] = {}

    def add_holding(self, stock: Stock, shares: Number) -> None:
        """
        Add shares of a Stock to the portfolio's current holdings.
        Calling this multiple times for the same stock_id accumulates shares.
        """
        if not isinstance(stock, Stock):
            raise InvalidAssetTypeError(ErrorMessages.EXPECTED_STOCK_INSTANCE)
        qty = to_decimal(shares, "shares")
        if qty < Decimal("0"):
            raise InvalidHoldingError(ErrorMessages.NEGATIVE_SHARES)

        self._stocks[stock.stock_id] = stock
        self._holdings[stock.stock_id] = (
            self._holdings.get(stock.stock_id, Decimal("0")) + qty
        )

    def set_target_allocations(self, allocations: Dict[Stock, Number]) -> None:
        """
        Define the desired portfolio distribution (e.g., {meta: 0.40, aapl: 0.60}).

        Validates that all weights are non-negative and sum to 1.0 (100%).
        Replaces any previously configured target allocation.
        """
        if not allocations:
            raise InvalidAllocationError(ErrorMessages.EMPTY_ALLOCATIONS)

        normalized_allocations: Dict[str, Decimal] = {}
        registered_stocks: Dict[str, Stock] = {}
        total_weight = Decimal("0")

        for stock, raw_weight in allocations.items():
            if not isinstance(stock, Stock):
                raise InvalidAssetTypeError(ErrorMessages.INVALID_ALLOCATION_KEY)
            weight = to_decimal(raw_weight, f"weight for {stock.stock_id}")
            if weight < Decimal("0"):
                raise InvalidAllocationError(
                    ErrorMessages.NEGATIVE_TARGET_WEIGHT.format(stock_id=stock.stock_id)
                )
            if stock.stock_id in normalized_allocations:
                raise InvalidAllocationError(
                    ErrorMessages.DUPLICATE_ALLOCATION_STOCK_ID.format(
                        stock_id=stock.stock_id
                    )
                )

            normalized_allocations[stock.stock_id] = weight
            registered_stocks[stock.stock_id] = stock
            total_weight += weight

        if abs(total_weight - Decimal("1")) > self.WEIGHT_TOLERANCE:
            raise InvalidAllocationError(
                ErrorMessages.WEIGHT_SUM_MISMATCH.format(total_weight=total_weight)
            )

        self._stocks.update(registered_stocks)
        self._allocations = normalized_allocations

    def total_value(self) -> Decimal:
        """Calculate total market value of all current holdings: sum(N_i * P_i)."""
        total = Decimal("0")
        for stock_id, shares in self._holdings.items():
            price = self._stocks[stock_id].current_price()
            total += shares * price
        return total

    def current_weights(self) -> Dict[str, Decimal]:
        """Return actual portfolio weight (w_i = V_i / V_total) for each stock."""
        total = self.total_value()
        if total == Decimal("0"):
            return {}
        return {
            stock_id: (shares * self._stocks[stock_id].current_price()) / total
            for stock_id, shares in self._holdings.items()
            if shares > Decimal("0")
        }

    def rebalance(self) -> List[RebalanceOrder]:
        """
        Compute BUY, SELL, and HOLD instructions to align holdings with targets.

        Equations applied per asset `i` in (held_stock_ids | target_stock_ids):
            V_total = sum(N_i * P_i)
            V_i     = N_i * P_i
            V_i*    = w_i* * V_total
            dV_i    = V_i* - V_i
            dN_i    = dV_i / P_i

        Returns:
            A deterministic list of `RebalanceOrder` objects sorted by stock_id.
            Returns an empty list if the portfolio has zero total value.
        """
        if not self._allocations:
            raise MissingAllocationError(ErrorMessages.MISSING_TARGET_ALLOCATIONS)

        total = self.total_value()
        if total == Decimal("0"):
            return []

        orders: List[RebalanceOrder] = []
        universe = sorted(set(self._holdings.keys()) | set(self._allocations.keys()))

        for stock_id in universe:
            stock = self._stocks[stock_id]
            price = stock.current_price()

            current_shares = self._holdings.get(stock_id, Decimal("0"))
            current_value = current_shares * price
            current_weight = current_value / total

            target_weight = self._allocations.get(stock_id, Decimal("0"))
            target_value = target_weight * total

            delta_value = target_value - current_value
            delta_shares = delta_value / price

            if abs(delta_shares) <= self.SHARE_TOLERANCE:
                orders.append(
                    RebalanceOrder(
                        stock_id=stock_id,
                        action=TradeAction.HOLD,
                        shares=Decimal("0"),
                        amount=Decimal("0"),
                        current_weight=current_weight,
                        target_weight=target_weight,
                    )
                )
            elif delta_shares > Decimal("0"):
                orders.append(
                    RebalanceOrder(
                        stock_id=stock_id,
                        action=TradeAction.BUY,
                        shares=delta_shares,
                        amount=delta_value,
                        current_weight=current_weight,
                        target_weight=target_weight,
                    )
                )
            else:
                orders.append(
                    RebalanceOrder(
                        stock_id=stock_id,
                        action=TradeAction.SELL,
                        shares=abs(delta_shares),
                        amount=abs(delta_value),
                        current_weight=current_weight,
                        target_weight=target_weight,
                    )
                )

        return orders
```

---

### Updated `tests/test_portfolio.py`

Updated to import from `src.*` and assert against `order.stock_id` and `ErrorMessages`:

```python
"""Unit tests for `src.portfolio` and rebalancing logic."""

import re
import unittest
from decimal import Decimal

from src.exceptions import (
    ErrorMessages,
    InvalidAllocationError,
    InvalidAssetTypeError,
    InvalidHoldingError,
    MissingAllocationError,
    PortfolioError,
)
from src.order import TradeAction
from src.portfolio import Portfolio
from src.stock import Stock


class TestPortfolioValidation(unittest.TestCase):
    def test_invalid_stock_type_rejected(self) -> None:
        portfolio = Portfolio()
        with self.assertRaisesRegex(
            InvalidAssetTypeError, re.escape(ErrorMessages.EXPECTED_STOCK_INSTANCE)
        ):
            portfolio.add_holding("META", 10)  # type: ignore[arg-type]

        with self.assertRaisesRegex(
            InvalidAssetTypeError, re.escape(ErrorMessages.INVALID_ALLOCATION_KEY)
        ):
            portfolio.set_target_allocations({"META": Decimal("1.0")})  # type: ignore[dict-item]

    def test_negative_shares_rejected(self) -> None:
        portfolio = Portfolio()
        meta = Stock("META", 500)
        with self.assertRaisesRegex(
            InvalidHoldingError, re.escape(ErrorMessages.NEGATIVE_SHARES)
        ):
            portfolio.add_holding(meta, -1)

    def test_accumulating_holdings_sums_shares(self) -> None:
        portfolio = Portfolio()
        meta = Stock("META", 500)
        portfolio.add_holding(meta, 4)
        portfolio.add_holding(meta, 6)
        self.assertEqual(portfolio.total_value(), Decimal("5000"))

    def test_empty_allocations_rejected(self) -> None:
        portfolio = Portfolio()
        with self.assertRaisesRegex(
            InvalidAllocationError, re.escape(ErrorMessages.EMPTY_ALLOCATIONS)
        ):
            portfolio.set_target_allocations({})

    def test_target_allocations_must_sum_to_one(self) -> None:
        portfolio = Portfolio()
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)

        with self.assertRaisesRegex(
            InvalidAllocationError,
            re.escape(
                ErrorMessages.WEIGHT_SUM_MISMATCH.format(total_weight=Decimal("0.90"))
            ),
        ):
            portfolio.set_target_allocations(
                {meta: Decimal("0.40"), aapl: Decimal("0.50")}
            )

        with self.assertRaisesRegex(
            InvalidAllocationError,
            re.escape(
                ErrorMessages.WEIGHT_SUM_MISMATCH.format(total_weight=Decimal("1.20"))
            ),
        ):
            portfolio.set_target_allocations(
                {meta: Decimal("0.60"), aapl: Decimal("0.60")}
            )

    def test_negative_target_weight_rejected(self) -> None:
        portfolio = Portfolio()
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)

        expected_msg = re.escape(
            ErrorMessages.NEGATIVE_TARGET_WEIGHT.format(stock_id="META")
        )
        with self.assertRaisesRegex(InvalidAllocationError, expected_msg):
            portfolio.set_target_allocations(
                {meta: Decimal("-0.20"), aapl: Decimal("1.20")}
            )

    def test_rebalance_without_allocations_raises_missing_allocation_error(
        self,
    ) -> None:
        portfolio = Portfolio()
        portfolio.add_holding(Stock("META", 500), 10)
        with self.assertRaisesRegex(
            MissingAllocationError,
            re.escape(ErrorMessages.MISSING_TARGET_ALLOCATIONS),
        ):
            portfolio.rebalance()

    def test_all_domain_exceptions_inherit_from_portfolio_error(self) -> None:
        for exc_cls in (
            InvalidAssetTypeError,
            InvalidHoldingError,
            InvalidAllocationError,
            MissingAllocationError,
        ):
            self.assertTrue(issubclass(exc_cls, PortfolioError))


class TestPortfolioRebalance(unittest.TestCase):
    def test_standard_rebalance_meta_and_aapl(self) -> None:
        """
        Hold 10 META @ $500 ($5,000 -> 50%) and 25 AAPL @ $200 ($5,000 -> 50%).
        Total = $10,000. Target: 40% META ($4,000), 60% AAPL ($6,000).
        Expected: SELL 2 META ($1,000), BUY 5 AAPL ($1,000).
        """
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)

        portfolio = Portfolio()
        portfolio.add_holding(meta, 10)
        portfolio.add_holding(aapl, 25)
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        orders = {order.stock_id: order for order in portfolio.rebalance()}

        self.assertEqual(orders["META"].action, TradeAction.SELL)
        self.assertEqual(orders["META"].shares, Decimal("2"))
        self.assertEqual(orders["META"].amount, Decimal("1000.00"))
        self.assertEqual(orders["META"].current_weight, Decimal("0.5"))
        self.assertEqual(orders["META"].target_weight, Decimal("0.40"))

        self.assertEqual(orders["AAPL"].action, TradeAction.BUY)
        self.assertEqual(orders["AAPL"].shares, Decimal("5"))
        self.assertEqual(orders["AAPL"].amount, Decimal("1000.00"))
        self.assertEqual(orders["AAPL"].current_weight, Decimal("0.5"))
        self.assertEqual(orders["AAPL"].target_weight, Decimal("0.60"))

    def test_rebalance_after_market_price_drift(self) -> None:
        """Portfolio starts balanced (40/60), then price drift triggers rebalance."""
        meta = Stock("META", 400)
        aapl = Stock("AAPL", 200)

        portfolio = Portfolio()
        portfolio.add_holding(meta, 10)
        portfolio.add_holding(aapl, 30)
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        initial_orders = portfolio.rebalance()
        self.assertTrue(all(o.action == TradeAction.HOLD for o in initial_orders))

        # META surges to $700, AAPL stays $200 -> Total = $13,000
        meta.update_price(700)
        orders = {o.stock_id: o for o in portfolio.rebalance()}

        self.assertEqual(orders["META"].action, TradeAction.SELL)
        self.assertEqual(orders["META"].amount, Decimal("1800.00"))
        self.assertAlmostEqual(
            orders["META"].shares, Decimal("1800") / Decimal("700"), places=9
        )

        self.assertEqual(orders["AAPL"].action, TradeAction.BUY)
        self.assertEqual(orders["AAPL"].amount, Decimal("1800.00"))
        self.assertEqual(orders["AAPL"].shares, Decimal("9"))

    def test_orphan_holding_liquidated_and_unheld_target_bought(self) -> None:
        """
        Held stock omitted from target allocations is sold completely;
        target stock with 0 held shares is bought from scratch.
        """
        goog = Stock("GOOG", 200)
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 250)

        portfolio = Portfolio()
        portfolio.add_holding(goog, 5)
        portfolio.add_holding(meta, 2)
        portfolio.set_target_allocations({meta: Decimal("0.50"), aapl: Decimal("0.50")})

        orders = {o.stock_id: o for o in portfolio.rebalance()}

        self.assertEqual(orders["GOOG"].action, TradeAction.SELL)
        self.assertEqual(orders["GOOG"].shares, Decimal("5"))
        self.assertEqual(orders["GOOG"].amount, Decimal("1000.00"))

        self.assertEqual(orders["META"].action, TradeAction.HOLD)
        self.assertEqual(orders["META"].shares, Decimal("0"))

        self.assertEqual(orders["AAPL"].action, TradeAction.BUY)
        self.assertEqual(orders["AAPL"].shares, Decimal("4"))
        self.assertEqual(orders["AAPL"].amount, Decimal("1000.00"))

    def test_self_financing_conservation_of_value(self) -> None:
        """Sum of BUY amounts must always equal sum of SELL amounts."""
        stocks = [
            Stock("META", 512.35),
            Stock("AAPL", 227.80),
            Stock("MSFT", 418.10),
            Stock("NVDA", 135.45),
        ]
        portfolio = Portfolio()
        portfolio.add_holding(stocks[0], 7)
        portfolio.add_holding(stocks[1], 19)
        portfolio.add_holding(stocks[2], 3)

        portfolio.set_target_allocations(
            {
                stocks[0]: Decimal("0.25"),
                stocks[1]: Decimal("0.35"),
                stocks[2]: Decimal("0.15"),
                stocks[3]: Decimal("0.25"),
            }
        )

        orders = portfolio.rebalance()
        total_buy = sum(o.amount for o in orders if o.action == TradeAction.BUY)
        total_sell = sum(o.amount for o in orders if o.action == TradeAction.SELL)

        self.assertAlmostEqual(total_buy, total_sell, places=9)

    def test_empty_portfolio_returns_no_orders(self) -> None:
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)
        portfolio = Portfolio()
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        self.assertEqual(portfolio.total_value(), Decimal("0"))
        self.assertEqual(portfolio.current_weights(), {})
        self.assertEqual(portfolio.rebalance(), [])

    def test_rebalance_does_not_mutate_holdings(self) -> None:
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)
        portfolio = Portfolio()
        portfolio.add_holding(meta, 10)
        portfolio.add_holding(aapl, 25)
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        before_weights = portfolio.current_weights()
        _ = portfolio.rebalance()
        after_weights = portfolio.current_weights()

        self.assertEqual(before_weights, after_weights)


if __name__ == "__main__":
    unittest.main()
```

With all five modules (`validation.py`, `order.py`, `exceptions.py`, `stock.py`, `portfolio.py`) reviewed, you can run the entire suite from your project root using `python -m unittest discover -s tests -v`.

# Prompt

Built the readme for the project with this considerations:

I'm working with pyproject and ruff so its important to configure the environment

# Response

```markdown
# Portfolio Rebalancer

A lightweight, zero-runtime-dependency portfolio management and rebalancing engine built in Python. Given a collection of current stock holdings, live market prices, and target allocation weights (e.g., 40% `META`, 60% `AAPL`), the module computes deterministic `BUY`, `SELL`, and `HOLD` directives to bring the portfolio back into balance.

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

### 2. Configure `pyproject.toml`

Ensure your `pyproject.toml` defines the project metadata, `ruff` as a development dependency, and the linter/formatter rules:

```toml
[project]
name = "portfolio-rebalancer"
version = "0.1.0"
description = "Self-financing portfolio management and rebalancing module."
readme = "README.md"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["ruff>=0.8.0"]

[tool.ruff]
line-length = 88
target-version = "py312"
src = ["src", "test"]
respect-gitignore = false

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "lf"
docstring-code-format = true

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # Pyflakes (unused imports/variables)
    "I",   # isort (import sorting)
    "B",   # flake8-bugbear (common bugs & design anti-patterns)
    "UP",  # pyupgrade (modern Python syntax)
    "SIM", # flake8-simplify
]
```

> **Note on `respect-gitignore = false`:** If this repository lives inside a parent directory ignored by an upper-level `.gitignore`, keeping `respect-gitignore = false` ensures Ruff still discovers files in `src/` and `test/` while continuing to skip `.venv/` and `__pycache__/`.

### 3. Install Development Tools

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

### Authoritative References
* **Harry Markowitz**, *"Portfolio Selection"*, *The Journal of Finance*, Vol. 7, No. 1 (1952) — Defines portfolio allocation as a vector of non-negative weights summing to $1.0$.
* **U.S. Securities and Exchange Commission (SEC)**, *Beginners' Guide to Asset Allocation, Diversification, and Rebalancing* (Investor.gov) — Establishes drift mechanics and rebalancing by trimming overweight positions to fund underweight ones.
* **FINRA**, *Asset Allocation and Diversification* — Covers concentration risk from portfolio drift and self-financing vs. cash-inflow rebalancing.
* **CFA Institute**, *CFA Program Curriculum — Asset Allocation* — Formalizes strategic target weights ($w_i^*$), actual weights ($w_i$), and real-world trading constraints.

```