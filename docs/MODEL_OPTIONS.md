# Model options

The pipeline needs two roles: a **fast** model that reads every comment and checks findings, and a **strong** model that re-reads unclear comments and writes findings. Which provider fills them is one setting.

| Setting `FITRADAR_PROVIDER` | Fast | Strong | Needs |
|---|---|---|---|
| `anthropic` (default when a key is present) | Claude Haiku 4.5 | Claude Sonnet 5.5 | `ANTHROPIC_API_KEY` |
| `openai` | a GPT model you choose | a GPT model you choose | `OPENAI_API_KEY`, `OPENAI_FAST_MODEL`, `OPENAI_STRONG_MODEL` |
| `offline` | keyword rules | keyword rules | nothing |
| `auto` | Claude if its key is set, else GPT, else offline | | |

## Claude

Model ids and prices are in `config.py`: Haiku at $1 in / $5 out and Sonnet at $2 in / $10 out per million tokens, from Anthropic's pricing page on 1 October 2026. Check the page again before the demo.

## GPT

GPT models can do the same classification. To use them, set the two model names and their four prices in `.env`. The names and prices are left blank on purpose: look them up on OpenAI's models and pricing pages on the day, pick a small model for `fast` and a larger one for `strong`, and enter them. Until prices are set the cost tab shows zero and says so.

## Offline

No model at all: a list of keywords written for the bundled stand-in data. It exists so the public link opens and every tab works without a key or a bill. It is not a measure of how a model would do, and its 100% score on the accuracy test means only that the rules were written for this data.

## Choosing between them

Run each candidate on the same data and fill in this table. Decide on the three things the brief asks for: cost, latency, quality.

| Provider | Agreement with known answers | Cost for 2,000 comments | Seconds for the run | Share sent to a person |
|---|---|---|---|---|
| Claude Haiku + Sonnet | | | | |
| GPT fast + strong | | | | |

```bash
FITRADAR_PROVIDER=anthropic python -m fitradar.graph && python -m fitradar.accuracy
FITRADAR_PROVIDER=openai    python -m fitradar.graph && python -m fitradar.accuracy
```

Cost and seconds are on the Run and cost tab after each run.

## How the switch works

`fitradar/llm.py` builds the models through LangChain (`ChatAnthropic` or `ChatOpenAI`) and asks each for schema-constrained output with `with_structured_output`. The LangGraph pipeline in `fitradar/graph.py` only ever calls four methods on the reader (`read_batches`, `reread`, `write_finding`, `evaluate`), so it does not change when the provider does.

To mix providers (for example GPT to read and Claude to write), change `ModelReader._chat` to choose the provider per role. To add another provider, install its LangChain package and add a branch there.

## Not yet tested

The Claude and GPT paths were built and checked for construction, but have not been run against the live services from this repository. Expect to adjust on the first real run: for example, a model that rejects a temperature setting, or a schema feature a provider does not accept.
