# Contributing

## Development Setup
1. Install Python 3.11+.
2. Install dependencies:
```bash
pip install -r requirements-dev.txt
```
3. Start the API:
```bash
make dev
```

## Quality Checks
Run before opening a PR:
```bash
make test
make lint
```

## Add a New Pack
1. Create a folder under `packs/<pack_id>/`.
2. Implement a `ProductPack` class in `pack.py`.
3. Add read-only tools in `tools.py` with JSON schema args.
4. Add docs under `data/<org>/<pack_id>/howto/`.
5. Register the pack in `app/api.py` startup wiring.

## Pull Requests
- Keep PRs focused.
- Include tests for behavior changes.
- Update README/docs when user-visible behavior changes.
