# UI stutter — repro matrix (agent)

`AUDIENCE`: LLM agents. `GOAL`: classify *when* stutter happens before profiling.

## AXES

- **Repro**: this doc (S0–S5).  
- **Profile / tools**: `AGENTS.md` §17.  
- **Context log**: `PIPELA_AI_DEBUG` sessions.

## ENV_SNAPSHOT

Record: OS build, monitor Hz, Windows scale %, game window mode, Pipela commit.

## SCENARIOS

- **S0**: idle 20–30s after launch.  
- **S1**: control window + settings only; switch terminal↔settings 5×.  
- **S2**: dock to game; move overlays; open kill counter.  
- **S3**: enable macro loops (capture-heavy).  
- **S4**: multi-monitor / mixed DPI.  
- **S5**: reproduce with game fullscreen exclusive if applicable.

`NEXT`: once scenario locked, pair with `.stats` + session log.
