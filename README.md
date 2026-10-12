# Mini Process Monitor — Member 5
## Terminal UI and Refresh Module

This branch contains Member 5's implementation of the terminal user interface for the Mini Process Monitor Operating Systems project.

### Features
- Process table rendering and column alignment
- System CPU and memory summary presentation
- Menu and input-prompt handling
- Process details and action-result formatting
- Dashboard rendering and configurable refresh loop
- Handling of missing values, empty records, and Ctrl+C

### Run the Standalone Demo
From the project root, run:
```bash
python -m process_monitor.display
```
> **Note:** The standalone demo uses synthetic sample records for UI demonstration only. It does not represent live system process data. Search, sorting, process details, termination, and refresh behavior in the demo should be treated as simulated unless verified against the actual implementation.

### Run the Unit Tests
```bash
python -m unittest discover -s tests -v
```
The previous handoff report records 33 passing tests. Run the command above to verify the current checkout.

### Temporary Data and Integration
The process-record fields and statistics structures documented in [MEMBER_5_HANDOFF.md](MEMBER_5_HANDOFF.md) are proposed integration interfaces based on the project specification. Final compatibility depends on confirmation by the responsible module owners.

This branch implements the display component only. Live monitoring requires integration with the monitoring modules, while search, sorting, process details, and termination require the corresponding action modules and application controller.

### Documentation
See [MEMBER_5_HANDOFF.md](MEMBER_5_HANDOFF.md) for the detailed implementation report, public function interfaces, expected data schemas, integration example, test coverage, and outstanding dependencies.
