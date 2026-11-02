/* BTC-ALLTF study (2026-10-28): loop indicators for rules.py (causal: value at t uses bars 0..t only).
   Build: gcc -O2 -shared -o src/btc_alltf/ind.dll src/btc_alltf/ind.c   NaN = not available yet. */
#include <stdint.h>
#include <math.h>
#define EXP __declspec(dllexport)

/* weighted moving average, weights 1..n (newest = n) */
EXP void wma(int N, const double *x, int n, double *out) {
    double wsum = n * (n + 1) / 2.0;
    for (int t = 0; t < N; t++) {
        out[t] = NAN;
        if (t < n - 1) continue;
        double s = 0; int ok = 1;
        for (int k = 0; k < n; k++) { double v = x[t - k]; if (!isfinite(v)) { ok = 0; break; } s += v * (n - k); }
        if (ok) out[t] = s / wsum;
    }
}

/* rolling mean absolute deviation around the window mean (CCI) */
EXP void mad(int N, const double *x, int n, double *out) {
    for (int t = 0; t < N; t++) {
        out[t] = NAN;
        if (t < n - 1) continue;
        double m = 0; int ok = 1;
        for (int k = 0; k < n; k++) { double v = x[t - k]; if (!isfinite(v)) { ok = 0; break; } m += v; }
        if (!ok) continue;
        m /= n; double s = 0;
        for (int k = 0; k < n; k++) s += fabs(x[t - k] - m);
        out[t] = s / n;
    }
}

/* bars since the highest (mode 1) / lowest (mode -1) value inside the window of n bars ending at t (ties: most recent) */
EXP void ext_age(int N, const double *x, int n, int mode, double *out) {
    for (int t = 0; t < N; t++) {
        out[t] = NAN;
        if (t < n - 1) continue;
        int best = t; double bv = x[t];
        for (int k = 1; k < n; k++) { double v = x[t - k]; if (mode > 0 ? v > bv : v < bv) { bv = v; best = t - k; } }
        out[t] = t - best;
    }
}

/* percent rank of x[t] among the previous n-1 values of the window (Connors RSI): share of window values < x[t], x 100 */
EXP void pct_rank(int N, const double *x, int n, double *out) {
    for (int t = 0; t < N; t++) {
        out[t] = NAN;
        if (t < n - 1 || !isfinite(x[t])) continue;
        int cnt = 0, ok = 1;
        for (int k = 1; k < n; k++) { double v = x[t - k]; if (!isfinite(v)) { ok = 0; break; } if (v < x[t]) cnt++; }
        if (ok) out[t] = 100.0 * cnt / (n - 1);
    }
}

/* Parabolic SAR (Wilder), same algorithm as methods_bench.psar */
EXP void psar(int N, const double *h, const double *l, double step, double mx, double *out) {
    if (N < 1) return;
    int up = 1; double af = step, ep = h[0], s = l[0];
    out[0] = NAN;
    for (int i = 1; i < N; i++) {
        s = s + af * (ep - s);
        if (up) {
            double a = l[i - 1], b = (i >= 2 ? l[i - 2] : l[i - 1]);
            if (a < s) s = a; if (b < s) s = b;
            if (l[i] < s) { up = 0; s = ep; ep = l[i]; af = step; }
            else if (h[i] > ep) { ep = h[i]; af = af + step < mx ? af + step : mx; }
        } else {
            double a = h[i - 1], b = (i >= 2 ? h[i - 2] : h[i - 1]);
            if (a > s) s = a; if (b > s) s = b;
            if (h[i] > s) { up = 1; s = ep; ep = h[i]; af = step; }
            else if (l[i] < ep) { ep = l[i]; af = af + step < mx ? af + step : mx; }
        }
        out[i] = s;
    }
}

/* Supertrend direction (+1/-1, 0 before ATR exists), same algorithm as methods_bench.supertrend; atr = Wilder ATR(n) */
EXP void supertrend(int N, const double *h, const double *l, const double *c, const double *atr, double m, double *out) {
    double fu_p = NAN, fl_p = NAN, d_p = 0;
    for (int i = 0; i < N; i++) {
        double hl2 = (h[i] + l[i]) / 2, ub = hl2 + m * atr[i], lb = hl2 - m * atr[i];
        double fu, fl, d;
        if (i == 0 || !isfinite(ub)) { out[i] = 0; fu_p = ub; fl_p = lb; d_p = 0; continue; }
        fu = (!isfinite(fu_p) || ub < fu_p || c[i - 1] > fu_p) ? ub : fu_p;
        fl = (!isfinite(fl_p) || lb > fl_p || c[i - 1] < fl_p) ? lb : fl_p;
        double prev = d_p != 0 ? d_p : 1;
        if (!isfinite(fu_p)) d = 0;
        else d = c[i] > fu_p ? 1 : (c[i] < fl_p ? -1 : prev);
        out[i] = d; fu_p = fu; fl_p = fl; d_p = d;
    }
}

/* KAMA(n, fast, slow), same as methods_bench.kama: starts at bar n with the close */
EXP void kama(int N, const double *c, const double *sc, int n, double *out) {
    for (int i = 0; i < N; i++) out[i] = NAN;
    if (N <= n) return;
    out[n] = c[n];
    for (int i = n + 1; i < N; i++) out[i] = out[i - 1] + sc[i] * (c[i] - out[i - 1]);
}

/* Ehlers Fisher transform core, same as methods_bench.fisher (x = 2*((med-ll)/(hh-ll)-0.5), NaN -> 0) */
EXP void fisher(int N, const double *x, double *out) {
    double v = 0, f = 0;
    if (N > 0) out[0] = 0;
    for (int i = 1; i < N; i++) {
        double xi = isfinite(x[i]) ? x[i] : 0.0;
        v = 0.33 * xi + 0.67 * v; if (v > 0.999) v = 0.999; if (v < -0.999) v = -0.999;
        f = 0.5 * log((1 + v) / (1 - v)) + 0.5 * f;
        out[i] = f;
    }
}

/* up/down streak length of closes (Connors RSI): +k after k rising closes, -k after k falling, 0 if unchanged */
EXP void streak(int N, const double *c, double *out) {
    if (N > 0) out[0] = 0;
    for (int i = 1; i < N; i++) {
        double d = c[i] - c[i - 1], p = out[i - 1];
        out[i] = d > 0 ? (p > 0 ? p + 1 : 1) : (d < 0 ? (p < 0 ? p - 1 : -1) : 0);
    }
}

/* ZigZag on closes with an ATR threshold: a new swing direction is CONFIRMED when the close has moved k*atr[t] away from
   the running extreme of the current swing. out = direction of the last confirmed swing (+1 up, -1 down, 0 none yet). */
EXP void zigzag(int N, const double *c, const double *atr, double k, double *out) {
    int dir = 0; double hi = NAN, lo = NAN;
    for (int i = 0; i < N; i++) {
        double x = c[i], a = atr[i];
        if (!isfinite(a) || a <= 0) { out[i] = dir; if (isfinite(x)) { if (!isfinite(hi) || x > hi) hi = x; if (!isfinite(lo) || x < lo) lo = x; } continue; }
        if (dir >= 0) {                                       /* up swing (or none): track the high, confirm a down swing */
            if (!isfinite(hi) || x > hi) hi = x;
            if (x <= hi - k * a) { dir = -1; lo = x; }
            else if (dir == 0 && isfinite(lo) && x >= lo + k * a) { dir = 1; hi = x; }
        } else {
            if (!isfinite(lo) || x < lo) lo = x;
            if (x >= lo + k * a) { dir = 1; hi = x; }
        }
        out[i] = dir;
    }
}

/* Fractal pivots (2 bars each side), known only 2 bars later. Swing-structure state at t from the pivots confirmed by t:
   +1 if the last two confirmed pivot highs AND lows are rising (HH+HL), -1 if both falling (LH+LL), else 0.
   Double bottom / top EVENTS: the last two confirmed pivot lows are within tol*atr of each other (atr at the second
   one's confirmation) and the close breaks above the highest pivot high confirmed between them -> +1 at that bar
   (once per pattern); mirror for a double top -> -1. */
EXP void structure(int N, const double *h, const double *l, const double *c, const double *atr, double tol,
                   double *state, double *dbl) {
    double ph1 = NAN, ph2 = NAN, pl1 = NAN, pl2 = NAN;       /* 1 = last, 2 = the one before */
    double neck_hi = NAN, neck_lo = NAN; int armed_b = 0, armed_t = 0;
    double hi_since_pl = NAN, lo_since_ph = NAN;              /* highest pivot high since the previous pivot low, etc. */
    for (int t = 0; t < N; t++) {
        state[t] = 0; dbl[t] = 0;
        if (t >= 4) {
            int p = t - 2;
            int isH = h[p] > h[p - 1] && h[p] > h[p - 2] && h[p] >= h[p + 1] && h[p] >= h[p + 2];
            int isL = l[p] < l[p - 1] && l[p] < l[p - 2] && l[p] <= l[p + 1] && l[p] <= l[p + 2];
            if (isH) {
                ph2 = ph1; ph1 = h[p];
                if (!isfinite(hi_since_pl) || h[p] > hi_since_pl) hi_since_pl = h[p];
                if (isfinite(ph2) && isfinite(atr[t]) && fabs(ph1 - ph2) <= tol * atr[t] && isfinite(lo_since_ph)) { neck_lo = lo_since_ph; armed_t = 1; }
                lo_since_ph = NAN;
            }
            if (isL) {
                pl2 = pl1; pl1 = l[p];
                if (!isfinite(lo_since_ph) || l[p] < lo_since_ph) lo_since_ph = l[p];
                if (isfinite(pl2) && isfinite(atr[t]) && fabs(pl1 - pl2) <= tol * atr[t] && isfinite(hi_since_pl)) { neck_hi = hi_since_pl; armed_b = 1; }
                hi_since_pl = NAN;
            }
        }
        if (isfinite(ph1) && isfinite(ph2) && isfinite(pl1) && isfinite(pl2)) {
            if (ph1 > ph2 && pl1 > pl2) state[t] = 1;
            else if (ph1 < ph2 && pl1 < pl2) state[t] = -1;
        }
        if (armed_b && c[t] > neck_hi) { dbl[t] = 1; armed_b = 0; }
        else if (armed_t && c[t] < neck_lo) { dbl[t] = -1; armed_t = 0; }
    }
}
