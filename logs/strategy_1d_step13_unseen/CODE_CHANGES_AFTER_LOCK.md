# Code changes after the protocol lock (bug fixes only; the design in the protocol is unchanged)

1. 2026-10-13, first run crashed at the reference-breadth SELF-CHECK (before any model was trained or any prediction
   was made): `np.allclose` got an object-dtype array (TypeError: ufunc 'isfinite' not supported). Fix: cast both
   arrays to float in that assert. No result had been produced.
2. Same TypeError in the second self-check (swing-candidate breadth vs reference breadth), again before any model was
   trained. Fix: cast both arrays to float in that assert. No result had been produced.
