"""Phase 4 learners on the frozen biology (docs/PHASE4_DESIGN.md section 1).

The only training signal is the homeostatic drive-reduction reward in `reward.py`. Nothing here
reads a detector, a trace or a PlayScore field, and no reward, observation or goal is named
play / bout / motif / exaggeration (H2; audited in tests). The need-driven heuristic is a control
arm, never a teacher: no distillation, no behaviour cloning.
"""
