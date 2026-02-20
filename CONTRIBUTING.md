# Contributing

## Development Setup

1. Install Python 3.11+.
1. Install dependencies:

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
make lint
make typecheck
make test
make eval
```

## Add a New Pack

Packs are the extension units of the platform.

1. **Scaffold the pack**: Use the script to generate boilerplate:
   ```bash
   python scripts/new_pack.py --pack_id my_service --display_name "My Service"
   ```
2. **Implement tools**: Add read-only python functions in `packs/my_service/tools.py` and declare them with JSON Schemas in `pack.py`.
3. **Add documentation**: Place markdown files under `data/demo/my_service/howto/` (or the corresponding org directory). Ensure heading structures are correct for better chunking.
4. **Wire it up**: Open `app/api.py`, import your pack, and call `registry.register(MyServicePack())`.
5. **Add tests**: Add golden tests in `eval/` datasets or unit tests.

## Pull Requests

- Keep PRs focused.
- Include tests for behavior changes.
- Update README/docs when user-visible behavior changes.
