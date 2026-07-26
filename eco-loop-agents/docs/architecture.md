# Eco-Loop Building Agents: System Architecture

## 1. System Overview
The Eco-Loop Building Agent is an autonomous, closed-loop physical AI system designed to optimize commercial building energy consumption while maintaining strict thermal comfort parameters. 

By integrating a physics-based simulation engine (EnergyPlus) with an open-source Large Language Model (Qwen2.5) via the Model Context Protocol (MCP), the system transforms traditional, rigid rule-based Building Management Systems (BMS) into dynamic, reasoning-driven active control loops.

## 2. Component Architecture

### 2.1 The Digital Sandbox (EnergyPlus)
- **Role:** High-fidelity simulation of thermodynamics, HVAC equipment, and building physics.
- **Integration:** Wrapped via a custom Python bridge (`energyplus_wrapper.py`) that handles subprocess execution and parses `eplusout.csv` telemetry.
- **Data Streaming:** Outputs zone temperatures, HVAC energy consumption, and Predicted Mean Vote (PMV) comfort indices at 15-minute intervals.

### 2.2 The Communication Bus (MCP Server)
- **Role:** Standardized, secure interface exposing the digital sandbox to the AI.
- **Technology:** `FastMCP` (Python).
- **Exposed Tools:**
  1. `read_building_metrics()`: Ingests real-time sensor data from the simulation.
  2. `set_hvac_setpoints(zone, cooling_sp, heating_sp)`: Injects temperature setpoints back into the active `.idf` model.
  3. `apply_ecm(ecm_name, parameters)`: Executes complex Energy Conservation Measures (e.g., pre-cooling, load shifting).
  4. `get_energy_savings_report()`: Quantifies AI performance against a static baseline.

### 2.3 The Cognitive Engine (LLM Agent)
- **Role:** Autonomous reasoning and decision-making.
- **Technology:** Qwen2.5:7B (via Ollama) running locally to ensure zero latency dependency on cloud APIs and strict data privacy.
- **Orchestration:** At every timestep, the LLM analyzes metrics against predefined constraints (PMV between -0.5 and +0.5, Temps 20-26°C), logs its chain-of-thought reasoning, and maps decisions to strict tool calls.

## 3. The Closed-Loop Pipeline

1. **Simulate:** EnergyPlus advances the physical state by one 15-minute timestep.
2. **Observe:** The MCP server parses the output CSV and formats it into a semantic JSON state.
3. **Reason:** The LLM evaluates the state against occupancy schedules and comfort thresholds.
4. **Act:** The LLM issues a structured tool call (e.g., reducing cooling setpoints during off-peak hours).
5. **Inject:** `setpoint_injector.py` edits the underlying EnergyPlus `.idf` file.
6. **Repeat:** The loop advances autonomously.

## 4. Prompt Engineering & Latency Management

### 4.1 Prompt Strategy
The system utilizes a structured **System Prompt** enforcing constraint-based reasoning:
- **Hard Constraints:** "PMV MUST stay between -0.5 and +0.5."
- **Action Hierarchy:** "ALWAYS call read_building_metrics() first."
- **Context Awareness:** The prompt dynamically injects `time_of_day` and `occupancy_status` to guide load-shifting vs. comfort-prioritization.

### 4.2 Latency Management
- **Local Execution:** By utilizing Ollama with a quantized 7B model, network latency is eliminated.
- **History Pruning:** The conversation context window is strictly truncated to the last 20 turns, preventing token bloat and maintaining constant O(1) inference time throughout a multi-day simulation horizon.

### 4.3 Handling Lengthy Simulation Logs
EnergyPlus generates extremely dense `.eso` and `.csv` files (often millions of rows for an annual run). To prevent overwhelming the LLM's context window:
- **Incremental Polling:** The system parses only the most recent appended row at the current timestep instead of the entire historical file.
- **Semantic State Mapping:** We map raw, verbose CSV headers (e.g., `ZONE ONE:Zone Mean Air Temperature [C](TimeStep)`) to concise JSON keys (`avg_zone_temp_c`), vastly reducing the token payload sent to the LLM.

## 5. Agentic Autonomy & Self-Correction
The LLM acts as an active controller. If it sets a temperature that results in the PMV index dropping below -0.5 in the next timestep, the prompt constraints force the LLM to recognize the comfort violation in its reasoning log and self-correct by raising the heating setpoint immediately. This creates a resilient, self-healing control strategy superior to static PID loops.
