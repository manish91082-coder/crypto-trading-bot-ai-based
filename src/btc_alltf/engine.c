/* BTC-ALLTF study (2026-10-28): bar-by-bar paper-trade engine. One position at a time, one direction per call.
   Build: gcc -O2 -shared -o src/btc_alltf/engine.dll src/btc_alltf/engine.c

   Timing (no look-ahead):
     - st[s] is the rule state computed from bars 0..s only (1 = "in", 0 = "out").
     - ENTRY: onset at bar s (st[s]==1 and st[s-1]==0, gate[s]==1 if a gate is given) -> buy/sell at open of bar s+1+delay.
     - SIGNAL EXIT: st[t-1]==0 -> exit at open of bar t.   TIME EXIT: t - entry_bar == max_hold -> exit at open of bar t.
     - STOP / TAKE-PROFIT / TRAILING: levels fixed from ATR at the signal bar s (atr[s]); checked on every bar from the entry bar on:
         open beyond the level -> fill at the open (gap); else touched by low/high -> fill at the level.
         If the stop and the target are both inside one bar, the STOP is assumed first (conservative, reason SL_AMBIG).
         The trailing level is raised with the bar's extreme only AFTER that bar was checked (it works from the next bar).
     - LIQUIDATION (futures 1x isolated, shorts only; a 1x long can not be liquidated): price >= 2*entry/(1+mmr).
     - After an exit at an open, a new entry at the same open is allowed if its onset bar is the bar before.
     - Data end: an open position is closed at the last close (reason END).
   Reasons: 1 SIG, 2 TIME, 3 SL, 4 SL_GAP, 5 TP, 6 TP_GAP, 7 TRAIL, 8 TRAIL_GAP, 9 LIQ, 10 END, 11 SL_AMBIG
   MAE/MFE: worst / best price while the position was open: the full range of every bar before the exit bar, and on the
   exit bar only the fill price (the order of that bar's high and low is unknown). */
#include <stdint.h>
#include <math.h>

#define R_SIG 1
#define R_TIME 2
#define R_SL 3
#define R_SL_GAP 4
#define R_TP 5
#define R_TP_GAP 6
#define R_TRAIL 7
#define R_TRAIL_GAP 8
#define R_LIQ 9
#define R_END 10
#define R_SL_AMBIG 11

__declspec(dllexport) int bt(int n, const double *o, const double *h, const double *l, const double *c, const double *atr,
                             const int8_t *st, const int8_t *gate, int dir, int use_sig, double sl_k, double tp_k, double trail_k,
                             int max_hold, double mmr, int start, int end, int delay, int cap,
                             int32_t *ei, int32_t *xi, int8_t *rs, double *pin, double *pout, double *mae, double *mfe)
{
    int k = 0, pos = 0, eb = 0;
    double px = 0, stop = 0, tp = 0, tr = 0, liq = 0, a0 = 0, best = 0, worst = 0, ext = 0;
    int has_stop = 0, has_tp = 0, has_tr = 0, stop_is_trail = 0;
    int need_atr = (sl_k > 0 || tp_k > 0 || trail_k > 0);
    if (end > n) end = n;
    for (int t = (start < 1 ? 1 : start); t < end; t++) {
        /* ---- exits decided at the previous close, filled at this open */
        if (pos && t > eb) {
            int r = 0;
            if (use_sig && st[t - 1] == 0) r = R_SIG;
            else if (max_hold > 0 && t - eb >= max_hold) r = R_TIME;
            if (r) {
                double x = o[t];
                if (dir > 0) { if (x < worst) worst = x; if (x > best) best = x; }
                else { if (x > worst) worst = x; if (x < best) best = x; }
                ei[k] = eb; xi[k] = t; rs[k] = (int8_t)r; pin[k] = px; pout[k] = x; mae[k] = worst; mfe[k] = best; k++;
                pos = 0;
                if (k >= cap) return -1;
            }
        }
        /* ---- entry at this open */
        if (!pos) {
            int s = t - 1 - delay;
            if (s >= 1 && st[s] == 1 && st[s - 1] == 0 && (gate == 0 || gate[s] == 1)) {
                a0 = atr[s];
                if (!need_atr || (isfinite(a0) && a0 > 0)) {
                    pos = 1; eb = t; px = o[t];
                    has_stop = sl_k > 0; has_tp = tp_k > 0; has_tr = trail_k > 0; stop_is_trail = 0;
                    stop = has_stop ? px - dir * sl_k * a0 : 0;
                    tp = has_tp ? px + dir * tp_k * a0 : 0;
                    ext = px;
                    tr = has_tr ? px - dir * trail_k * a0 : 0;
                    if (has_tr) {                               /* the effective stop is the tighter of stop and trail */
                        if (!has_stop || (dir > 0 ? tr > stop : tr < stop)) { stop = tr; has_stop = 1; stop_is_trail = 1; }
                    }
                    liq = (dir < 0 && mmr > 0) ? 2.0 * px / (1.0 + mmr) : 0;
                    best = px; worst = px;
                }
            }
        }
        if (!pos) continue;
        /* ---- intrabar: gap at the open, then the bar's range */
        {
            double x = 0; int r = 0;
            double op = o[t], hi = h[t], lo = l[t];
            if (dir > 0) {
                if (has_stop && op <= stop && t > eb) { x = op; r = stop_is_trail ? R_TRAIL_GAP : R_SL_GAP; }
                else if (has_tp && op >= tp && t > eb) { x = op; r = R_TP_GAP; }
                else {
                    int hs = has_stop && lo <= stop, ht = has_tp && hi >= tp;
                    if (hs) { x = stop; r = stop_is_trail ? R_TRAIL : (ht ? R_SL_AMBIG : R_SL); }
                    else if (ht) { x = tp; r = R_TP; }
                }
            } else {
                if (liq > 0 && op >= liq && t > eb) { x = op; r = R_LIQ; }
                else if (has_stop && op >= stop && t > eb) { x = op; r = stop_is_trail ? R_TRAIL_GAP : R_SL_GAP; }
                else if (has_tp && op <= tp && t > eb) { x = op; r = R_TP_GAP; }
                else {
                    int hs = has_stop && hi >= stop, ht = has_tp && lo <= tp;
                    int hl = liq > 0 && hi >= liq && (!has_stop || stop >= liq);
                    if (hl) { x = liq; r = R_LIQ; }
                    else if (hs) { x = stop; r = stop_is_trail ? R_TRAIL : (ht ? R_SL_AMBIG : R_SL); }
                    else if (ht) { x = tp; r = R_TP; }
                }
            }
            if (r) {
                /* on the exit bar only the fill price counts (the order of the bar's high and low is unknown) */
                if (dir > 0) { if (x < worst) worst = x; if (x > best) best = x; }
                else { if (x > worst) worst = x; if (x < best) best = x; }
                ei[k] = eb; xi[k] = t; rs[k] = (int8_t)r; pin[k] = px; pout[k] = x; mae[k] = worst; mfe[k] = best; k++;
                pos = 0;
                if (k >= cap) return -1;
                continue;
            }
            if (dir > 0) { if (lo < worst) worst = lo; if (hi > best) best = hi; }
            else { if (hi > worst) worst = hi; if (lo < best) best = lo; }
            /* ---- trailing update (applies from the next bar) */
            if (has_tr) {
                if (dir > 0) { if (hi > ext) ext = hi; double nt = ext - trail_k * a0; if (nt > stop) { stop = nt; stop_is_trail = 1; } }
                else { if (lo < ext) ext = lo; double nt = ext + trail_k * a0; if (nt < stop) { stop = nt; stop_is_trail = 1; } }
            }
        }
    }
    if (pos) {
        int t = end - 1;
        ei[k] = eb; xi[k] = t; rs[k] = R_END; pin[k] = px; pout[k] = c[t]; mae[k] = worst; mfe[k] = best; k++;
    }
    return k;
}

/* Random-entry control: for each actual trade j (hold h_j bars, same direction), reps random entries e uniform in
   [lo, hi - h_j]; return = open[e+h]/open[e]; net = dir*(R-1) - f - f*R - dir*(cf[e+h]-cf[e]).  cf = cumulative funding
   rate at bar opens (0 for spot). Returns mean and sd of all reps*n control nets. xorshift64* RNG, seeded per config. */
__declspec(dllexport) void ctrl(int n, const double *o, const double *cf, int lo, int hi, int dir, const int32_t *hold, int m,
                                int reps, uint64_t seed, double f, double *out_mean, double *out_sd, int64_t *out_n)
{
    uint64_t x = seed ? seed : 88172645463325252ULL;
    double s = 0, s2 = 0; int64_t cnt = 0;
    for (int r = 0; r < reps; r++) {
        for (int j = 0; j < m; j++) {
            int hj = hold[j] < 1 ? 1 : hold[j];
            int span = hi - hj - lo;
            if (span <= 0) continue;
            x ^= x >> 12; x ^= x << 25; x ^= x >> 27;
            uint64_t z = x * 2685821657736338717ULL;
            int e = lo + (int)(z % (uint64_t)span);
            double R = o[e + hj] / o[e];
            double v = dir * (R - 1.0) - f - f * R - dir * (cf[e + hj] - cf[e]);
            s += v; s2 += v * v; cnt++;
        }
    }
    *out_n = cnt;
    if (cnt > 1) { double mu = s / cnt; *out_mean = mu; *out_sd = sqrt((s2 - cnt * mu * mu) / (cnt - 1)); }
    else { *out_mean = NAN; *out_sd = NAN; }
}
