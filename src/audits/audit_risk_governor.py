import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from risk_governor import RiskGovernor

def run_risk_governor_audit():
    print("==================================================")
    print("ZERO-TRUST AUDIT: RISK GOVERNOR MATHEMATICAL PROOF")
    print("==================================================")
    
    gov = RiskGovernor(
        initial_capital=1000.0,
        base_risk_pct=0.05,
        max_concurrent_trades=3,
        max_portfolio_risk_pct=0.12,
        dd_tier_1=0.10,
        dd_tier_2=0.20,
        dd_tier_3=0.35,
        min_risk_pct=0.015
    )
    
    # TEST 1: Baseline Peak (DD = 0%)
    gov.update_capital(1000.0)
    risk_0 = gov.get_dynamic_risk_pct(1000.0)
    print(f"[TEST 1] Baseline Capital $1000 (DD: {gov.current_drawdown*100:.1f}%) -> Risk: {risk_0*100:.2f}%")
    assert risk_0 == 0.05, f"Expected 0.05, got {risk_0}"
    print("  -> [PASS] Base risk matches 5.00%")
    
    # TEST 2: Tier 1 Drawdown (DD = 15%)
    gov.update_capital(850.0)
    risk_15 = gov.get_dynamic_risk_pct(850.0)
    print(f"[TEST 2] Capital $850 (DD: {gov.current_drawdown*100:.1f}%) -> Risk: {risk_15*100:.2f}%")
    assert risk_15 == 0.035, f"Expected 0.035, got {risk_15}"
    print("  -> [PASS] Tier 1 damping correctly scaled to 3.50%")
    
    # TEST 3: Tier 2 Drawdown (DD = 25%)
    gov.update_capital(750.0)
    risk_25 = gov.get_dynamic_risk_pct(750.0)
    print(f"[TEST 3] Capital $750 (DD: {gov.current_drawdown*100:.1f}%) -> Risk: {risk_25*100:.2f}%")
    assert risk_25 == 0.025, f"Expected 0.025, got {risk_25}"
    print("  -> [PASS] Tier 2 defense correctly scaled to 2.50%")
    
    # TEST 4: Tier 3 Drawdown Floor (DD = 40%)
    gov.update_capital(600.0)
    risk_40 = gov.get_dynamic_risk_pct(600.0)
    print(f"[TEST 4] Capital $600 (DD: {gov.current_drawdown*100:.1f}%) -> Risk: {risk_40*100:.2f}%")
    assert risk_40 == 0.015, f"Expected 0.015, got {risk_40}"
    print("  -> [PASS] Preservation floor correctly enforced at 1.50%")
    
    # TEST 5: Recovery to New Peak (DD = 0%)
    gov.update_capital(1200.0)
    risk_new_peak = gov.get_dynamic_risk_pct(1200.0)
    print(f"[TEST 5] Recovered to $1200 (DD: {gov.current_drawdown*100:.1f}%) -> Risk: {risk_new_peak*100:.2f}%")
    assert risk_new_peak == 0.05, f"Expected 0.05, got {risk_new_peak}"
    print("  -> [PASS] Risk smoothly restored to 5.00% upon new all-time high")
    
    # TEST 6: Concurrent Position Cap
    open_trades = [
        {'symbol': 'BTCUSDT', 'risk_amount': 30.0},
        {'symbol': 'ETHUSDT', 'risk_amount': 30.0},
        {'symbol': 'SOLUSDT', 'risk_amount': 30.0}
    ]
    dec_max = gov.evaluate_entry(
        current_capital=1200.0,
        entry_price=100.0,
        stop_loss=95.0,
        open_trades=open_trades
    )
    print(f"[TEST 6] 4th trade candidacy with 3 open positions -> Approved: {dec_max.approved} ({dec_max.reason})")
    assert not dec_max.approved, "Should reject when 3 positions are open"
    print("  -> [PASS] Concurrent position limit strictly enforced")
    
    # TEST 7: Portfolio Exposure Ceiling
    open_trades_2 = [
        {'symbol': 'BTCUSDT', 'risk_amount': 100.0} # 100/1200 = 8.33% risk
    ]
    # Max portfolio risk is 12%, remaining is 12% - 8.33% = 3.67%
    # Candidate base risk is 5%, so it should scale down to 3.67%
    dec_ceil = gov.evaluate_entry(
        current_capital=1200.0,
        entry_price=100.0,
        stop_loss=95.0,
        open_trades=open_trades_2
    )
    print(f"[TEST 7] Trade candidacy with 8.33% portfolio exposure -> Approved: {dec_ceil.approved} | Risk: {dec_ceil.risk_pct*100:.2f}%")
    assert dec_ceil.approved, "Should approve scaled-down risk"
    assert round(dec_ceil.risk_pct, 4) == round(0.12 - (100.0/1200.0), 4), "Should scale risk to exact remaining ceiling"
    print("  -> [PASS] Portfolio ceiling scaled risk dynamically to protect capital")

    print("\n==================================================")
    print("AUDIT RESULT: ALL RISK GOVERNOR TESTS PASSED 100%")
    print("==================================================")

if __name__ == '__main__':
    run_risk_governor_audit()
