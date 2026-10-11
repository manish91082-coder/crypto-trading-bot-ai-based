from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import math

@dataclass
class RiskDecision:
    approved: bool
    risk_pct: float
    risk_amount: float
    position_size: float
    current_drawdown: float
    reason: str

class RiskGovernor:
    """
    Zero-Trust Institutional Risk Governor.
    
    Protects portfolio equity against severe drawdown cascades, correlated altcoin
    simultaneous stop-outs, and regime shifts while allowing aggressive compounding 
    during sustained alpha expansion regimes.
    
    Mathematical Principles:
    1. Drawdown-Damped Dynamic Sizing: Slashes risk percentage as drawdown increases from equity peak.
    2. Concurrent Exposure Cap: Prevents simultaneous multi-asset failure correlations.
    3. Maximum Total Portfolio Risk Ceiling: Enforces strict upper bound on aggregate open risk.
    4. Volatility Surge Scaling: Adjusts position size if current ATR expands abnormally.
    """
    
    def __init__(
        self,
        initial_capital: float = 120.0,
        base_risk_pct: float = 0.05,
        max_concurrent_trades: int = 3,
        max_portfolio_risk_pct: float = 0.12,
        dd_tier_1: float = 0.10,  # 10% DD -> 3.5% risk
        dd_tier_2: float = 0.20,  # 20% DD -> 2.5% risk
        dd_tier_3: float = 0.35,  # 35% DD -> 1.5% risk (Protection floor)
        min_risk_pct: float = 0.015,
        atr_expansion_cap: float = 2.5
    ):
        self.initial_capital = initial_capital
        self.base_risk_pct = base_risk_pct
        self.max_concurrent_trades = max_concurrent_trades
        self.max_portfolio_risk_pct = max_portfolio_risk_pct
        
        self.dd_tier_1 = dd_tier_1
        self.dd_tier_2 = dd_tier_2
        self.dd_tier_3 = dd_tier_3
        self.min_risk_pct = min_risk_pct
        self.atr_expansion_cap = atr_expansion_cap
        
        self.peak_capital = initial_capital
        self.current_drawdown = 0.0
        
    def update_capital(self, capital: float):
        """Update peak capital and current drawdown percentage."""
        if capital > self.peak_capital:
            self.peak_capital = capital
        if self.peak_capital > 0:
            self.current_drawdown = (self.peak_capital - capital) / self.peak_capital
        else:
            self.current_drawdown = 0.0

    def get_dynamic_risk_pct(self, current_capital: float) -> float:
        """
        Calculates dynamic risk percentage based on drawdown tier.
        Mathematical piecewise step damping function:
          DD < 10%            -> 5.0% (Full Aggressive Alpha)
          10% <= DD < 20%     -> 3.5% (Early Caution Damping)
          20% <= DD < 35%     -> 2.5% (High Defense Capital Protection)
          DD >= 35%           -> 1.5% (Emergency Preservation Floor)
        """
        self.update_capital(current_capital)
        
        if self.current_drawdown < self.dd_tier_1:
            return self.base_risk_pct
        elif self.current_drawdown < self.dd_tier_2:
            return 0.035
        elif self.current_drawdown < self.dd_tier_3:
            return 0.025
        else:
            return self.min_risk_pct

    def evaluate_entry(
        self,
        current_capital: float,
        entry_price: float,
        stop_loss: float,
        open_trades: List[Dict],
        atr: Optional[float] = None,
        avg_atr: Optional[float] = None
    ) -> RiskDecision:
        """
        Evaluate entry candidacy against all institutional risk constraints.
        Returns a RiskDecision containing approval status, sizing, and audit explanation.
        """
        self.update_capital(current_capital)
        
        # 1. Constraint: Maximum Concurrent Positions
        if len(open_trades) >= self.max_concurrent_trades:
            return RiskDecision(
                approved=False,
                risk_pct=0.0,
                risk_amount=0.0,
                position_size=0.0,
                current_drawdown=self.current_drawdown,
                reason=f"REJECTED: Max concurrent trades ({self.max_concurrent_trades}) reached"
            )
            
        # 2. Constraint: Dynamic Drawdown Risk Sizing
        adjusted_risk_pct = self.get_dynamic_risk_pct(current_capital)
        
        # 3. Constraint: Maximum Total Portfolio Exposure
        current_open_risk = sum(t.get('risk_amount', 0.0) for t in open_trades)
        current_open_risk_pct = (current_open_risk / current_capital) if current_capital > 0 else 0.0
        
        if (current_open_risk_pct + adjusted_risk_pct) > self.max_portfolio_risk_pct:
            # Scale down to remaining allowance if allowance >= min_risk_pct, else reject
            remaining_risk_pct = self.max_portfolio_risk_pct - current_open_risk_pct
            if remaining_risk_pct >= self.min_risk_pct:
                adjusted_risk_pct = remaining_risk_pct
            else:
                return RiskDecision(
                    approved=False,
                    risk_pct=0.0,
                    risk_amount=0.0,
                    position_size=0.0,
                    current_drawdown=self.current_drawdown,
                    reason=f"REJECTED: Max portfolio exposure ({self.max_portfolio_risk_pct*100:.1f}%) would be exceeded"
                )
                
        # 4. Calculation: Stop Distance and Position Sizing
        sl_distance = abs(entry_price - stop_loss)
        if sl_distance <= 0:
            return RiskDecision(
                approved=False,
                risk_pct=0.0,
                risk_amount=0.0,
                position_size=0.0,
                current_drawdown=self.current_drawdown,
                reason="REJECTED: Stop Loss distance is zero or negative"
            )
            
        risk_amount = current_capital * adjusted_risk_pct
        position_size = risk_amount / sl_distance
        
        # 5. Volatility Expansion Dampener (Optional Guard)
        if atr is not None and avg_atr is not None and avg_atr > 0:
            atr_ratio = atr / avg_atr
            if atr_ratio > self.atr_expansion_cap:
                dampener = self.atr_expansion_cap / atr_ratio
                position_size *= dampener
                risk_amount *= dampener
                
        return RiskDecision(
            approved=True,
            risk_pct=adjusted_risk_pct,
            risk_amount=risk_amount,
            position_size=position_size,
            current_drawdown=self.current_drawdown,
            reason=f"APPROVED: Risk {adjusted_risk_pct*100:.2f}% (DD: {self.current_drawdown*100:.2f}%)"
        )
