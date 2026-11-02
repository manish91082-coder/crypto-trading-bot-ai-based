"""
Synthetic validation of the N3 POT / GPD estimator against known distributions (protocol thresholds).
(1) Student-t (nu = 4) losses, 200,000 draws: VaR99, VaR99.9 within 5 % of the true t quantiles; ES99 within 10 % of
    the true t expected shortfall (closed form: ES_p = f(q)/(1-p) * (nu + q^2)/(nu - 1), f = t pdf, q = t quantile).
(2) Exponential losses (xi = 0): VaR99 / VaR99.9 within 5 % of -ln(1-p).
(3) The ES formula re-derived by numerical integration of the fitted GPD tail (independent of the closed form).
"""
import sys
from pathlib import Path
import numpy as np
from scipy import stats, integrate

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "execution"))
import n3_evt_monitor as M


def main():
    rng = np.random.default_rng(42)
    nu = 4
    x = stats.t.rvs(nu, size=200_000, random_state=rng)
    est = M.pot(x)
    for p, tag in ((0.99, "99"), (0.999, "999")):
        true = stats.t.ppf(p, nu)
        assert abs(est[f"VaR{tag}"] / true - 1) < 0.05, (tag, est[f"VaR{tag}"], true)
    q = stats.t.ppf(0.99, nu)
    es_true = stats.t.pdf(q, nu) / 0.01 * (nu + q ** 2) / (nu - 1)
    assert abs(est["ES99"] / es_true - 1) < 0.10, (est["ES99"], es_true)
    print(f"[1 PASS] Student-t(4): VaR99 {est['VaR99']:.4f} vs {stats.t.ppf(0.99, nu):.4f}; VaR99.9 {est['VaR999']:.4f} vs "
          f"{stats.t.ppf(0.999, nu):.4f}; ES99 {est['ES99']:.4f} vs {es_true:.4f}; xi {est['xi']:.3f} (theory 1/nu = 0.25)")
    e = rng.exponential(1.0, 200_000)
    est2 = M.pot(e)
    for p, tag in ((0.99, "99"), (0.999, "999")):
        assert abs(est2[f"VaR{tag}"] / -np.log(1 - p) - 1) < 0.05, (tag, est2[f"VaR{tag}"])
    print(f"[2 PASS] Exponential: VaR99 {est2['VaR99']:.4f} vs {-np.log(0.01):.4f}; VaR99.9 {est2['VaR999']:.4f} vs {-np.log(0.001):.4f}; "
          f"xi {est2['xi']:.3f} (theory 0)")
    # (3) ES by integrating the fitted tail beyond VaR: ES = VaR + E[L - VaR | L > VaR]
    u, xi, beta, n, nu_ = est["u"], est["xi"], est["beta"], est["n"], est["n_u"]
    var = est["VaR99"]
    sf = lambda l: (nu_ / n) * (1 + xi * (l - u) / beta) ** (-1 / xi)          # P(L > l) under the fitted tail
    mean_excess = integrate.quad(sf, var, np.inf)[0] / sf(var)
    assert abs((var + mean_excess) / est["ES99"] - 1) < 1e-6, (var + mean_excess, est["ES99"])
    print(f"[3 PASS] ES99 closed form {est['ES99']:.6f} = numerical integration of the fitted tail {var + mean_excess:.6f}")
    print("N3 SYNTHETIC VALIDATION PASS")


if __name__ == "__main__":
    main()
