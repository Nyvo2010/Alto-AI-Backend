# Alto-AI-Backend

## Logging

The backend now produces *verbose, human‑readable* logs on the console and a
JSON‑formatted, rotating file (`logs/alto.log`) for analysis. Set
`LOG_LEVEL=DEBUG` (default in `.env.example`) to see module/line information,
exception traces, and other detailed messages. The stream at
https://logs.alto-ai.tech will display the pretty logs when the
`LOG_STREAM_TOKEN` is configured.
